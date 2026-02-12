import csv
import json
import os

from engine.portfolio import allocate_weights_with_method, build_corr_matrix
from main import main


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _read_curve(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _returns_from_curve(rows):
    values = [float(r.get("equity", r.get("cash", 0.0))) for r in rows]
    out = []
    prev = None
    for v in values:
        if prev is not None and prev != 0:
            out.append((v - prev) / prev)
        prev = v
    return out


def _normalized_equity(rows):
    values = [float(r.get("equity", r.get("cash", 0.0))) for r in rows]
    if not values or values[0] == 0:
        return []
    base = values[0]
    return [v / base for v in values]


def _max_drawdown(values):
    peak = None
    max_dd = 0.0
    for v in values:
        if peak is None or v > peak:
            peak = v
        dd = peak - v
        if dd > max_dd:
            max_dd = dd
    return max_dd


def main_portfolio():
    cfg = load_config()
    symbols = cfg.get("symbols") or [cfg.get("symbol")]
    symbols = [s for s in symbols if s]
    if not symbols:
        raise SystemExit("no symbols configured")

    portfolio_cfg = cfg.get("portfolio", {})
    corr_limit = float(portfolio_cfg.get("max_corr", 0.8))
    weight_method = str(portfolio_cfg.get("weight_method", "equal")).lower()
    out_dir = portfolio_cfg.get("output_dir", os.path.join("output", "portfolio"))
    os.makedirs(out_dir, exist_ok=True)

    perf_map = {}
    curve_map = {}
    returns_map = {}

    for sym in symbols:
        sym_out = os.path.join(out_dir, sym)
        os.makedirs(sym_out, exist_ok=True)
        main(symbol_override=sym, output_dir=sym_out)

        perf_path = os.path.join(sym_out, "performance.json")
        curve_path = os.path.join(sym_out, "equity_curve.csv")
        if not (os.path.exists(perf_path) and os.path.exists(curve_path)):
            continue
        with open(perf_path, "r", encoding="utf-8") as f:
            perf_map[sym] = json.load(f)
        rows = _read_curve(curve_path)
        curve_map[sym] = rows
        returns_map[sym] = _returns_from_curve(rows)

    symbols = [s for s in symbols if s in perf_map and s in curve_map]
    if not symbols:
        raise SystemExit("no valid symbol results")

    corr = build_corr_matrix(returns_map)
    weights, selected, weight_meta = allocate_weights_with_method(
        symbols=symbols,
        corr_matrix=corr,
        return_map=returns_map,
        max_corr=corr_limit,
        weight_method=weight_method,
    )

    initial_capital = float(cfg.get("backtest", {}).get("initial_capital", 100000))
    combined_pnl = sum(float(perf_map[s].get("total_pnl", 0.0)) * float(weights.get(s, 0.0)) for s in symbols)

    norm_map = {s: _normalized_equity(curve_map[s]) for s in symbols}
    min_len = min((len(v) for v in norm_map.values() if v), default=0)
    portfolio_equity = []
    for i in range(min_len):
        ratio = sum(float(weights[s]) * norm_map[s][i] for s in symbols if len(norm_map[s]) >= min_len)
        equity = initial_capital * ratio
        portfolio_equity.append(equity)
    max_dd = _max_drawdown(portfolio_equity)

    summary = {
        "symbols": symbols,
        "selected_symbols": selected,
        "max_corr": corr_limit,
        "weight_method": weight_method,
        "weight_meta": weight_meta,
        "weights": weights,
        "correlation": corr,
        "initial_capital": initial_capital,
        "final_capital": initial_capital + combined_pnl,
        "total_pnl": combined_pnl,
        "max_drawdown": max_dd,
    }

    with open(os.path.join(out_dir, "portfolio_summary.json"), "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    curve_out = os.path.join(out_dir, "portfolio_equity.csv")
    with open(curve_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "equity"])
        for i, v in enumerate(portfolio_equity):
            writer.writerow([i, v])

    print(f"[PORTFOLIO] symbols={len(symbols)} selected={len(selected)}")
    print(f"[PORTFOLIO] summary={os.path.join(out_dir, 'portfolio_summary.json')}")
    print(f"[PORTFOLIO] curve={curve_out}")


if __name__ == "__main__":
    main_portfolio()
