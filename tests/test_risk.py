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


if __name__ == "__main__":
    unittest.main()
