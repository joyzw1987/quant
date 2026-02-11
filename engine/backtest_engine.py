from datetime import datetime


def run_backtest(
    bars,
    strategy,
    risk,
    execution,
    strategy_cfg,
    symbol,
    max_trades_per_day,
    trade_start,
    trade_end,
    schedule,
    initial_capital,
    schedule_checker,
    runtime_update=None,
):
    capital = initial_capital
    equity_curve = []
    daily_trade_count = 0
    current_date = None

    def append_equity(step, bar_time):
        equity_curve.append(
            {
                "step": step,
                "cash": capital,
                "unrealized": 0,
                "equity": capital,
                "drawdown": 0,
                "datetime": bar_time,
            }
        )

    for step, bar in enumerate(bars):
        price = bar["close"]
        bar_dt = datetime.strptime(bar["datetime"], "%Y-%m-%d %H:%M")
        bar_date = bar_dt.date()
        if runtime_update:
            runtime_update(
                {
                    "last_step": step,
                    "last_bar_time": bar["datetime"],
                    "last_price": price,
                    "halt_reason": risk.halt_reason,
                }
            )

        if current_date is None or bar_date != current_date:
            current_date = bar_date
            daily_trade_count = 0
            risk.on_new_day()
            if hasattr(strategy, "on_new_day"):
                strategy.on_new_day()
            if runtime_update:
                runtime_update({"event": "new_day", "trading_day": str(bar_date)})

        if not schedule_checker(bar_dt, schedule):
            append_equity(step, bar["datetime"])
            continue

        if trade_start and bar_dt.time() < trade_start:
            append_equity(step, bar["datetime"])
            continue
        if trade_end and bar_dt.time() > trade_end:
            append_equity(step, bar["datetime"])
            continue

        if execution.position is not None:
            closed, pnl = execution.check_exit(price, risk, bar_time=bar["datetime"])
            if closed:
                capital += pnl
                risk.update_after_trade(pnl, capital)
                if hasattr(strategy, "on_trade_close"):
                    strategy.on_trade_close(pnl, step)
            append_equity(step, bar["datetime"])
            continue

        if daily_trade_count >= max_trades_per_day:
            append_equity(step, bar["datetime"])
            continue

        if not risk.allow_trade():
            append_equity(step, bar["datetime"])
            continue

        prices = [b["close"] for b in bars[: step + 1]]
        atr = risk.update_atr(bars[: step + 1])
        if atr is not None and atr < strategy_cfg.get("min_atr", 0.0):
            append_equity(step, bar["datetime"])
            continue

        signal = strategy.generate_signal(prices, step=step)
        if signal == 0:
            append_equity(step, bar["datetime"])
            continue

        position_size = risk.calc_position_size(capital, price, atr)
        if position_size <= 0:
            append_equity(step, bar["datetime"])
            continue

        if hasattr(risk, "can_open_order") and not risk.can_open_order(position_size):
            append_equity(step, bar["datetime"])
            continue

        opened = execution.send_order(
            symbol,
            signal,
            price,
            position_size,
            atr=atr,
            risk=risk,
            bar_time=bar["datetime"],
        )
        if opened:
            daily_trade_count += 1
            if hasattr(risk, "record_order"):
                risk.record_order()

        append_equity(step, bar["datetime"])

    if execution.position is not None:
        pnl = execution.force_close(bars[-1]["close"], bar_time=bars[-1]["datetime"])
        capital += pnl
        risk.update_after_trade(pnl, capital)

    return {
        "capital": capital,
        "equity_curve": equity_curve,
    }
