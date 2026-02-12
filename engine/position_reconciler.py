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
    for k, v in local_snapshot.items():
        if k not in broker_summary and v != 0:
            diffs[k] = {"local": v, "broker": 0}
    return diffs


def diff_account(local_account, broker_account, tolerance=1e-6):
    diffs = {}
    keys = set((local_account or {}).keys()) | set((broker_account or {}).keys())
    for key in keys:
        lv = (local_account or {}).get(key)
        bv = (broker_account or {}).get(key)
        if lv is None or bv is None:
            if lv != bv:
                diffs[key] = {"local": lv, "broker": bv}
            continue
        try:
            if abs(float(lv) - float(bv)) > tolerance:
                diffs[key] = {"local": lv, "broker": bv}
        except Exception:
            if lv != bv:
                diffs[key] = {"local": lv, "broker": bv}
    return diffs
