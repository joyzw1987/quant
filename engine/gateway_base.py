class GatewayBase:
    def connect(self, *args, **kwargs):
        raise NotImplementedError

    def disconnect(self, *args, **kwargs):
        raise NotImplementedError

    def subscribe(self, *args, **kwargs):
        raise NotImplementedError

    def place_order(self, *args, **kwargs):
        raise NotImplementedError

    def cancel_order(self, *args, **kwargs):
        raise NotImplementedError

    def query_orders(self, *args, **kwargs):
        raise NotImplementedError

    def query_positions(self, *args, **kwargs):
        raise NotImplementedError
