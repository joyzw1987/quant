import json
import unittest
from pathlib import Path

from engine.config_validator import validate_config


class ConfigValidatorTest(unittest.TestCase):
    def _load(self):
        path = Path("config_template.json")
        return json.loads(path.read_text(encoding="utf-8-sig"))

    def test_portfolio_weight_method_invalid(self):
        cfg = self._load()
        cfg["portfolio"]["weight_method"] = "bad"
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("portfolio.weight_method" in e for e in errors))

    def test_portfolio_rebalance_invalid(self):
        cfg = self._load()
        cfg["portfolio"]["rebalance"] = "daily"
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("portfolio.rebalance" in e for e in errors))

    def test_portfolio_valid(self):
        cfg = self._load()
        cfg["portfolio"]["weight_method"] = "risk_budget"
        cfg["portfolio"]["rebalance"] = "weekly"
        cfg["portfolio"]["min_rebalance_bars"] = 10
        errors, _ = validate_config(cfg, mode="paper")
        self.assertFalse(any("portfolio." in e for e in errors))

    def test_market_hours_special_date_invalid(self):
        cfg = self._load()
        cfg["market_hours"]["special_closures"] = [{"date": "2026/01/01", "start": "09:00", "end": "10:00"}]
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("market_hours.special_closures[0].date" in e for e in errors))

    def test_market_hours_special_time_invalid(self):
        cfg = self._load()
        cfg["market_hours"]["special_sessions"] = [{"date": "2026-01-01", "start": "25:00", "end": "10:00"}]
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("market_hours.special_sessions[0].start" in e for e in errors))

    def test_market_hours_extra_workdays_invalid(self):
        cfg = self._load()
        cfg["market_hours"]["extra_workdays"] = ["2026/01/01"]
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("market_hours.extra_workdays[0]" in e for e in errors))

    def test_market_hours_holidays_dates_invalid(self):
        cfg = self._load()
        cfg["market_hours"]["holidays"] = {"dates": ["2026/01/01"]}
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("market_hours.holidays.dates[0]" in e for e in errors))

    def test_data_quality_warn_greater_than_max_invalid(self):
        cfg = self._load()
        cfg["data_quality"]["warn_missing_ratio"] = 0.2
        cfg["data_quality"]["max_missing_ratio"] = 0.1
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("data_quality.warn_missing_ratio must be <=" in e for e in errors))

    def test_data_quality_valid(self):
        cfg = self._load()
        cfg["data_quality"] = {
            "enabled": True,
            "min_rows": 100,
            "max_missing_bars": 10,
            "max_duplicates": 0,
            "max_missing_ratio": 0.1,
            "warn_missing_ratio": 0.05,
            "max_jump_ratio": 0.1,
            "min_coverage_ratio": 0.8,
            "warn_coverage_ratio": 0.9,
        }
        errors, _ = validate_config(cfg, mode="paper")
        self.assertFalse(any("data_quality." in e for e in errors))

    def test_data_quality_coverage_relation_invalid(self):
        cfg = self._load()
        cfg["data_quality"]["min_coverage_ratio"] = 0.9
        cfg["data_quality"]["warn_coverage_ratio"] = 0.8
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("data_quality.warn_coverage_ratio must be >=" in e for e in errors))

    def test_paper_check_invalid(self):
        cfg = self._load()
        cfg["paper_check"]["strict"] = "yes"
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("paper_check.strict" in e for e in errors))

    def test_cost_model_overlap_warn(self):
        cfg = self._load()
        cfg["cost_model"]["profiles"] = [
            {"start": "09:00", "end": "11:00", "slippage": 1.0},
            {"start": "10:30", "end": "12:00", "slippage": 1.0},
        ]
        errors, warnings = validate_config(cfg, mode="paper")
        self.assertEqual(errors, [])
        self.assertTrue(any("overlaps with" in w for w in warnings))

    def test_monitor_no_new_data_threshold_invalid(self):
        cfg = self._load()
        cfg["monitor"]["no_new_data_error_threshold"] = 0
        errors, _ = validate_config(cfg, mode="paper")
        self.assertTrue(any("monitor.no_new_data_error_threshold" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
