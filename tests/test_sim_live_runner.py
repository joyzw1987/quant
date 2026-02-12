import unittest

from sim_live_runner import get_no_new_data_alert_level, get_no_new_data_error_threshold


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


if __name__ == "__main__":
    unittest.main()
