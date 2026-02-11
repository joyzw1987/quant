class GatewayBase:
    def connect(self, *args, **kwargs):
        raise NotImplementedError

    def subscribe(self, *args, **kwargs):
        raise NotImplementedError
