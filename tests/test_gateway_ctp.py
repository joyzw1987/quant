import unittest

from engine.ctp_adapter import CtpAdapter
from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway
from engine.order_state import ORDER_STATUS_PARTIAL, ORDER_STATUS_REJECTED


class GatewayCtpTest(unittest.TestCase):
    def setUp(self):
        adapter = CtpAdapter({})
        self.md = CtpMarketDataGateway(adapter.create_md_api())
        self.td = CtpTradeGateway(adapter.create_td_api())

    def test_connect_subscribe_place_query(self):
        self.assertTrue(self.md.connect())
        self.assertTrue(self.td.connect())
        self.assertTrue(self.md.subscribe(["M2609"]))

        ret = self.td.place_order(symbol="M2609", direction="BUY", price=1.0, size=1, order_type="LIMIT")
        self.assertTrue(ret.get("ok"))
        self.assertTrue(ret.get("order_id"))

        orders = self.td.query_orders()
        self.assertGreaterEqual(len(orders), 1)

    def test_cancel_filled_order_returns_false(self):
        self.assertTrue(self.td.connect())
        ret = self.td.place_order(symbol="M2609", direction="BUY", price=1.0, size=1)
        order_id = ret.get("order_id")
        cancel_ret = self.td.cancel_order(order_id)
        self.assertFalse(cancel_ret.get("ok"))

    def test_protection_mode_blocks_new_order(self):
        self.assertTrue(self.td.connect())
        self.td.set_protection_mode(True, reason="RECONCILE_MISMATCH")
        ret = self.td.place_order(symbol="M2609", direction="BUY", price=1.0, size=1)
        self.assertFalse(ret.get("ok"))
        self.assertEqual(ret.get("error"), "PROTECTION_MODE")

    def test_query_orders_maps_remote_partial(self):
        class PartialApi:
            def __init__(self):
                self.connected = False
                self.order_id = "T_0001"

            def connect(self, **kwargs):
                self.connected = True
                return True

            def place_order(self, **kwargs):
                return self.order_id

            def query_orders(self):
                return [
                    {
                        "order_id": self.order_id,
                        "symbol": "M2609",
                        "direction": "BUY",
                        "price": 3000.0,
                        "size": 2.0,
                        "filled": 1.0,
                        "status": "PartTradedQueueing",
                    }
                ]

        td = CtpTradeGateway(PartialApi())
        self.assertTrue(td.connect())
        ret = td.place_order(symbol="M2609", direction="BUY", price=3000.0, size=2.0)
        self.assertTrue(ret.get("ok"))
        orders = td.query_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].get("status"), ORDER_STATUS_PARTIAL)
        self.assertEqual(float(orders[0].get("filled", 0.0)), 1.0)

    def test_query_orders_maps_remote_rejected(self):
        class RejectApi:
            def __init__(self):
                self.connected = False
                self.order_id = "T_0002"

            def connect(self, **kwargs):
                self.connected = True
                return True

            def place_order(self, **kwargs):
                return self.order_id

            def query_orders(self):
                return [
                    {
                        "order_id": self.order_id,
                        "symbol": "M2609",
                        "direction": "BUY",
                        "price": 3000.0,
                        "size": 1.0,
                        "filled": 0.0,
                        "status": "InsertRejected",
                        "message": "risk reject",
                    }
                ]

        td = CtpTradeGateway(RejectApi())
        self.assertTrue(td.connect())
        ret = td.place_order(symbol="M2609", direction="BUY", price=3000.0, size=1.0)
        self.assertTrue(ret.get("ok"))
        orders = td.query_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].get("status"), ORDER_STATUS_REJECTED)


if __name__ == "__main__":
    unittest.main()
