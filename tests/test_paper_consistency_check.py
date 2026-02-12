import csv
import os
import tempfile
import unittest

from paper_consistency_check import check_trades


class PaperConsistencyCheckTest(unittest.TestCase):
    def test_check_trades_ok(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trades.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "direction",
                        "entry_price",
                        "exit_price",
                        "size",
                        "fill_ratio",
                        "gross_pnl",
                        "commission",
                        "pnl",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "direction": "LONG",
                        "entry_price": 100,
                        "exit_price": 101,
                        "size": 1,
                        "fill_ratio": 1.0,
                        "gross_pnl": 10,
                        "commission": 2,
                        "pnl": 8,
                    }
                )
            errors = check_trades(path)
            self.assertEqual(errors, [])

    def test_check_trades_detects_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "trades.csv")
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(
                    f,
                    fieldnames=[
                        "direction",
                        "entry_price",
                        "exit_price",
                        "size",
                        "gross_pnl",
                        "commission",
                        "pnl",
                    ],
                )
                writer.writeheader()
                writer.writerow(
                    {
                        "direction": "LONG",
                        "entry_price": 100,
                        "exit_price": 101,
                        "size": 1,
                        "gross_pnl": 10,
                        "commission": 2,
                        "pnl": 9,
                    }
                )
            errors = check_trades(path)
            self.assertTrue(any("pnl mismatch" in e for e in errors))


if __name__ == "__main__":
    unittest.main()

