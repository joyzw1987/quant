from engine.gateway_base import GatewayBase
from engine.order_state import (
    ORDER_STATUS_ACKED,
    ORDER_STATUS_CANCELING,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_REJECTED,
    OrderStateMachine,
)


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
            self.order_state.transition(order_id, ORDER_STATUS_FILLED, filled=size)
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
            merged = {o["order_id"]: o for o in self.order_state.all_orders() if o.get("order_id")}
            for row in remote:
                oid = row.get("order_id")
                if oid:
                    merged[oid] = row
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
