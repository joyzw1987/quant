import unittest

from engine.data_engine import DataEngine
from engine.market_scheduler import load_market_schedule


class DataEngineTest(unittest.TestCase):
    def test_validate_bars_without_schedule_counts_all_gaps(self):
        bars = [
            {"datetime": "2026-02-12 11:30", "open": 1, "high": 1, "low": 1, "close": 1},
            {"datetime": "2026-02-12 13:31", "open": 1, "high": 1, "low": 1, "close": 1},
        ]
        report = DataEngine().validate_bars(bars, schedule=None)
        self.assertEqual(report["missing"], 120)

    def test_validate_bars_with_schedule_ignores_closed_minutes(self):
        bars = [
            {"datetime": "2026-02-12 11:30", "open": 1, "high": 1, "low": 1, "close": 1},
            {"datetime": "2026-02-12 13:31", "open": 1, "high": 1, "low": 1, "close": 1},
        ]
        schedule = load_market_schedule(
            {
                "market_hours": {
                    "sessions": [{"start": "09:00", "end": "11:30"}, {"start": "13:30", "end": "15:00"}],
                    "weekdays": [1, 2, 3, 4, 5],
                    "holidays": {"dates": []},
                }
            }
        )
        report = DataEngine().validate_bars(bars, schedule=schedule)
        # Lunch break is ignored; only 13:30 is expected but missing.
        self.assertEqual(report["missing"], 1)

    def test_validate_bars_duplicate_jump_and_coverage(self):
        bars = [
            {"datetime": "2026-02-12 09:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-12 09:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-12 09:02", "open": 110, "high": 111, "low": 109, "close": 110},
        ]
        report = DataEngine().validate_bars(bars, schedule=None)
        self.assertEqual(report["raw_total"], 3)
        self.assertEqual(report["total"], 2)
        self.assertEqual(report["duplicates"], 1)
        self.assertEqual(report["missing"], 1)
        self.assertAlmostEqual(report["max_jump_ratio"], 0.10, places=6)
        self.assertAlmostEqual(report["coverage_ratio"], 2.0 / 3.0, places=6)


if __name__ == "__main__":
    unittest.main()
