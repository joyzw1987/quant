import unittest

from strict_oos_validate import build_candidates, choose_winner, frange


class StrictOosTest(unittest.TestCase):
    def test_frange(self):
        values = frange(0.2, 0.6, 0.2)
        self.assertEqual([0.2, 0.4, 0.6], values)

    def test_build_candidates_bounded(self):
        cfg = {
            "strategy": {
                "name": "rsi_ma",
                "min_diff": 0.8,
                "rsi_period": 14,
                "rsi_overbought": 60,
                "rsi_oversold": 40,
            },
            "auto_adjust": {
                "fast_min": 3,
                "fast_max": 8,
                "slow_min": 10,
                "slow_max": 30,
                "slow_step": 2,
            },
        }
        candidates = build_candidates(cfg, top_n=120)
        self.assertTrue(len(candidates) <= 120)
        self.assertTrue(len(candidates) > 0)

    def test_choose_winner_gate_pass(self):
        result = choose_winner(
            baseline_stats={"pnl": 100, "trades": 8, "max_drawdown": 50},
            baseline_score=80,
            tuned_stats={"pnl": 140, "trades": 10, "max_drawdown": 40},
            tuned_score=120,
            min_holdout_trades=6,
            min_score_improve=10,
            require_positive_holdout=True,
        )
        self.assertEqual("tuned", result["winner"])
        self.assertTrue(result["gate_pass"])

    def test_choose_winner_gate_block(self):
        result = choose_winner(
            baseline_stats={"pnl": 100, "trades": 8, "max_drawdown": 50},
            baseline_score=80,
            tuned_stats={"pnl": 60, "trades": 2, "max_drawdown": 40},
            tuned_score=79,
            min_holdout_trades=6,
            min_score_improve=10,
            require_positive_holdout=True,
        )
        self.assertEqual("baseline", result["winner"])
        self.assertFalse(result["gate_pass"])
        self.assertIn("holdout_trades_below_threshold", result["reasons"])


if __name__ == "__main__":
    unittest.main()
