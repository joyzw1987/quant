import unittest

from strict_oos_validate import build_candidates, frange


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


if __name__ == "__main__":
    unittest.main()
