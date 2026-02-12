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


if __name__ == "__main__":
    unittest.main()
