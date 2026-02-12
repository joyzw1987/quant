import unittest

from param_heatmap import build_windows, stability_of


class ParamHeatmapTest(unittest.TestCase):
    def test_stability_of(self):
        avg_score, std_score, stable_score = stability_of([1.0, 3.0, 5.0], 0.5)
        self.assertAlmostEqual(avg_score, 3.0)
        self.assertTrue(std_score > 0)
        self.assertAlmostEqual(stable_score, avg_score - 0.5 * std_score)

    def test_build_windows(self):
        bars = [{"datetime": f"2026-01-01 09:{i:02d}", "close": 100 + i} for i in range(10)]
        windows = build_windows(bars, window_bars=4, window_step=3)
        self.assertTrue(len(windows) >= 3)
        self.assertEqual(len(windows[0]), 4)
        self.assertEqual(windows[-1][-1]["datetime"], bars[-1]["datetime"])


if __name__ == "__main__":
    unittest.main()

