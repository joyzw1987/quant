import unittest

from schedule_tasks import build_plan, normalize_hhmm


class ScheduleTasksTest(unittest.TestCase):
    def test_normalize_hhmm(self):
        self.assertEqual("09:05", normalize_hhmm("9:5"))
        self.assertEqual("23:00", normalize_hhmm("23:00"))

    def test_build_plan(self):
        cfg = {
            "symbol": "M2609",
            "scheduler": {
                "task_prefix": "Quant_M2609",
                "days": "MON,TUE,WED,THU,FRI",
                "source": "akshare",
                "fetch_times": ["11:35", "15:05"],
                "research_time": "23:20",
            },
        }
        plan = build_plan(cfg)
        self.assertEqual(3, len(plan))
        self.assertEqual("fetch", plan[0]["kind"])
        self.assertEqual("research", plan[-1]["kind"])
        self.assertTrue(plan[0]["name"].startswith("Quant_M2609_fetch_"))


if __name__ == "__main__":
    unittest.main()
