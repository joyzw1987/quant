import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import e2e_regression


class E2ERegressionTest(unittest.TestCase):
    def test_main_quick_success(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "data").mkdir(parents=True, exist_ok=True)
            (root / "data" / "M2609.csv").write_text(
                "datetime,open,high,low,close\n2026-02-12 09:00:00,100,101,99,100\n",
                encoding="utf-8",
            )
            out_dir = root / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            def fake_step(name, cmd):
                if name == "backtest_main":
                    (out_dir / "performance.json").write_text("{}", encoding="utf-8")
                    (out_dir / "equity_curve.csv").write_text("step,equity\n0,100000\n", encoding="utf-8")
                if name == "weekly_report":
                    (out_dir / "weekly_report.json").write_text("{}", encoding="utf-8")
                if name == "monthly_report":
                    (out_dir / "monthly_report.json").write_text("{}", encoding="utf-8")
                if name == "single_report":
                    (out_dir / "report.html").write_text("<html></html>", encoding="utf-8")
                return {
                    "name": name,
                    "cmd": cmd,
                    "returncode": 0,
                    "elapsed_sec": 0.01,
                    "stdout": "",
                    "stderr": "",
                }

            old_cwd = os.getcwd()
            os.chdir(root)
            try:
                with patch("e2e_regression._run_step", side_effect=fake_step):
                    with patch(
                        "sys.argv",
                        [
                            "e2e_regression.py",
                            "--symbol",
                            "M2609",
                            "--output-dir",
                            str(out_dir),
                            "--quick",
                        ],
                    ):
                        e2e_regression.main()
            finally:
                os.chdir(old_cwd)

            report = json.loads((out_dir / "e2e_regression_report.json").read_text(encoding="utf-8"))
            self.assertTrue(report["ok"])
            self.assertEqual(len(report["steps"]), 5)

    def test_main_auto_generate_when_data_missing(self):
        with tempfile.TemporaryDirectory() as d:
            out_dir = Path(d) / "out"
            old_cwd = os.getcwd()
            os.chdir(d)
            try:
                def fake_step(name, cmd):
                    out_dir.mkdir(parents=True, exist_ok=True)
                    if name == "backtest_main":
                        (out_dir / "performance.json").write_text("{}", encoding="utf-8")
                        (out_dir / "equity_curve.csv").write_text("step,equity\n0,100000\n", encoding="utf-8")
                    if name == "weekly_report":
                        (out_dir / "weekly_report.json").write_text("{}", encoding="utf-8")
                    if name == "monthly_report":
                        (out_dir / "monthly_report.json").write_text("{}", encoding="utf-8")
                    if name == "single_report":
                        (out_dir / "report.html").write_text("<html></html>", encoding="utf-8")
                    return {
                        "name": name,
                        "cmd": cmd,
                        "returncode": 0,
                        "elapsed_sec": 0.01,
                        "stdout": "",
                        "stderr": "",
                    }

                with patch("e2e_regression._run_step", side_effect=fake_step):
                    with patch(
                        "sys.argv",
                        ["e2e_regression.py", "--symbol", "M2609", "--output-dir", str(out_dir), "--quick"],
                    ):
                        e2e_regression.main()
                self.assertTrue((Path(d) / "data" / "M2609.csv").exists())
            finally:
                os.chdir(old_cwd)

    def test_main_fail_when_data_missing_and_required(self):
        with tempfile.TemporaryDirectory() as d:
            old_cwd = os.getcwd()
            os.chdir(d)
            try:
                with patch(
                    "sys.argv",
                    [
                        "e2e_regression.py",
                        "--symbol",
                        "M2609",
                        "--output-dir",
                        "out",
                        "--require-existing-data",
                    ],
                ):
                    with self.assertRaises(SystemExit):
                        e2e_regression.main()
            finally:
                os.chdir(old_cwd)


if __name__ == "__main__":
    unittest.main()
