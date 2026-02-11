import unittest

from engine.strategy import Strategy, RSIMAStrategy


class StrategyTest(unittest.TestCase):
    def test_ma_trend_signal(self):
        s = Strategy(fast=3, slow=5, mode="trend", min_diff=0.1)
        prices = [10, 11, 12, 13, 14, 15]
        self.assertEqual(s.generate_signal(prices), 1)

    def test_rsi_strategy_returns_signal_or_zero(self):
        s = RSIMAStrategy(fast=3, slow=5, rsi_period=3, rsi_overbought=55, rsi_oversold=45)
        prices = [10, 11, 12, 13, 12, 11, 10, 11, 12]
        self.assertIn(s.generate_signal(prices), (-1, 0, 1))


if __name__ == "__main__":
    unittest.main()
