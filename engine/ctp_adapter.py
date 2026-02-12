class _DummyCtpApi:
    def __init__(self, kind):
        self.kind = kind
        self.connected = False
        self.last_connect_args = {}
        self.subscribed = []

    def connect(self, **kwargs):
        self.last_connect_args = dict(kwargs or {})
        self.connected = True
        return True

    def subscribe(self, symbols):
        symbols = list(symbols or [])
        self.subscribed.extend(symbols)
        return True

    def query_positions(self):
        return []

    def query_orders(self):
        return []


class CtpAdapter:
    """
    内置最小 CTP 适配器：
    - 默认提供可连通的 Dummy API，便于本地模拟与健康检查。
    - 若要接入真实 CTP，请在 config.json 配置 adapter_module/adapter_class 覆盖本适配器。
    """

    def __init__(self, ctp_config=None):
        self.ctp_config = ctp_config or {}

    def create_md_api(self):
        return _DummyCtpApi(kind="md")

    def create_td_api(self):
        return _DummyCtpApi(kind="td")
