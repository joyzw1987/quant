class RiskManager:
    def __init__(
        self,
        stop_loss_percentage=0.02,
        daily_loss_limit=None,
        max_drawdown=None,
        max_drawdown_pct=None,
        max_consecutive_losses=None,
        risk_per_trade=0.01,
        atr_period=14,
        atr_multiplier=2.0,
        take_profit_multiplier=None,
        max_position_size=None,
        max_orders_per_day=None,
        min_seconds_between_orders=0,
        max_total_position=None,
        max_symbol_position=None,
        max_total_notional=None,
        max_symbol_notional=None,
        max_total_exposure_pct=None,
        max_symbol_exposure_pct=None,
        max_slippage=None,
    ):
        self.stop_loss_percentage = stop_loss_percentage
        self.daily_loss_limit = daily_loss_limit
        self.max_drawdown = max_drawdown
        self.max_drawdown_pct = max_drawdown_pct
        self.max_consecutive_losses = max_consecutive_losses
        self.risk_per_trade = risk_per_trade
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.take_profit_multiplier = take_profit_multiplier
        self.max_position_size = max_position_size
        self.max_orders_per_day = max_orders_per_day
        self.min_seconds_between_orders = min_seconds_between_orders
        self.max_total_position = max_total_position
        self.max_symbol_position = max_symbol_position
        self.max_total_notional = max_total_notional
        self.max_symbol_notional = max_symbol_notional
        self.max_total_exposure_pct = max_total_exposure_pct
        self.max_symbol_exposure_pct = max_symbol_exposure_pct
        self.max_slippage = max_slippage

        self.daily_pnl = 0.0
        self.consecutive_losses = 0
        self.peak_equity = None
        self.trading_halted = False
        self.halt_reason = None
        self._atr_values = []
        self.orders_today = 0
        self.last_order_ts = None
        self.connection_ok = True
        self.force_close_triggered = False

    def on_new_day(self):
        self.daily_pnl = 0.0
        self.orders_today = 0
        if self.halt_reason in ("DAILY_LOSS", "SAFETY_DAILY_LOSS"):
            self.trading_halted = False
            self.halt_reason = None
        self.force_close_triggered = False

    def trigger_halt(self, reason):
        self.trading_halted = True
        self.halt_reason = reason

    def allow_trade(self):
        return not self.trading_halted

    def should_force_close(self):
        if not self.trading_halted:
            return False
        if self.force_close_triggered:
            return False
        return self.halt_reason in (
            "MAX_DRAWDOWN",
            "DAILY_LOSS",
            "SAFETY_DAILY_LOSS",
            "KILL_SWITCH",
            "DISCONNECTED",
        )

    def calc_position_size(self, capital, price, atr=None):
        if atr is None or atr <= 0:
            return max(0.0, capital / price * 0.1)
        risk_amount = capital * self.risk_per_trade
        stop_distance = atr * self.atr_multiplier
        size = risk_amount / stop_distance
        return max(0.0, size)

    def get_stop_price(self, entry_price, direction, atr=None):
        if atr is not None and atr > 0:
            if direction == "LONG":
                return entry_price - atr * self.atr_multiplier
            if direction == "SHORT":
                return entry_price + atr * self.atr_multiplier
            return entry_price
        if direction == "LONG":
            return entry_price * (1 - self.stop_loss_percentage)
        if direction == "SHORT":
            return entry_price * (1 + self.stop_loss_percentage)
        return entry_price

    def get_take_profit_price(self, entry_price, direction, atr=None):
        if self.take_profit_multiplier is None:
            return None
        if atr is None or atr <= 0:
            return None
        if direction == "LONG":
            return entry_price + atr * self.take_profit_multiplier
        if direction == "SHORT":
            return entry_price - atr * self.take_profit_multiplier
        return None

    def update_atr(self, bars):
        if len(bars) < 2:
            return None
        current = bars[-1]
        prev_close = bars[-2]["close"]
        tr = max(
            current["high"] - current["low"],
            abs(current["high"] - prev_close),
            abs(current["low"] - prev_close),
        )
        self._atr_values.append(tr)
        if len(self._atr_values) > self.atr_period:
            self._atr_values.pop(0)
        if len(self._atr_values) < self.atr_period:
            return None
        return sum(self._atr_values) / len(self._atr_values)

    def update_equity(self, equity):
        if self.peak_equity is None:
            self.peak_equity = equity
        if equity > self.peak_equity:
            self.peak_equity = equity
        drawdown = self.peak_equity - equity
        drawdown_pct = (drawdown / self.peak_equity) if self.peak_equity else 0.0
        if self.max_drawdown is not None and drawdown >= self.max_drawdown:
            self.trigger_halt("MAX_DRAWDOWN")
        if self.max_drawdown_pct is not None and drawdown_pct >= self.max_drawdown_pct:
            self.trigger_halt("MAX_DRAWDOWN_PCT")
        return drawdown

    def update_after_trade(self, pnl, equity):
        self.daily_pnl += pnl
        if pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        if self.max_consecutive_losses is not None and self.consecutive_losses >= self.max_consecutive_losses:
            self.trigger_halt("MAX_CONSECUTIVE_LOSSES")
        if self.daily_loss_limit is not None and self.daily_pnl <= -self.daily_loss_limit:
            self.trigger_halt("DAILY_LOSS")
        self.update_equity(equity)
