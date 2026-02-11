import unittest

from engine.walk_forward import build_windows, run_walk_forward


class WalkForwardTest(unittest.TestCase):
    def test_build_windows_default_step(self):
        windows = build_windows(total_size=100, train_size=40, test_size=20)
        self.assertEqual(len(windows), 3)
        self.assertEqual(windows[0]["train_start"], 0)
        self.assertEqual(windows[0]["train_end"], 40)
        self.assertEqual(windows[0]["test_start"], 40)
        self.assertEqual(windows[0]["test_end"], 60)
        self.assertEqual(windows[-1]["train_start"], 40)
        self.assertEqual(windows[-1]["test_end"], 100)

    def test_run_walk_forward_summary(self):
        prices = [100 + (i % 15) for i in range(180)]
        candidates = [{"fast": 3, "slow": 8}, {"fast": 5, "slow": 20}]
        result = run_walk_forward(
            prices=prices,
            candidates=candidates,
            train_size=60,
            test_size=30,
            step_size=30,
            objective="pnl",
            dd_penalty=0.0,
            min_trades=0,
        )
        self.assertEqual(result["summary"]["windows_total"], 4)
        self.assertEqual(len(result["rows"]), 4)
        self.assertTrue(result["summary"]["windows_valid"] >= 1)
        self.assertIn("test_total_pnl", result["summary"])


if __name__ == "__main__":
    unittest.main()
