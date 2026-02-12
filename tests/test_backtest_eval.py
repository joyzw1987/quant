import unittest
from datetime import datetime

from engine.backtest_eval import compute_max_drawdown, schedule_allows


class BacktestEvalTest(unittest.TestCase):
    def test_compute_max_drawdown(self):
        curve = [
            {"equity": 100000},
            {"equity": 102000},
            {"equity": 101000},
            {"equity": 98000},
            {"equity": 99000},
        ]
        self.assertEqual(4000.0, compute_max_drawdown(curve))

    def test_schedule_allows(self):
        schedule = {"weekdays": [1, 2, 3, 4, 5], "sessions": []}
        self.assertTrue(schedule_allows(datetime(2026, 2, 11, 10, 0), schedule))
        self.assertFalse(schedule_allows(datetime(2026, 2, 14, 10, 0), schedule))


if __name__ == "__main__":
    unittest.main()
