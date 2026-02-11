from collections import defaultdict


def _month_key(dt_value):
    if not dt_value:
        return ""
    text = str(dt_value)
    if len(text) >= 7:
        return text[:7]
    return ""


def _month_drawdown(equities):
    peak = None
    max_dd = 0.0
    for value in equities:
        if peak is None or value > peak:
            peak = value
        dd = peak - value
        if dd > max_dd:
            max_dd = dd
    return max_dd


def build_monthly_metrics(equity_rows, trade_rows):
    monthly_equity = defaultdict(list)
    for row in equity_rows:
        month = _month_key(row.get("datetime"))
        if not month:
            continue
        monthly_equity[month].append(float(row.get("equity", 0.0)))

    monthly_trades = defaultdict(list)
    for trade in trade_rows:
        month = _month_key(trade.get("exit_time"))
        if not month:
            continue
        monthly_trades[month].append(float(trade.get("pnl", 0.0)))

    all_months = sorted(set(monthly_equity.keys()) | set(monthly_trades.keys()))
    rows = []
    for month in all_months:
        eq = monthly_equity.get(month, [])
        tr = monthly_trades.get(month, [])

        start_equity = eq[0] if eq else 0.0
        end_equity = eq[-1] if eq else 0.0
        return_pct = ((end_equity - start_equity) / start_equity * 100.0) if start_equity else 0.0
        max_dd = _month_drawdown(eq) if eq else 0.0

        trade_count = len(tr)
        win_count = sum(1 for value in tr if value > 0)
        win_rate = (win_count / trade_count * 100.0) if trade_count else 0.0
        total_pnl = sum(tr)

        rows.append(
            {
                "month": month,
                "start_equity": start_equity,
                "end_equity": end_equity,
                "return_pct": return_pct,
                "max_drawdown": max_dd,
                "trade_count": trade_count,
                "win_rate": win_rate,
                "pnl": total_pnl,
            }
        )
    return rows
