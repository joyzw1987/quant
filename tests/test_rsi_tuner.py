import unittest

from engine.rsi_tuner import evaluate_candidate_walk_forward, evaluate_rsi_ma_params_with_drawdown


class RSITunerTest(unittest.TestCase):
    def test_evaluate_rsi_ma_params_with_drawdown_basic(self):
        prices = [100 + (i % 10) for i in range(120)]
        stats = evaluate_rsi_ma_params_with_drawdown(
            prices,
            {
                "fast": 5,
                "slow": 20,
                "rsi_period": 14,
                "rsi_overbought": 60,
                "rsi_oversold": 40,
                "min_diff": 0.0,
                "trend_filter": False,
            },
        )
        self.assertIsNotNone(stats)
        self.assertIn("pnl", stats)
        self.assertIn("max_drawdown", stats)
        self.assertIn("trades", stats)

    def test_evaluate_candidate_walk_forward_summary(self):
        prices = [100 + (i % 12) for i in range(240)]
        summary = evaluate_candidate_walk_forward(
            prices=prices,
            candidate={"fast": 5, "slow": 20},
            train_size=120,
            test_size=60,
            step_size=60,
            base_params={
                "rsi_period": 14,
                "rsi_overbought": 60,
                "rsi_oversold": 40,
                "min_diff": 0.0,
                "trend_filter": False,
                "trend_window": 40,
                "cooldown_bars": 0,
                "max_consecutive_losses": None,
            },
            min_trades=0,
        )
        self.assertEqual(summary["windows_total"], 2)
        self.assertTrue(summary["windows_valid"] >= 0)
        self.assertIn("test_total_pnl", summary)


if __name__ == "__main__":
    unittest.main()
