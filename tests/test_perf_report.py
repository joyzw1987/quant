import unittest

from engine.perf_report import build_monthly_metrics


class PerfReportTest(unittest.TestCase):
    def test_build_monthly_metrics(self):
        equity_rows = [
            {"datetime": "2026-01-02 09:00", "equity": 100000},
            {"datetime": "2026-01-20 09:00", "equity": 101000},
            {"datetime": "2026-02-03 09:00", "equity": 100500},
            {"datetime": "2026-02-20 09:00", "equity": 102000},
        ]
        trade_rows = [
            {"exit_time": "2026-01-10 10:00", "pnl": 500},
            {"exit_time": "2026-01-15 10:00", "pnl": -200},
            {"exit_time": "2026-02-18 10:00", "pnl": 900},
        ]

        rows = build_monthly_metrics(equity_rows, trade_rows)
        self.assertEqual(len(rows), 2)
        jan = rows[0]
        feb = rows[1]

        self.assertEqual(jan["month"], "2026-01")
        self.assertAlmostEqual(jan["pnl"], 300.0)
        self.assertEqual(jan["trade_count"], 2)
        self.assertAlmostEqual(jan["win_rate"], 50.0)

        self.assertEqual(feb["month"], "2026-02")
        self.assertAlmostEqual(feb["pnl"], 900.0)
        self.assertEqual(feb["trade_count"], 1)


if __name__ == "__main__":
    unittest.main()
