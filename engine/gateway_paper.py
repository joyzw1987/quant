from engine.gateway_base import GatewayBase
from engine.order_state import (
    ORDER_STATUS_ACKED,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_CANCELING,
    ORDER_STATUS_FILLED,
    ORDER_STATUS_REJECTED,
    OrderStateMachine,
)


class PaperMarketDataGateway(GatewayBase):
    def __init__(self, data_engine):
        self.data_engine = data_engine
        self.connected = False

    def connect(self, **kwargs):
        self.connected = True
        return True

    def disconnect(self, **kwargs):
        self.connected = False
        return True

    def subscribe(self, symbols):
        return True

    def stream_bars(self, symbol):
        return self.data_engine.get_bars(symbol)

    def place_order(self, *args, **kwargs):
        raise RuntimeError("PaperMarketDataGateway does not support place_order")

    def cancel_order(self, *args, **kwargs):
        raise RuntimeError("PaperMarketDataGateway does not support cancel_order")

    def query_orders(self, *args, **kwargs):
        return []

    def query_positions(self, *args, **kwargs):
        return []

    def query_account(self, *args, **kwargs):
        return {}


class PaperTradeGateway(GatewayBase):
    def __init__(self, execution):
        self.execution = execution
        self.connected = False
        self.order_state = OrderStateMachine()
        self._seq = 0

    def _next_order_id(self):
        self._seq += 1
        return f"PAPER_{self._seq:08d}"

    def connect(self, **kwargs):
        self.connected = True
        return True

    def disconnect(self, **kwargs):
        self.connected = False
        return True

    def subscribe(self, symbols):
        return True

    def place_order(self, symbol, direction, price, size, order_type="LIMIT"):
        if not self.connected:
            return {"ok": False, "error": "PAPER_TRADE_NOT_CONNECTED"}
        order_id = self._next_order_id()
        order = self.order_state.create_order(order_id, symbol, direction, price, size, order_type=order_type)
        signal = 1 if str(direction).upper() in ("LONG", "BUY") else -1
        self.order_state.transition(order_id, ORDER_STATUS_ACKED)
        opened = self.execution.send_order(symbol, signal, price, size)
        if not opened:
            self.order_state.transition(order_id, ORDER_STATUS_REJECTED, message="PAPER_ORDER_REJECTED")
            return {"ok": False, "order_id": order_id, "status": ORDER_STATUS_REJECTED, "error": "PAPER_ORDER_REJECTED"}
        self.order_state.transition(order_id, ORDER_STATUS_FILLED, filled=size)
        return {"ok": True, "order_id": order_id, "status": ORDER_STATUS_FILLED, "order": order}

    def cancel_order(self, order_id):
        if not self.connected:
            return {"ok": False, "error": "PAPER_TRADE_NOT_CONNECTED", "order_id": order_id}
        order = self.order_state.get(order_id)
        if not order:
            return {"ok": False, "order_id": order_id, "error": "PAPER_ORDER_NOT_FOUND"}
        status = order.get("status")
        if status in (ORDER_STATUS_FILLED, ORDER_STATUS_CANCELED, ORDER_STATUS_REJECTED):
            return {"ok": False, "order_id": order_id, "error": "PAPER_ALREADY_FINAL"}
        self.order_state.transition(order_id, ORDER_STATUS_CANCELING)
        self.order_state.transition(order_id, ORDER_STATUS_CANCELED)
        return {"ok": True, "order_id": order_id, "status": ORDER_STATUS_CANCELED}

    def query_orders(self):
        return self.order_state.all_orders()

    def query_positions(self):
        pos = self.execution.position
        if not pos:
            return []
        qty = float(pos.get("size", 0.0))
        if str(pos.get("direction", "")).upper() in ("SHORT", "SELL"):
            qty = -qty
        return [{"symbol": pos.get("symbol"), "qty": qty, "direction": pos.get("direction"), "size": pos.get("size")}]

    def query_account(self):
        return {}
