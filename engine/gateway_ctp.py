from engine.gateway_base import GatewayBase


class CtpMarketDataGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False

    def connect(self, **kwargs):
        if self.api and hasattr(self.api, "connect"):
            ok = self.api.connect(**kwargs)
            self.connected = bool(ok if ok is not None else True)
        else:
            self.connected = True
        return self.connected

    def subscribe(self, symbols):
        if self.api and hasattr(self.api, "subscribe"):
            return bool(self.api.subscribe(symbols))
        return True


class CtpTradeGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False

    def connect(self, **kwargs):
        if self.api and hasattr(self.api, "connect"):
            ok = self.api.connect(**kwargs)
            self.connected = bool(ok if ok is not None else True)
        else:
            self.connected = True
        return self.connected

    def query_positions(self):
        if self.api and hasattr(self.api, "query_positions"):
            return self.api.query_positions()
        return []

    def query_orders(self):
        if self.api and hasattr(self.api, "query_orders"):
            return self.api.query_orders()
        return []
