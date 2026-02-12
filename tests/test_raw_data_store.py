import tempfile
import unittest
from pathlib import Path

import pandas as pd

from engine.raw_data_store import save_raw_minutes_by_date_session


class RawDataStoreTest(unittest.TestCase):
    def test_save_by_date_and_session(self):
        cfg = {
            "market_hours": {
                "sessions": [
                    {"start": "09:00", "end": "11:30"},
                    {"start": "13:30", "end": "15:00"},
                ]
            }
        }
        df = pd.DataFrame(
            [
                {"datetime": "2026-02-12 09:05", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
                {"datetime": "2026-02-12 14:01", "open": 2, "high": 3, "low": 1.5, "close": 2.5},
                {"datetime": "2026-02-12 20:01", "open": 3, "high": 4, "low": 2.5, "close": 3.5},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            files = save_raw_minutes_by_date_session(df, "M2609", td, cfg)
            self.assertEqual(3, len(files))

            day_dir = Path(td) / "2026" / "02" / "2026-02-12"
            self.assertTrue((day_dir / "M2609_s1_0900_1130.csv").exists())
            self.assertTrue((day_dir / "M2609_s2_1330_1500.csv").exists())
            self.assertTrue((day_dir / "M2609_other.csv").exists())

    def test_merge_and_dedup(self):
        cfg = {"market_hours": {"sessions": [{"start": "09:00", "end": "11:30"}]}}
        first = pd.DataFrame(
            [
                {"datetime": "2026-02-12 09:05", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
            ]
        )
        second = pd.DataFrame(
            [
                {"datetime": "2026-02-12 09:05", "open": 1, "high": 2, "low": 0.5, "close": 1.5},
                {"datetime": "2026-02-12 09:06", "open": 2, "high": 3, "low": 1.5, "close": 2.5},
            ]
        )

        with tempfile.TemporaryDirectory() as td:
            save_raw_minutes_by_date_session(first, "M2609", td, cfg)
            save_raw_minutes_by_date_session(second, "M2609", td, cfg)
            target = Path(td) / "2026" / "02" / "2026-02-12" / "M2609_s1_0900_1130.csv"
            merged = pd.read_csv(target)
            self.assertEqual(2, len(merged))


if __name__ == "__main__":
    unittest.main()
