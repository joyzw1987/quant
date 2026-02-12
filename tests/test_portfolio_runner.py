import unittest

from portfolio_runner import _period_key, _simulate_portfolio


class PortfolioRunnerTest(unittest.TestCase):
    def test_period_key(self):
        self.assertEqual(_period_key("2026-02-12 09:00", "none"), "all")
        self.assertTrue(_period_key("2026-02-12 09:00", "weekly").startswith("2026-W"))
        self.assertEqual(_period_key("2026-02-12 09:00", "monthly"), "2026-02")

    def test_simulate_portfolio_rebalance(self):
        symbols = ["A", "B"]
        dates = [
            "2026-01-05 09:00",
            "2026-01-06 09:00",
            "2026-01-07 09:00",
            "2026-01-08 09:00",
            "2026-01-09 09:00",
            "2026-01-12 09:00",
            "2026-01-13 09:00",
        ]
        aligned_returns = {
            "A": [0.0, 0.01, 0.01, 0.01, 0.01, 0.01, 0.01],
            "B": [0.0, -0.005, -0.005, -0.005, -0.005, -0.005, -0.005],
        }
        equity, events, corr = _simulate_portfolio(
            symbols=symbols,
            dates=dates,
            aligned_returns=aligned_returns,
            initial_capital=100000,
            corr_limit=0.8,
            weight_method="risk_budget",
            rebalance_mode="weekly",
            min_rebalance_bars=1,
        )
        self.assertEqual(len(equity), len(dates))
        self.assertTrue(len(events) >= 2)
        self.assertIn("A", corr)


if __name__ == "__main__":
    unittest.main()

