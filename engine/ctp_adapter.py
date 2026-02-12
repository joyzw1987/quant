from datetime import datetime


class _DummyCtpApi:
    def __init__(self, kind):
        self.kind = kind
        self.connected = False
        self.last_connect_args = {}
        self.subscribed = []
        self.orders = {}
        self._seq = 0

    def connect(self, **kwargs):
        self.last_connect_args = dict(kwargs or {})
        self.connected = True
        return True

    def disconnect(self):
        self.connected = False
        return True

    def subscribe(self, symbols):
        symbols = list(symbols or [])
        self.subscribed.extend(symbols)
        return True

    def place_order(self, symbol, direction, price, size, order_type="LIMIT"):
        self._seq += 1
        order_id = f"{self.kind.upper()}_{self._seq:08d}"
        order = {
            "order_id": order_id,
            "symbol": symbol,
            "direction": direction,
            "price": float(price),
            "size": float(size),
            "filled": float(size),
            "status": "FILLED",
            "order_type": order_type,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.orders[order_id] = order
        return order_id

    def cancel_order(self, order_id):
        order = self.orders.get(order_id)
        if not order:
            return False
        if order.get("status") == "FILLED":
            return False
        order["status"] = "CANCELED"
        return True

    def query_positions(self):
        # Dummy adapter keeps flat position by default.
        return []

    def query_account(self):
        return {"balance": 1000000.0, "available": 1000000.0}

    def query_orders(self):
        return list(self.orders.values())


class CtpAdapter:
    """
    内置最小 CTP 适配器：
    - 默认提供可连通的 Dummy API，便于本地模拟与健康检查。
    - 真实 CTP 请通过 config 中 adapter_module/adapter_class 覆盖。
    """

    def __init__(self, ctp_config=None):
        self.ctp_config = ctp_config or {}

    def create_md_api(self):
        return _DummyCtpApi(kind="md")

    def create_td_api(self):
        return _DummyCtpApi(kind="td")
