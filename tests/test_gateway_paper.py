import unittest

from engine.execution_sim import SimExecution
from engine.gateway_paper import PaperTradeGateway
from engine.order_state import ORDER_STATUS_FILLED, ORDER_STATUS_REJECTED


class GatewayPaperTest(unittest.TestCase):
    def setUp(self):
        self.execution = SimExecution(slippage=0)
        self.gw = PaperTradeGateway(self.execution)

    def test_place_order_and_query_orders(self):
        self.assertTrue(self.gw.connect())
        ret = self.gw.place_order(symbol="M2609", direction="BUY", price=100.0, size=2, order_type="LIMIT")
        self.assertTrue(ret.get("ok"))
        self.assertEqual(ret.get("status"), ORDER_STATUS_FILLED)
        orders = self.gw.query_orders()
        self.assertEqual(len(orders), 1)
        self.assertEqual(orders[0].get("status"), ORDER_STATUS_FILLED)

    def test_reject_when_position_exists(self):
        self.assertTrue(self.gw.connect())
        first = self.gw.place_order(symbol="M2609", direction="BUY", price=100.0, size=1)
        self.assertTrue(first.get("ok"))
        second = self.gw.place_order(symbol="M2609", direction="BUY", price=101.0, size=1)
        self.assertFalse(second.get("ok"))
        self.assertEqual(second.get("status"), ORDER_STATUS_REJECTED)
        orders = self.gw.query_orders()
        self.assertEqual(len(orders), 2)
        self.assertEqual(orders[-1].get("status"), ORDER_STATUS_REJECTED)

    def test_query_positions_from_execution(self):
        self.assertTrue(self.gw.connect())
        self.gw.place_order(symbol="M2609", direction="BUY", price=100.0, size=3)
        positions = self.gw.query_positions()
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0].get("symbol"), "M2609")
        self.assertGreater(positions[0].get("qty", 0), 0)


if __name__ == "__main__":
    unittest.main()
