def summarize_positions(positions):
    summary = {}
    for p in positions or []:
        symbol = p.get("symbol")
        qty = p.get("qty", 0)
        summary[symbol] = summary.get(symbol, 0) + qty
    return summary


def diff_positions(local_snapshot, broker_summary):
    diffs = {}
    for k, v in broker_summary.items():
        if local_snapshot.get(k) != v:
            diffs[k] = {"local": local_snapshot.get(k, 0), "broker": v}
    return diffs
