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


if __name__ == "__main__":
    unittest.main()
