from engine.strategy import RSIMAStrategy
from engine.walk_forward import build_windows


def evaluate_rsi_ma_params_with_drawdown(prices, params):
    slow = int(params.get("slow", 20))
    rsi_period = int(params.get("rsi_period", 14))
    min_required = max(slow, rsi_period + 1)
    if len(prices) < min_required:
        return None

    strategy = RSIMAStrategy(
        rsi_period=rsi_period,
        rsi_overbought=float(params.get("rsi_overbought", 70)),
        rsi_oversold=float(params.get("rsi_oversold", 30)),
        fast=int(params.get("fast", 5)),
        slow=slow,
        min_diff=float(params.get("min_diff", 0.0)),
        cooldown_bars=int(params.get("cooldown_bars", 0)),
        max_consecutive_losses=params.get("max_consecutive_losses"),
        trend_filter=bool(params.get("trend_filter", False)),
        trend_window=int(params.get("trend_window", 50)),
    )

    position = 0
    entry = 0.0
    pnl = 0.0
    peak = 0.0
    max_dd = 0.0
    trades = 0

    for i in range(min_required - 1, len(prices)):
        signal = strategy.generate_signal(prices[: i + 1], step=i)
        price = prices[i]

        if position == 0 and signal != 0:
            position = signal
            entry = price
            continue

        if position != 0 and signal != 0 and signal != position:
            trade_pnl = (price - entry) * position
            pnl += trade_pnl
            peak = max(peak, pnl)
            max_dd = max(max_dd, peak - pnl)
            trades += 1
            strategy.on_trade_close(trade_pnl, i)

            position = signal
            entry = price

    if position != 0:
        trade_pnl = (prices[-1] - entry) * position
        pnl += trade_pnl
        peak = max(peak, pnl)
        max_dd = max(max_dd, peak - pnl)
        trades += 1

    return {"pnl": pnl, "max_drawdown": max_dd, "trades": trades}


def evaluate_candidate_walk_forward(
    prices,
    candidate,
    train_size,
    test_size,
    step_size,
    base_params,
    min_trades=0,
):
    windows = build_windows(len(prices), train_size, test_size, step_size=step_size)
    test_pnls = []
    test_drawdowns = []
    windows_valid = 0

    merged = dict(base_params)
    merged["fast"] = candidate["fast"]
    merged["slow"] = candidate["slow"]

    for window in windows:
        train_prices = prices[window["train_start"]: window["train_end"]]
        test_prices = prices[window["test_start"]: window["test_end"]]
        train_stats = evaluate_rsi_ma_params_with_drawdown(train_prices, merged)
        if not train_stats or train_stats["trades"] < min_trades:
            continue
        test_stats = evaluate_rsi_ma_params_with_drawdown(test_prices, merged)
        if not test_stats:
            continue
        windows_valid += 1
        test_pnls.append(float(test_stats["pnl"]))
        test_drawdowns.append(float(test_stats["max_drawdown"]))

    return {
        "windows_total": len(windows),
        "windows_valid": windows_valid,
        "windows_positive": sum(1 for value in test_pnls if value > 0),
        "test_total_pnl": sum(test_pnls),
        "test_avg_pnl": (sum(test_pnls) / len(test_pnls)) if test_pnls else 0.0,
        "test_avg_drawdown": (sum(test_drawdowns) / len(test_drawdowns)) if test_drawdowns else 0.0,
    }
