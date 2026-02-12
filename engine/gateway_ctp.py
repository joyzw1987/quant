from engine.gateway_base import GatewayBase
from engine.order_state import (
    ORDER_STATUS_ACKED,
    ORDER_STATUS_CANCELING,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_PARTIAL,
    ORDER_STATUS_REJECTED,
    OrderStateMachine,
)


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return float(default)


def _normalize_remote_status(status, filled, size):
    text = str(status or "").strip().upper()
    if text in ("FILLED", "ALL_TRADED", "ALLTRADED", "TRADED"):
        return ORDER_STATUS_FILLED
    if text in ("PARTIAL", "PART_TRADED", "PARTTRADED", "PART_TRADED_QUEUEING", "PARTTRADEDQUEUEING"):
        return ORDER_STATUS_PARTIAL
    if text in ("CANCELING", "PENDING_CANCEL"):
        return ORDER_STATUS_CANCELING
    if text in ("CANCELED", "CANCELLED", "CANCEL", "ALL_CANCELED", "ALLCANCELED"):
        return ORDER_STATUS_CANCELED
    if text in ("REJECTED", "REJECT", "ERROR", "INSERT_REJECTED", "INSERTREJECTED"):
        return ORDER_STATUS_REJECTED
    if text in ("NEW", "SUBMITTED", "NO_TRADE_QUEUEING", "NOTRADEQUEUEING", "ACKED", "ACCEPTED"):
        return ORDER_STATUS_ACKED
    if size > 0 and filled >= size:
        return ORDER_STATUS_FILLED
    if filled > 0:
        return ORDER_STATUS_PARTIAL
    return ORDER_STATUS_ACKED


class CtpMarketDataGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False
        self.last_error = ""

    def connect(self, **kwargs):
        try:
            if self.api and hasattr(self.api, "connect"):
                ok = self.api.connect(**kwargs)
                self.connected = bool(ok if ok is not None else True)
            else:
                self.connected = True
            self.last_error = ""
            return self.connected
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            return False

    def disconnect(self, **kwargs):
        try:
            if self.api and hasattr(self.api, "disconnect"):
                self.api.disconnect()
            self.connected = False
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def subscribe(self, symbols):
        try:
            if self.api and hasattr(self.api, "subscribe"):
                return bool(self.api.subscribe(symbols))
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def place_order(self, *args, **kwargs):
        raise RuntimeError("MarketDataGateway does not support place_order")

    def cancel_order(self, *args, **kwargs):
        raise RuntimeError("MarketDataGateway does not support cancel_order")

    def query_orders(self, *args, **kwargs):
        return []

    def query_positions(self, *args, **kwargs):
        return []

    def query_account(self, *args, **kwargs):
        return {}


class CtpTradeGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False
        self.last_error = ""
        self.order_state = OrderStateMachine()
        self.protection_mode = False
        self.protection_reason = ""

    def set_protection_mode(self, enabled, reason=""):
        self.protection_mode = bool(enabled)
        self.protection_reason = str(reason or "")

    def _sync_order_from_remote(self, row):
        if not isinstance(row, dict):
            return None
        order_id = row.get("order_id")
        if not order_id:
            return None

        order = self.order_state.get(order_id)
        symbol = row.get("symbol", "")
        direction = row.get("direction", "")
        price = _to_float(row.get("price"), 0.0)
        size = _to_float(row.get("size"), 0.0)
        filled = _to_float(row.get("filled", row.get("volume_traded", row.get("traded", 0.0))), 0.0)
        if order is None:
            order = self.order_state.create_order(
                order_id=order_id,
                symbol=symbol,
                direction=direction,
                price=price,
                size=size,
                order_type=row.get("order_type", "LIMIT"),
            )
            # Remote order is already acknowledged by exchange/gateway.
            self.order_state.transition(order_id, ORDER_STATUS_ACKED, filled=filled)
        else:
            size = _to_float(order.get("size"), size)

        target_status = _normalize_remote_status(row.get("status"), filled=filled, size=size)
        current = self.order_state.get(order_id)
        if current:
            if current.get("status") != target_status:
                self.order_state.transition(
                    order_id,
                    target_status,
                    filled=filled,
                    message=str(row.get("message") or ""),
                )
            else:
                current["filled"] = filled
        return self.order_state.get(order_id)

    def connect(self, **kwargs):
        try:
            if self.api and hasattr(self.api, "connect"):
                ok = self.api.connect(**kwargs)
                self.connected = bool(ok if ok is not None else True)
            else:
                self.connected = True
            self.last_error = ""
            return self.connected
        except Exception as exc:
            self.connected = False
            self.last_error = str(exc)
            return False

    def disconnect(self, **kwargs):
        try:
            if self.api and hasattr(self.api, "disconnect"):
                self.api.disconnect()
            self.connected = False
            return True
        except Exception as exc:
            self.last_error = str(exc)
            return False

    def subscribe(self, symbols):
        # Trade gateway doesn't subscribe market data by default.
        return True

    def place_order(self, symbol, direction, price, size, order_type="LIMIT"):
        if not self.connected:
            return {"ok": False, "error": "TRADE_NOT_CONNECTED"}
        if self.protection_mode:
            return {"ok": False, "error": "PROTECTION_MODE", "reason": self.protection_reason}
        try:
            if self.api and hasattr(self.api, "place_order"):
                order_id = self.api.place_order(
                    symbol=symbol,
                    direction=direction,
                    price=price,
                    size=size,
                    order_type=order_type,
                )
            else:
                order_id = f"LOCAL_{len(self.order_state.orders) + 1:08d}"
            order = self.order_state.create_order(order_id, symbol, direction, price, size, order_type=order_type)
            self.order_state.transition(order_id, ORDER_STATUS_ACKED)
            if self.api and hasattr(self.api, "query_orders"):
                try:
                    remote = list(self.api.query_orders() or [])
                    for row in remote:
                        if row.get("order_id") == order_id:
                            synced = self._sync_order_from_remote(row)
                            if synced is not None:
                                order = synced
                            break
                except Exception:
                    pass
            else:
                # Fallback local mode: fill immediately to keep compatibility.
                self.order_state.transition(order_id, ORDER_STATUS_FILLED, filled=size)
                order = self.order_state.get(order_id) or order
            return {"ok": True, "order_id": order_id, "status": order["status"], "order": order}
        except Exception as exc:
            self.last_error = str(exc)
            return {"ok": False, "error": self.last_error}

    def cancel_order(self, order_id):
        if not self.connected:
            return {"ok": False, "error": "TRADE_NOT_CONNECTED"}
        try:
            ok = True
            if self.api and hasattr(self.api, "cancel_order"):
                ok = bool(self.api.cancel_order(order_id))
            order = self.order_state.get(order_id)
            if order and order.get("status") not in (ORDER_STATUS_FILLED, ORDER_STATUS_CANCELED, ORDER_STATUS_REJECTED):
                self.order_state.transition(order_id, ORDER_STATUS_CANCELING)
                if ok:
                    self.order_state.transition(order_id, ORDER_STATUS_CANCELED)
            return {"ok": bool(ok), "order_id": order_id}
        except Exception as exc:
            self.last_error = str(exc)
            return {"ok": False, "error": self.last_error, "order_id": order_id}

    def query_positions(self):
        try:
            if self.api and hasattr(self.api, "query_positions"):
                return self.api.query_positions()
            return []
        except Exception as exc:
            self.last_error = str(exc)
            return []

    def query_orders(self):
        try:
            remote = []
            if self.api and hasattr(self.api, "query_orders"):
                remote = list(self.api.query_orders() or [])
            for row in remote:
                self._sync_order_from_remote(row)
            merged = {o["order_id"]: dict(o) for o in self.order_state.all_orders() if o.get("order_id")}
            for row in remote:
                oid = row.get("order_id")
                if oid:
                    base = merged.get(oid, {})
                    merged[oid] = {**row, **base}
            return list(merged.values())
        except Exception as exc:
            self.last_error = str(exc)
            return self.order_state.all_orders()

    def query_account(self):
        try:
            if self.api and hasattr(self.api, "query_account"):
                account = self.api.query_account()
                if isinstance(account, dict):
                    return account
            return {}
        except Exception as exc:
            self.last_error = str(exc)
            return {}
