import unittest

from engine.order_state import (
    ORDER_STATUS_ACKED,
    ORDER_STATUS_CANCELING,
    ORDER_STATUS_CANCELED,
    ORDER_STATUS_FILLED,
    OrderStateMachine,
)


class OrderStateMachineTest(unittest.TestCase):
    def setUp(self):
        self.sm = OrderStateMachine()
        self.sm.create_order("OID1", "M2609", "BUY", 100.0, 2.0)

    def test_valid_transition_to_filled(self):
        ok, _ = self.sm.transition("OID1", ORDER_STATUS_ACKED)
        self.assertTrue(ok)
        ok, _ = self.sm.transition("OID1", ORDER_STATUS_FILLED, filled=2.0)
        self.assertTrue(ok)
        self.assertEqual(self.sm.get("OID1")["status"], ORDER_STATUS_FILLED)

    def test_cancel_flow(self):
        ok, _ = self.sm.transition("OID1", ORDER_STATUS_ACKED)
        self.assertTrue(ok)
        ok, _ = self.sm.transition("OID1", ORDER_STATUS_CANCELING)
        self.assertTrue(ok)
        ok, _ = self.sm.transition("OID1", ORDER_STATUS_CANCELED)
        self.assertTrue(ok)

    def test_invalid_transition(self):
        ok, reason = self.sm.transition("OID1", ORDER_STATUS_CANCELED)
        self.assertFalse(ok)
        self.assertIn("INVALID_TRANSITION", reason)


if __name__ == "__main__":
    unittest.main()
