import json
import os
import tempfile
import unittest
from pathlib import Path

import dashboard


class DashboardTest(unittest.TestCase):
    def test_dashboard_contains_portfolio_blocked(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            output_dir = root / "output"
            portfolio_dir = output_dir / "portfolio"
            portfolio_dir.mkdir(parents=True, exist_ok=True)

            (output_dir / "performance.json").write_text(
                json.dumps({"total_pnl": 123.4}, ensure_ascii=False),
                encoding="utf-8",
            )
            (portfolio_dir / "portfolio_summary.json").write_text(
                json.dumps(
                    {
                        "selected_symbols": ["A", "C"],
                        "blocked_by_corr": [{"symbol": "B", "blocked_by": "A", "corr": 0.95}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            old = os.getcwd()
            os.chdir(root)
            try:
                dashboard.main([])
            finally:
                os.chdir(old)

            html = (output_dir / "dashboard.html").read_text(encoding="utf-8")
            self.assertIn("相关性剔除明细", html)
            self.assertIn("B", html)
            self.assertIn("0.95", html)


if __name__ == "__main__":
    unittest.main()
