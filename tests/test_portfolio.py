import unittest

from engine.portfolio import allocate_weights, allocate_weights_with_method, build_corr_matrix, pearson_corr


class PortfolioTest(unittest.TestCase):
    def test_pearson_corr(self):
        self.assertAlmostEqual(pearson_corr([1, 2, 3], [2, 4, 6]), 1.0, places=6)
        self.assertAlmostEqual(pearson_corr([1, 2, 3], [6, 4, 2]), -1.0, places=6)

    def test_allocate_weights_with_corr_limit(self):
        symbols = ["A", "B", "C"]
        corr = {
            "A": {"A": 1.0, "B": 0.95, "C": 0.2},
            "B": {"A": 0.95, "B": 1.0, "C": 0.1},
            "C": {"A": 0.2, "B": 0.1, "C": 1.0},
        }
        weights, selected = allocate_weights(symbols, corr, max_corr=0.8)
        self.assertEqual(selected, ["A", "C"])
        self.assertAlmostEqual(weights["A"], 0.5)
        self.assertAlmostEqual(weights["B"], 0.0)
        self.assertAlmostEqual(weights["C"], 0.5)

    def test_allocate_weights_meta_blocked(self):
        symbols = ["A", "B", "C"]
        corr = {
            "A": {"A": 1.0, "B": 0.95, "C": 0.2},
            "B": {"A": 0.95, "B": 1.0, "C": 0.1},
            "C": {"A": 0.2, "B": 0.1, "C": 1.0},
        }
        _, selected, meta = allocate_weights_with_method(
            symbols=symbols,
            corr_matrix=corr,
            return_map={},
            max_corr=0.8,
            weight_method="equal",
        )
        self.assertEqual(selected, ["A", "C"])
        self.assertTrue(meta.get("blocked_by_corr"))
        self.assertEqual(meta["blocked_by_corr"][0]["symbol"], "B")

    def test_build_corr_matrix(self):
        ret = {"A": [0.1, 0.2, 0.3], "B": [0.2, 0.4, 0.6]}
        matrix = build_corr_matrix(ret)
        self.assertIn("A", matrix)
        self.assertIn("B", matrix)
        self.assertAlmostEqual(matrix["A"]["B"], 1.0, places=6)

    def test_allocate_weights_risk_budget(self):
        symbols = ["A", "B"]
        corr = {"A": {"A": 1.0, "B": 0.2}, "B": {"A": 0.2, "B": 1.0}}
        ret = {
            "A": [0.01, 0.011, 0.009, 0.01],
            "B": [0.05, -0.04, 0.06, -0.03],
        }
        weights, selected, meta = allocate_weights_with_method(
            symbols=symbols,
            corr_matrix=corr,
            return_map=ret,
            max_corr=0.8,
            weight_method="risk_budget",
        )
        self.assertEqual(selected, symbols)
        self.assertGreater(weights["A"], weights["B"])
        self.assertAlmostEqual(weights["A"] + weights["B"], 1.0, places=6)
        self.assertEqual(meta["method"], "risk_budget")


if __name__ == "__main__":
    unittest.main()
