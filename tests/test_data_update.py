import os
import tempfile
import unittest

import pandas as pd

from data_update import fetch_minutes_by_source


class DataUpdateTest(unittest.TestCase):
    def test_fetch_minutes_by_source_csv(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "M2609.csv")
            df = pd.DataFrame(
                [
                    {"datetime": "2026-02-10 09:00", "open": 1, "high": 2, "low": 1, "close": 2},
                    {"datetime": "2026-02-11 09:00", "open": 2, "high": 3, "low": 2, "close": 3},
                ]
            )
            df.to_csv(path, index=False)
            got = fetch_minutes_by_source(symbol="M2609", days=20, source="csv", out_path=path)
            self.assertEqual(len(got), 2)
            self.assertEqual(got.iloc[0]["datetime"].strftime("%Y-%m-%d %H:%M"), "2026-02-10 09:00")

    def test_fetch_minutes_by_source_csv_days_filter(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "M2609.csv")
            df = pd.DataFrame(
                [
                    {"datetime": "2026-02-10 09:00", "open": 1, "high": 2, "low": 1, "close": 2},
                    {"datetime": "2026-02-11 09:00", "open": 2, "high": 3, "low": 2, "close": 3},
                ]
            )
            df.to_csv(path, index=False)
            got = fetch_minutes_by_source(symbol="M2609", days=1, source="csv", out_path=path)
            self.assertEqual(len(got), 1)
            self.assertEqual(got.iloc[0]["datetime"].strftime("%Y-%m-%d"), "2026-02-11")

    def test_fetch_minutes_by_source_unsupported(self):
        with self.assertRaises(SystemExit):
            fetch_minutes_by_source(symbol="M2609", days=20, source="foo", out_path="data/M2609.csv")


if __name__ == "__main__":
    unittest.main()
