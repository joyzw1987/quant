import unittest

from engine.perf_report import build_monthly_metrics, build_return_distribution, build_weekly_metrics


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

    def test_build_weekly_metrics(self):
        equity_rows = [
            {"datetime": "2026-01-05 09:00", "equity": 100000},
            {"datetime": "2026-01-06 09:00", "equity": 101000},
            {"datetime": "2026-01-13 09:00", "equity": 100500},
        ]
        trade_rows = [
            {"exit_time": "2026-01-06 10:00", "pnl": 500},
            {"exit_time": "2026-01-13 10:00", "pnl": -200},
        ]
        rows = build_weekly_metrics(equity_rows, trade_rows)
        self.assertTrue(len(rows) >= 2)
        self.assertIn("week", rows[0])
        self.assertIn("pnl", rows[0])

    def test_build_return_distribution(self):
        rows = [
            {"return_pct": -3.0},
            {"return_pct": -1.0},
            {"return_pct": 0.5},
            {"return_pct": 3.0},
        ]
        dist = build_return_distribution(rows)
        self.assertEqual(dist["count"], 4)
        self.assertEqual(dist["positive_count"], 2)
        self.assertEqual(dist["negative_count"], 2)
        self.assertEqual(dist["buckets"]["lt_-2"], 1)
        self.assertEqual(dist["buckets"]["-2_to_0"], 1)
        self.assertEqual(dist["buckets"]["0_to_2"], 1)
        self.assertEqual(dist["buckets"]["gt_2"], 1)


if __name__ == "__main__":
    unittest.main()
