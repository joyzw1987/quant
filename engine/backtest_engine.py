import os
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
    safety_cfg=None,
):
    capital = initial_capital
    equity_curve = []
    daily_trade_count = 0
    current_date = None
    last_gate_reason = None

    safety_cfg = safety_cfg or {}
    kill_switch_file = safety_cfg.get("kill_switch_file", "")
    safety_max_daily_loss = safety_cfg.get("max_daily_loss")

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
                    "capital": capital,
                    "position": execution.position,
                    "trades": len(execution.trades),
                    "halt_reason": risk.halt_reason,
                    "gate_reason": last_gate_reason,
                }
            )

        def block_by(reason):
            nonlocal last_gate_reason
            last_gate_reason = reason
            if runtime_update:
                runtime_update(
                    {
                        "event": "gate_block",
                        "last_step": step,
                        "last_bar_time": bar["datetime"],
                        "symbol": symbol,
                        "gate_reason": reason,
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
                runtime_update(
                    {
                        "event": "new_day",
                        "trading_day": str(bar_date),
                        "capital": capital,
                        "position": execution.position,
                        "trades": len(execution.trades),
                    }
                )

        if kill_switch_file and os.path.exists(kill_switch_file):
            risk.trigger_halt("KILL_SWITCH")
            if runtime_update:
                runtime_update(
                    {
                        "event": "safety_kill_switch",
                        "last_step": step,
                        "last_bar_time": bar["datetime"],
                        "symbol": symbol,
                        "halt_reason": risk.halt_reason,
                    }
                )

        if safety_max_daily_loss is not None and risk.daily_pnl <= -abs(float(safety_max_daily_loss)):
            risk.trigger_halt("SAFETY_DAILY_LOSS")

        if execution.position is not None and hasattr(risk, "should_force_close") and risk.should_force_close():
            pnl = execution.force_close(price, bar_time=bar["datetime"])
            capital += pnl
            risk.update_after_trade(pnl, capital)
            risk.force_close_triggered = True
            if runtime_update and execution.trades:
                runtime_update(
                    {
                        "event": "force_close",
                        "capital": capital,
                        "position": execution.position,
                        "trades": len(execution.trades),
                        "last_trade": execution.trades[-1],
                        "halt_reason": risk.halt_reason,
                    }
                )
            append_equity(step, bar["datetime"])
            continue

        if not schedule_checker(bar_dt, schedule):
            block_by("SCHEDULE_CLOSED")
            append_equity(step, bar["datetime"])
            continue

        if trade_start and bar_dt.time() < trade_start:
            block_by("BEFORE_TRADE_START")
            append_equity(step, bar["datetime"])
            continue
        if trade_end and bar_dt.time() > trade_end:
            block_by("AFTER_TRADE_END")
            append_equity(step, bar["datetime"])
            continue

        atr = risk.update_atr(bars[: step + 1])
        if hasattr(risk, "update_volatility_pause"):
            risk.update_volatility_pause(atr)

        if execution.position is not None:
            closed, pnl = execution.check_exit(price, risk, bar_time=bar["datetime"])
            if closed:
                capital += pnl
                risk.update_after_trade(pnl, capital)
                if hasattr(strategy, "on_trade_close"):
                    strategy.on_trade_close(pnl, step)
                if runtime_update and execution.trades:
                    runtime_update(
                        {
                            "event": "trade_close",
                            "capital": capital,
                            "position": execution.position,
                            "trades": len(execution.trades),
                            "last_trade": execution.trades[-1],
                        }
                    )
            append_equity(step, bar["datetime"])
            continue

        if daily_trade_count >= max_trades_per_day:
            block_by("MAX_TRADES_PER_DAY")
            append_equity(step, bar["datetime"])
            continue

        if not risk.allow_trade():
            block_by("RISK_NOT_ALLOWED")
            append_equity(step, bar["datetime"])
            continue

        if atr is not None and atr < strategy_cfg.get("min_atr", 0.0):
            block_by("MIN_ATR")
            append_equity(step, bar["datetime"])
            continue

        prices = [b["close"] for b in bars[: step + 1]]
        signal = strategy.generate_signal(prices, step=step)
        if signal == 0:
            block_by("NO_SIGNAL")
            append_equity(step, bar["datetime"])
            continue

        position_size = risk.calc_position_size(capital, price, atr)
        if position_size <= 0:
            block_by("POSITION_SIZE_ZERO")
            append_equity(step, bar["datetime"])
            continue

        if hasattr(risk, "can_open_order") and not risk.can_open_order(position_size):
            block_by("RISK_ORDER_LIMIT")
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
            last_gate_reason = None
            daily_trade_count += 1
            if hasattr(risk, "record_order"):
                risk.record_order()
            if runtime_update:
                runtime_update(
                    {
                        "event": "trade_open",
                        "signal": signal,
                        "capital": capital,
                        "position": execution.position,
                        "trades": len(execution.trades),
                    }
                )

        append_equity(step, bar["datetime"])

    if execution.position is not None:
        pnl = execution.force_close(bars[-1]["close"], bar_time=bars[-1]["datetime"])
        capital += pnl
        risk.update_after_trade(pnl, capital)
        if runtime_update and execution.trades:
            runtime_update(
                {
                    "event": "force_close",
                    "capital": capital,
                    "position": execution.position,
                    "trades": len(execution.trades),
                    "last_trade": execution.trades[-1],
                }
            )

    if runtime_update:
        last_bar = bars[-1] if bars else {}
        runtime_update(
            {
                "event": "finished",
                "last_step": (len(bars) - 1) if bars else -1,
                "last_bar_time": last_bar.get("datetime"),
                "last_price": last_bar.get("close"),
                "capital": capital,
                "position": execution.position,
                "trades": len(execution.trades),
            }
        )

    return {
        "capital": capital,
        "equity_curve": equity_curve,
    }
