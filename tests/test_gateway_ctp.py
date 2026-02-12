import unittest

from engine.ctp_adapter import CtpAdapter
from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway


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


if __name__ == "__main__":
    unittest.main()
