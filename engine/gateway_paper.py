from engine.gateway_base import GatewayBase


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


class PaperTradeGateway(GatewayBase):
    def __init__(self, execution):
        self.execution = execution
        self.connected = False

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
        signal = 1 if str(direction).upper() in ("LONG", "BUY") else -1
        opened = self.execution.send_order(symbol, signal, price, size)
        if not opened:
            return {"ok": False, "error": "PAPER_ORDER_REJECTED"}
        return {"ok": True, "order_id": f"PAPER_{len(self.execution.trades)+1:08d}", "status": "FILLED"}

    def cancel_order(self, order_id):
        return {"ok": False, "order_id": order_id, "error": "PAPER_ALREADY_FILLED"}

    def query_orders(self):
        return []

    def query_positions(self):
        return []
