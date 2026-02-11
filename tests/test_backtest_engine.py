import unittest

from engine.backtest_engine import run_backtest
from engine.execution_sim import SimExecution
from engine.risk import RiskManager


class _NoTradeStrategy:
    def generate_signal(self, prices, step=None):
        return 0

    def on_new_day(self):
        return None


class _AlwaysLongStrategy:
    def generate_signal(self, prices, step=None):
        return 1

    def on_new_day(self):
        return None


class BacktestEngineTest(unittest.TestCase):
    def test_no_trade_path(self):
        bars = [
            {"datetime": "2026-02-09 09:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-09 09:01", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-09 09:02", "open": 100, "high": 101, "low": 99, "close": 100},
        ]
        strategy = _NoTradeStrategy()
        risk = RiskManager()
        execution = SimExecution(slippage=0)

        result = run_backtest(
            bars=bars,
            strategy=strategy,
            risk=risk,
            execution=execution,
            strategy_cfg={"min_atr": 0.0},
            symbol="M2609",
            max_trades_per_day=5,
            trade_start=None,
            trade_end=None,
            schedule=None,
            initial_capital=100000,
            schedule_checker=lambda dt, schedule: True,
            runtime_update=None,
        )

        self.assertEqual(result["capital"], 100000)
        self.assertEqual(len(result["equity_curve"]), len(bars))
        self.assertEqual(len(execution.trades), 0)

    def test_order_limits_block_open(self):
        bars = [
            {"datetime": "2026-02-09 09:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-09 09:01", "open": 100, "high": 101, "low": 99, "close": 101},
            {"datetime": "2026-02-09 09:02", "open": 101, "high": 102, "low": 100, "close": 102},
        ]
        strategy = _AlwaysLongStrategy()
        risk = RiskManager(max_orders_per_day=0)
        execution = SimExecution(slippage=0)

        result = run_backtest(
            bars=bars,
            strategy=strategy,
            risk=risk,
            execution=execution,
            strategy_cfg={"min_atr": 0.0},
            symbol="M2609",
            max_trades_per_day=5,
            trade_start=None,
            trade_end=None,
            schedule=None,
            initial_capital=100000,
            schedule_checker=lambda dt, schedule: True,
            runtime_update=None,
        )

        self.assertEqual(result["capital"], 100000)
        self.assertEqual(len(execution.trades), 0)

    def test_runtime_callback_receives_bar_context(self):
        bars = [
            {"datetime": "2026-02-09 09:00", "open": 100, "high": 101, "low": 99, "close": 100},
            {"datetime": "2026-02-09 09:01", "open": 100, "high": 101, "low": 99, "close": 100},
        ]
        strategy = _NoTradeStrategy()
        risk = RiskManager()
        execution = SimExecution(slippage=0)
        snapshots = []

        def runtime_update(payload):
            snapshots.append(payload)

        run_backtest(
            bars=bars,
            strategy=strategy,
            risk=risk,
            execution=execution,
            strategy_cfg={"min_atr": 0.0},
            symbol="M2609",
            max_trades_per_day=5,
            trade_start=None,
            trade_end=None,
            schedule=None,
            initial_capital=100000,
            schedule_checker=lambda dt, schedule: True,
            runtime_update=runtime_update,
        )

        self.assertTrue(any("last_step" in s for s in snapshots))
        self.assertTrue(any(s.get("event") == "new_day" for s in snapshots))


if __name__ == "__main__":
    unittest.main()
