from typing import List


def _calc_rsi(prices: List[float], period: int):
    if len(prices) < period + 1:
        return None
    gains = 0.0
    losses = 0.0
    for i in range(-period, 0):
        change = prices[i] - prices[i - 1]
        if change >= 0:
            gains += change
        else:
            losses += -change
    if losses == 0:
        return 100.0
    rs = gains / losses
    return 100.0 - (100.0 / (1.0 + rs))


class Strategy:
    def __init__(
        self,
        fast=3,
        slow=8,
        mode="trend",
        min_diff=0.0,
        cooldown_bars=0,
        max_consecutive_losses=None,
        trend_filter=False,
        trend_window=50,
    ):
        self.fast = fast
        self.slow = slow
        self.mode = mode
        self.min_diff = min_diff
        self.cooldown_bars = cooldown_bars
        self.max_consecutive_losses = max_consecutive_losses
        self.trend_filter = trend_filter
        self.trend_window = trend_window
        self._cooldown_until = -1
        self._loss_streak = 0
        self._disabled = False

    def generate_signal(self, prices, step=None):
        if self._disabled:
            return 0
        if step is not None and step <= self._cooldown_until:
            return 0
        if len(prices) < self.slow:
            return 0
        if self.trend_filter and len(prices) < self.trend_window:
            return 0

        fast_ma = sum(prices[-self.fast:]) / self.fast
        slow_ma = sum(prices[-self.slow:]) / self.slow
        diff = fast_ma - slow_ma

        trend_dir = 0
        if self.trend_filter:
            trend_ma = sum(prices[-self.trend_window:]) / self.trend_window
            trend_dir = 1 if prices[-1] > trend_ma else -1 if prices[-1] < trend_ma else 0

        if abs(diff) < self.min_diff:
            return 0

        if self.mode == "trend":
            if fast_ma > slow_ma:
                if self.trend_filter and trend_dir != 1:
                    return 0
                return 1
            if fast_ma < slow_ma:
                if self.trend_filter and trend_dir != -1:
                    return 0
                return -1
            return 0

        if fast_ma > slow_ma:
            if self.trend_filter and trend_dir != -1:
                return 0
            return -1
        if fast_ma < slow_ma:
            if self.trend_filter and trend_dir != 1:
                return 0
            return 1
        return 0

    def set_params(
        self,
        fast=None,
        slow=None,
        mode=None,
        min_diff=None,
        trend_filter=None,
        trend_window=None,
        rsi_period=None,
        rsi_overbought=None,
        rsi_oversold=None,
    ):
        if fast is not None:
            self.fast = fast
        if slow is not None:
            self.slow = slow
        if mode is not None:
            self.mode = mode
        if min_diff is not None:
            self.min_diff = min_diff
        if trend_filter is not None:
            self.trend_filter = trend_filter
        if trend_window is not None:
            self.trend_window = trend_window

    def on_trade_close(self, pnl, step):
        if pnl < 0:
            self._loss_streak += 1
            if self.cooldown_bars:
                self._cooldown_until = max(self._cooldown_until, step + self.cooldown_bars)
        else:
            self._loss_streak = 0
        if self.max_consecutive_losses is not None and self._loss_streak >= self.max_consecutive_losses:
            self._disabled = True

    def on_new_day(self):
        self._loss_streak = 0
        self._disabled = False
        self._cooldown_until = -1


class StrategyComposite:
    def __init__(self, members, weights=None, threshold=0.0):
        self.members = members
        self.weights = weights if weights and len(weights) == len(members) else [1.0] * len(members)
        self.threshold = threshold

    def generate_signal(self, prices, step=None):
        score = 0.0
        for member, weight in zip(self.members, self.weights):
            score += weight * member.generate_signal(prices, step=step)
        if score > self.threshold:
            return 1
        if score < -self.threshold:
            return -1
        return 0

    def set_params(self, **kwargs):
        for member in self.members:
            member.set_params(**kwargs)

    def on_trade_close(self, pnl, step):
        for member in self.members:
            member.on_trade_close(pnl, step)

    def on_new_day(self):
        for member in self.members:
            member.on_new_day()


class RSIMAStrategy:
    def __init__(
        self,
        rsi_period=14,
        rsi_overbought=70,
        rsi_oversold=30,
        fast=5,
        slow=20,
        min_diff=0.0,
        cooldown_bars=0,
        max_consecutive_losses=None,
        trend_filter=False,
        trend_window=50,
    ):
        self.rsi_period = rsi_period
        self.rsi_overbought = rsi_overbought
        self.rsi_oversold = rsi_oversold
        self.fast = fast
        self.slow = slow
        self.min_diff = min_diff
        self.mode = "rsi_ma"
        self.cooldown_bars = cooldown_bars
        self.max_consecutive_losses = max_consecutive_losses
        self.trend_filter = trend_filter
        self.trend_window = trend_window
        self._cooldown_until = -1
        self._loss_streak = 0
        self._disabled = False

    def generate_signal(self, prices, step=None):
        if self._disabled:
            return 0
        if step is not None and step <= self._cooldown_until:
            return 0
        if len(prices) < max(self.slow, self.rsi_period + 1):
            return 0
        if self.trend_filter and len(prices) < self.trend_window:
            return 0

        rsi = _calc_rsi(prices, self.rsi_period)
        if rsi is None:
            return 0

        fast_ma = sum(prices[-self.fast:]) / self.fast
        slow_ma = sum(prices[-self.slow:]) / self.slow
        diff = fast_ma - slow_ma
        if abs(diff) < self.min_diff:
            return 0

        trend_dir = 0
        if self.trend_filter:
            trend_ma = sum(prices[-self.trend_window:]) / self.trend_window
            trend_dir = 1 if prices[-1] > trend_ma else -1 if prices[-1] < trend_ma else 0

        signal = 0
        if rsi <= self.rsi_oversold and fast_ma > slow_ma:
            signal = 1
        elif rsi >= self.rsi_overbought and fast_ma < slow_ma:
            signal = -1

        if self.trend_filter and signal != 0:
            if signal == 1 and trend_dir != 1:
                return 0
            if signal == -1 and trend_dir != -1:
                return 0

        return signal

    def set_params(
        self,
        fast=None,
        slow=None,
        mode=None,
        min_diff=None,
        rsi_period=None,
        rsi_overbought=None,
        rsi_oversold=None,
        trend_filter=None,
        trend_window=None,
    ):
        if fast is not None:
            self.fast = fast
        if slow is not None:
            self.slow = slow
        if mode is not None:
            self.mode = mode
        if min_diff is not None:
            self.min_diff = min_diff
        if rsi_period is not None:
            self.rsi_period = rsi_period
        if rsi_overbought is not None:
            self.rsi_overbought = rsi_overbought
        if rsi_oversold is not None:
            self.rsi_oversold = rsi_oversold
        if trend_filter is not None:
            self.trend_filter = trend_filter
        if trend_window is not None:
            self.trend_window = trend_window

    def on_trade_close(self, pnl, step):
        if pnl < 0:
            self._loss_streak += 1
            if self.cooldown_bars:
                self._cooldown_until = max(self._cooldown_until, step + self.cooldown_bars)
        else:
            self._loss_streak = 0
        if self.max_consecutive_losses is not None and self._loss_streak >= self.max_consecutive_losses:
            self._disabled = True

    def on_new_day(self):
        self._loss_streak = 0
        self._disabled = False
        self._cooldown_until = -1
