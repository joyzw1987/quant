import unittest

from engine.risk import RiskManager


class RiskManagerTest(unittest.TestCase):
    def test_calc_position_size_with_atr(self):
        risk = RiskManager(risk_per_trade=0.01, atr_multiplier=2.0)
        size = risk.calc_position_size(capital=100000, price=3000, atr=10)
        self.assertAlmostEqual(size, 50.0)

    def test_drawdown_halt(self):
        risk = RiskManager(max_drawdown=1000)
        risk.update_equity(100000)
        risk.update_equity(98800)
        self.assertTrue(risk.trading_halted)
        self.assertEqual(risk.halt_reason, "MAX_DRAWDOWN")

    def test_can_open_order_limits(self):
        risk = RiskManager(max_position_size=5, max_orders_per_day=1)
        self.assertFalse(risk.can_open_order(10))
        self.assertEqual(risk.halt_reason, "MAX_POSITION_SIZE")

        risk.halt_reason = None
        self.assertTrue(risk.can_open_order(2))
        risk.record_order()
        self.assertFalse(risk.can_open_order(2))
        self.assertEqual(risk.halt_reason, "MAX_ORDERS_PER_DAY")

    def test_loss_streak_reduces_position_size(self):
        risk = RiskManager(
            risk_per_trade=0.01,
            atr_multiplier=2.0,
            loss_streak_reduce_ratio=0.5,
            loss_streak_min_multiplier=0.2,
        )
        base_size = risk.calc_position_size(capital=100000, price=3000, atr=10)
        risk.update_after_trade(-100, 99900)
        reduced_size = risk.calc_position_size(capital=100000, price=3000, atr=10)
        self.assertAlmostEqual(base_size, 50.0)
        self.assertAlmostEqual(reduced_size, 25.0)

    def test_volatility_pause_and_resume(self):
        risk = RiskManager(volatility_halt_atr=10.0, volatility_resume_atr=8.0)
        risk.update_volatility_pause(10.5)
        self.assertFalse(risk.allow_trade())
        self.assertEqual(risk.halt_reason, "VOLATILITY_PAUSE")

        risk.update_volatility_pause(7.5)
        self.assertTrue(risk.allow_trade())


if __name__ == "__main__":
    unittest.main()
