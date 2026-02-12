import unittest
from datetime import datetime

from engine.market_scheduler import is_market_open, load_market_schedule, next_market_open


class MarketSchedulerTest(unittest.TestCase):
    def test_is_market_open_by_session(self):
        cfg = {
            "market_hours": {
                "sessions": [{"start": "09:00", "end": "11:30"}, {"start": "13:30", "end": "15:00"}],
                "weekdays": [1, 2, 3, 4, 5],
                "holidays": {"dates": []},
            }
        }
        schedule = load_market_schedule(cfg)
        self.assertTrue(is_market_open(datetime(2026, 2, 11, 9, 30), schedule))
        self.assertFalse(is_market_open(datetime(2026, 2, 11, 12, 0), schedule))
        self.assertFalse(is_market_open(datetime(2026, 2, 14, 9, 30), schedule))

    def test_next_market_open(self):
        cfg = {
            "market_hours": {
                "sessions": [{"start": "09:00", "end": "11:30"}],
                "weekdays": [1, 2, 3, 4, 5],
                "holidays": {"dates": ["2026-02-12"]},
            }
        }
        schedule = load_market_schedule(cfg)
        dt = datetime(2026, 2, 11, 12, 0)
        nxt = next_market_open(dt, schedule)
        self.assertEqual(nxt.strftime("%Y-%m-%d %H:%M"), "2026-02-13 09:00")

    def test_partial_closure_blocks_session(self):
        cfg = {
            "market_hours": {
                "sessions": [{"start": "09:00", "end": "11:30"}],
                "weekdays": [1, 2, 3, 4, 5],
                "holidays": {"dates": []},
                "special_closures": [{"date": "2026-02-11", "start": "09:20", "end": "09:40"}],
            }
        }
        schedule = load_market_schedule(cfg)
        self.assertTrue(is_market_open(datetime(2026, 2, 11, 9, 10), schedule))
        self.assertFalse(is_market_open(datetime(2026, 2, 11, 9, 30), schedule))
        self.assertTrue(is_market_open(datetime(2026, 2, 11, 9, 50), schedule))

    def test_special_sessions_override_holiday_and_weekend(self):
        cfg = {
            "market_hours": {
                "sessions": [{"start": "09:00", "end": "11:30"}],
                "weekdays": [1, 2, 3, 4, 5],
                "holidays": {"dates": ["2026-02-14"]},
                "special_sessions": [{"date": "2026-02-14", "start": "10:00", "end": "10:30"}],
            }
        }
        schedule = load_market_schedule(cfg)
        self.assertFalse(is_market_open(datetime(2026, 2, 14, 9, 30), schedule))
        self.assertTrue(is_market_open(datetime(2026, 2, 14, 10, 10), schedule))


if __name__ == "__main__":
    unittest.main()
