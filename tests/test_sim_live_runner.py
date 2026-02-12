import unittest

from sim_live_runner import _build_dq_report, get_no_new_data_alert_level, get_no_new_data_error_threshold


class SimLiveRunnerTest(unittest.TestCase):
    def test_no_new_data_threshold_default(self):
        self.assertEqual(get_no_new_data_error_threshold({}), 3)

    def test_no_new_data_threshold_from_config(self):
        cfg = {"monitor": {"no_new_data_error_threshold": 5}}
        self.assertEqual(get_no_new_data_error_threshold(cfg), 5)

    def test_no_new_data_alert_level(self):
        cfg = {"monitor": {"no_new_data_error_threshold": 3}}
        self.assertEqual(get_no_new_data_alert_level(1, cfg), "WARN")
        self.assertEqual(get_no_new_data_alert_level(3, cfg), "ERROR")

    def test_build_dq_report_detects_missing_minutes(self):
        bars = [
            {"datetime": "2026-02-12 09:00", "open": 1, "high": 1, "low": 1, "close": 1},
            {"datetime": "2026-02-12 09:01", "open": 1, "high": 1, "low": 1, "close": 1},
            {"datetime": "2026-02-12 09:04", "open": 1, "high": 1, "low": 1, "close": 1},
        ]
        report = _build_dq_report(bars)
        self.assertEqual(report["total"], 3)
        self.assertEqual(report["missing"], 2)


if __name__ == "__main__":
    unittest.main()
