from engine.gateway_base import GatewayBase


class CtpMarketDataGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False

    def connect(self, **kwargs):
        self.connected = True

    def subscribe(self, symbols):
        return True


class CtpTradeGateway(GatewayBase):
    def __init__(self, api=None):
        self.api = api
        self.connected = False

    def connect(self, **kwargs):
        self.connected = True

    def query_positions(self):
        return []

    def query_orders(self):
        return []
