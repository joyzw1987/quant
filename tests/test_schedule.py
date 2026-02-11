import unittest
from datetime import datetime

from main import parse_schedule, schedule_allows


class ScheduleTest(unittest.TestCase):
    def test_schedule_allows_time_window(self):
        schedule = parse_schedule(
            {
                "weekdays": [1, 2, 3, 4, 5],
                "sessions": [{"start": "09:00", "end": "11:30"}],
            }
        )
        self.assertTrue(schedule_allows(datetime(2026, 2, 9, 10, 0), schedule))
        self.assertFalse(schedule_allows(datetime(2026, 2, 9, 12, 0), schedule))


if __name__ == "__main__":
    unittest.main()
