import unittest

from engine.position_reconciler import diff_account, diff_positions, summarize_positions


class PositionReconcilerTest(unittest.TestCase):
    def test_summarize_positions(self):
        positions = [
            {"symbol": "M2609", "qty": 2},
            {"symbol": "M2609", "qty": -1},
            {"symbol": "RB2605", "qty": 3},
        ]
        s = summarize_positions(positions)
        self.assertEqual(s["M2609"], 1)
        self.assertEqual(s["RB2605"], 3)

    def test_diff_positions(self):
        local = {"M2609": 1, "RB2605": 0, "AU2606": 2}
        broker = {"M2609": 1, "RB2605": 1}
        d = diff_positions(local, broker)
        self.assertIn("RB2605", d)
        self.assertIn("AU2606", d)

    def test_diff_account_with_tolerance(self):
        local = {"balance": 100.0, "available": 90.0000001}
        broker = {"balance": 100.0, "available": 90.0}
        d = diff_account(local, broker, tolerance=1e-4)
        self.assertEqual(d, {})
        d2 = diff_account(local, {"balance": 90.0}, tolerance=1e-4)
        self.assertIn("balance", d2)
        self.assertIn("available", d2)


if __name__ == "__main__":
    unittest.main()
