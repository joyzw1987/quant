def evaluate_params(prices, fast, slow):
    if len(prices) < slow + 2:
        return None
    position = 0
    entry = 0.0
    pnl = 0.0
    for i in range(slow, len(prices)):
        fast_ma = sum(prices[i - fast:i]) / fast
        slow_ma = sum(prices[i - slow:i]) / slow
        signal = 1 if fast_ma > slow_ma else -1 if fast_ma < slow_ma else 0
        if position == 0 and signal != 0:
            position = signal
            entry = prices[i]
        elif position != 0 and signal != 0 and signal != position:
            pnl += (prices[i] - entry) * position
            position = signal
            entry = prices[i]
    if position != 0:
        pnl += (prices[-1] - entry) * position
    return pnl


def evaluate_params_with_drawdown(prices, fast, slow):
    if len(prices) < slow + 2:
        return None
    position = 0
    entry = 0.0
    pnl = 0.0
    equity = 0.0
    peak = 0.0
    max_dd = 0.0
    trades = 0
    for i in range(slow, len(prices)):
        fast_ma = sum(prices[i - fast:i]) / fast
        slow_ma = sum(prices[i - slow:i]) / slow
        signal = 1 if fast_ma > slow_ma else -1 if fast_ma < slow_ma else 0
        if position == 0 and signal != 0:
            position = signal
            entry = prices[i]
        elif position != 0 and signal != 0 and signal != position:
            pnl += (prices[i] - entry) * position
            equity = pnl
            peak = max(peak, equity)
            max_dd = max(max_dd, peak - equity)
            trades += 1
            position = signal
            entry = prices[i]
    if position != 0:
        pnl += (prices[-1] - entry) * position
        equity = pnl
        peak = max(peak, equity)
        max_dd = max(max_dd, peak - equity)
        trades += 1
    return {"pnl": pnl, "max_drawdown": max_dd, "trades": trades}


def pick_best_params_scored(prices, candidates, objective="pnl", dd_penalty=0.0, min_trades=0):
    best = None
    best_score = None
    best_stats = None
    for c in candidates:
        stats = evaluate_params_with_drawdown(prices, c["fast"], c["slow"])
        if stats is None:
            continue
        if stats["trades"] < min_trades:
            continue
        score = stats["pnl"] - dd_penalty * stats["max_drawdown"] if objective == "pnl_dd" else stats["pnl"]
        if best_score is None or score > best_score:
            best_score = score
            best = c
            best_stats = stats
    return best, best_score, best_stats


def pick_best_params(prices, candidates):
    best = None
    best_score = None
    for c in candidates:
        score = evaluate_params(prices, c["fast"], c["slow"])
        if score is None:
            continue
        if best_score is None or score > best_score:
            best_score = score
            best = c
    return best, best_score
