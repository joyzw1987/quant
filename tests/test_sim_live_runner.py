import unittest
import tempfile
import json
import os

from sim_live_runner import (
    _build_dq_report,
    compute_runtime_metrics,
    get_drawdown_alert_threshold,
    get_no_new_data_alert_level,
    get_no_new_data_error_threshold,
    read_paper_check_status,
)


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

    def test_drawdown_threshold(self):
        self.assertIsNone(get_drawdown_alert_threshold({}))
        cfg = {"monitor": {"drawdown_alert_threshold": 8000}}
        self.assertEqual(get_drawdown_alert_threshold(cfg), 8000.0)

    def test_compute_runtime_metrics(self):
        trades = [{"pnl": 10}, {"pnl": -5}, {"pnl": 3}]
        equity_curve = [{"equity": 100000}, {"equity": 100100}, {"equity": 99950}]
        metrics = compute_runtime_metrics(100000, 100008, trades, equity_curve)
        self.assertEqual(metrics["total_pnl"], 8.0)
        self.assertAlmostEqual(metrics["win_rate"], 66.6666666, places=3)
        self.assertEqual(metrics["runtime_drawdown"], 150.0)

    def test_read_paper_check_status_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            status = read_paper_check_status(tmp)
            self.assertIsNone(status["ok"])
            self.assertEqual(status["error_count"], 0)
            self.assertEqual(status["errors"], [])

    def test_read_paper_check_status_ok_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "paper_check_report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"ok": True, "error_count": 0, "errors": []}, f)
            status = read_paper_check_status(tmp)
            self.assertEqual(status["ok"], True)
            self.assertEqual(status["error_count"], 0)
            self.assertEqual(status["errors"], [])

    def test_read_paper_check_status_failed_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "paper_check_report.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"error_count": 2, "errors": ["e1", "e2"]}, f)
            status = read_paper_check_status(tmp)
            self.assertEqual(status["ok"], False)
            self.assertEqual(status["error_count"], 2)
            self.assertEqual(status["errors"], ["e1", "e2"])


if __name__ == "__main__":
    unittest.main()
