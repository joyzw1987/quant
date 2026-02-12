import unittest

from engine.data_quality_gate import evaluate_data_quality


class DataQualityGateTest(unittest.TestCase):
    def test_gate_pass(self):
        report = {"total": 500, "missing": 5}
        cfg = {
            "enabled": True,
            "min_rows": 200,
            "max_missing_bars": 10,
            "max_missing_ratio": 0.05,
            "warn_missing_ratio": 0.02,
        }
        ok, errors, warnings = evaluate_data_quality(report, cfg)
        self.assertTrue(ok)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_gate_block_on_short_data(self):
        report = {"total": 100, "missing": 0}
        cfg = {"enabled": True, "min_rows": 200}
        ok, errors, _ = evaluate_data_quality(report, cfg)
        self.assertFalse(ok)
        self.assertTrue(any("DATA_TOO_SHORT" in e for e in errors))

    def test_gate_warn_and_block_on_missing(self):
        report = {"total": 100, "missing": 10}
        cfg = {
            "enabled": True,
            "max_missing_bars": 20,
            "max_missing_ratio": 0.08,
            "warn_missing_ratio": 0.05,
        }
        ok, errors, warnings = evaluate_data_quality(report, cfg)
        self.assertFalse(ok)
        self.assertTrue(any("MISSING_RATIO_EXCEEDED" in e for e in errors))
        self.assertTrue(any("MISSING_RATIO_WARN" in w for w in warnings))


if __name__ == "__main__":
    unittest.main()
