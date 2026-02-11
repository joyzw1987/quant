from engine.param_optimizer import evaluate_params_with_drawdown, pick_best_params_scored


def build_windows(total_size, train_size, test_size, step_size=None):
    if total_size <= 0:
        return []
    if train_size <= 0 or test_size <= 0:
        raise ValueError("train_size and test_size must be > 0")
    if step_size is None:
        step_size = test_size
    if step_size <= 0:
        raise ValueError("step_size must be > 0")

    windows = []
    start = 0
    while start + train_size + test_size <= total_size:
        train_start = start
        train_end = start + train_size
        test_start = train_end
        test_end = test_start + test_size
        windows.append(
            {
                "train_start": train_start,
                "train_end": train_end,
                "test_start": test_start,
                "test_end": test_end,
            }
        )
        start += step_size
    return windows


def run_walk_forward(
    prices,
    candidates,
    train_size,
    test_size,
    step_size=None,
    objective="pnl",
    dd_penalty=0.0,
    min_trades=0,
):
    windows = build_windows(len(prices), train_size, test_size, step_size=step_size)
    rows = []
    for idx, window in enumerate(windows, start=1):
        train_prices = prices[window["train_start"]: window["train_end"]]
        test_prices = prices[window["test_start"]: window["test_end"]]

        best, train_score, train_stats = pick_best_params_scored(
            train_prices,
            candidates,
            objective=objective,
            dd_penalty=dd_penalty,
            min_trades=min_trades,
        )

        if not best or not train_stats:
            rows.append(
                {
                    "window": idx,
                    "train_start": window["train_start"],
                    "train_end": window["train_end"],
                    "test_start": window["test_start"],
                    "test_end": window["test_end"],
                    "best_fast": "",
                    "best_slow": "",
                    "train_score": "",
                    "train_pnl": "",
                    "train_max_drawdown": "",
                    "train_trades": "",
                    "test_pnl": "",
                    "test_max_drawdown": "",
                    "test_trades": "",
                }
            )
            continue

        test_stats = evaluate_params_with_drawdown(test_prices, best["fast"], best["slow"])
        if not test_stats:
            test_stats = {"pnl": 0.0, "max_drawdown": 0.0, "trades": 0}

        rows.append(
            {
                "window": idx,
                "train_start": window["train_start"],
                "train_end": window["train_end"],
                "test_start": window["test_start"],
                "test_end": window["test_end"],
                "best_fast": best["fast"],
                "best_slow": best["slow"],
                "train_score": train_score,
                "train_pnl": train_stats["pnl"],
                "train_max_drawdown": train_stats["max_drawdown"],
                "train_trades": train_stats["trades"],
                "test_pnl": test_stats["pnl"],
                "test_max_drawdown": test_stats["max_drawdown"],
                "test_trades": test_stats["trades"],
            }
        )

    valid_rows = [row for row in rows if row["best_fast"] != ""]
    test_pnls = [float(row["test_pnl"]) for row in valid_rows]
    test_drawdowns = [float(row["test_max_drawdown"]) for row in valid_rows]

    summary = {
        "windows_total": len(rows),
        "windows_valid": len(valid_rows),
        "windows_positive": sum(1 for value in test_pnls if value > 0),
        "test_total_pnl": sum(test_pnls),
        "test_avg_pnl": (sum(test_pnls) / len(test_pnls)) if test_pnls else 0.0,
        "test_avg_drawdown": (sum(test_drawdowns) / len(test_drawdowns)) if test_drawdowns else 0.0,
    }
    return {"rows": rows, "summary": summary}
