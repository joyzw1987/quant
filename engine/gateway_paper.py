from engine.gateway_base import GatewayBase


class PaperMarketDataGateway(GatewayBase):
    def __init__(self, data_engine):
        self.data_engine = data_engine

    def stream_bars(self, symbol):
        return self.data_engine.get_bars(symbol)


class PaperTradeGateway(GatewayBase):
    def __init__(self, execution):
        self.execution = execution
