import unittest
from unittest.mock import patch

import run


class RunEntryTest(unittest.TestCase):
    @patch("run.report_validation")
    @patch("run.validate_config", return_value=([], []))
    @patch("run.run_portfolio")
    @patch("run.load_config", return_value={"symbol": "M2609"})
    def test_mode_portfolio(self, _load, run_portfolio, validate_config, _report):
        with patch("sys.argv", ["run.py", "--mode", "portfolio"]):
            run.main()
        run_portfolio.assert_called_once()
        validate_config.assert_called_once()
        self.assertEqual(validate_config.call_args.kwargs.get("mode"), "paper")

    @patch("run.report_validation")
    @patch("run.validate_config", return_value=([], []))
    @patch("run.run_all")
    @patch("run.load_config", return_value={"symbol": "M2609"})
    def test_mode_all(self, _load, run_all, validate_config, _report):
        with patch("sys.argv", ["run.py", "--mode", "all"]):
            run.main()
        run_all.assert_called_once()
        validate_config.assert_called_once()
        self.assertEqual(validate_config.call_args.kwargs.get("mode"), "paper")

    @patch("run.report_validation")
    @patch("run.validate_config", return_value=([], []))
    @patch("run.run_paper_check")
    @patch("run.load_config", return_value={"symbol": "M2609"})
    def test_mode_paper_check(self, _load, run_paper_check, validate_config, _report):
        with patch("sys.argv", ["run.py", "--mode", "paper_check"]):
            run.main()
        run_paper_check.assert_called_once()
        validate_config.assert_called_once()

    @patch("run.report_validation")
    @patch("run.validate_config", return_value=([], []))
    @patch("run.run_e2e")
    @patch("run.load_config", return_value={"symbol": "M2609"})
    def test_mode_e2e(self, _load, run_e2e, validate_config, _report):
        with patch("sys.argv", ["run.py", "--mode", "e2e"]):
            run.main()
        run_e2e.assert_called_once()
        validate_config.assert_called_once()

    @patch("run.report_validation")
    @patch("run.validate_config", return_value=([], []))
    @patch("run.run_sim")
    @patch("run.load_config", return_value={"symbol": "M2609"})
    def test_default_mode_sim(self, load_config, run_sim, validate_config, _report):
        with patch("sys.argv", ["run.py"]):
            run.main()
        run_sim.assert_called_once()
        cfg = load_config.return_value
        self.assertEqual(run_sim.call_args.args[0], cfg)
        self.assertEqual(validate_config.call_args.kwargs.get("mode"), "paper")


if __name__ == "__main__":
    unittest.main()
