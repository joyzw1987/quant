import csv
import json
import os
from datetime import datetime

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


def _returns_from_norm(norm_values):
    if not norm_values:
        return []
    out = [0.0]
    for i in range(1, len(norm_values)):
        prev = norm_values[i - 1]
        now = norm_values[i]
        if prev == 0:
            out.append(0.0)
        else:
            out.append((now / prev) - 1.0)
    return out


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


def _period_key(datetime_text, mode):
    mode = str(mode or "none").lower()
    if mode == "none":
        return "all"
    text = str(datetime_text or "")
    date_text = text[:10]
    try:
        d = datetime.strptime(date_text, "%Y-%m-%d")
    except Exception:
        return "unknown"
    if mode == "weekly":
        y, w, _ = d.isocalendar()
        return f"{y}-W{w:02d}"
    if mode == "monthly":
        return f"{d.year}-{d.month:02d}"
    return "all"


def _resolve_symbols(cfg):
    portfolio_cfg = cfg.get("portfolio", {}) if isinstance(cfg, dict) else {}
    symbols = portfolio_cfg.get("symbols")
    if not isinstance(symbols, list) or not symbols:
        symbols = cfg.get("symbols") if isinstance(cfg, dict) else None
    if not isinstance(symbols, list) or not symbols:
        symbols = [cfg.get("symbol")] if isinstance(cfg, dict) else []

    out = []
    seen = set()
    for s in symbols:
        if not s:
            continue
        sym = str(s).strip()
        if not sym or sym in seen:
            continue
        seen.add(sym)
        out.append(sym)
    return out


def _simulate_portfolio(
    symbols,
    dates,
    aligned_returns,
    initial_capital,
    corr_limit,
    weight_method,
    rebalance_mode,
    min_rebalance_bars,
):
    base_return_map = {s: aligned_returns[s][1:] for s in symbols}
    base_corr = build_corr_matrix(base_return_map)
    weights, selected, weight_meta = allocate_weights_with_method(
        symbols=symbols,
        corr_matrix=base_corr,
        return_map=base_return_map,
        max_corr=corr_limit,
        weight_method=weight_method,
    )
    weight_events = [
        {
            "step": 0,
            "datetime": dates[0] if dates else "",
            "reason": "initial",
            "weights": weights,
            "selected_symbols": selected,
            "meta": weight_meta,
        }
    ]

    equity = [initial_capital]
    current_weights = dict(weights)
    current_period = _period_key(dates[0] if dates else "", rebalance_mode)

    for i in range(1, len(dates)):
        new_period = _period_key(dates[i], rebalance_mode)
        if rebalance_mode != "none" and new_period != current_period and i >= min_rebalance_bars:
            hist_returns = {s: aligned_returns[s][1:i] for s in symbols}
            corr = build_corr_matrix(hist_returns)
            current_weights, selected, weight_meta = allocate_weights_with_method(
                symbols=symbols,
                corr_matrix=corr,
                return_map=hist_returns,
                max_corr=corr_limit,
                weight_method=weight_method,
            )
            weight_events.append(
                {
                    "step": i,
                    "datetime": dates[i],
                    "reason": f"rebalance_{rebalance_mode}",
                    "weights": current_weights,
                    "selected_symbols": selected,
                    "meta": weight_meta,
                }
            )
            current_period = new_period

        portfolio_ret = sum(float(current_weights.get(s, 0.0)) * float(aligned_returns[s][i]) for s in symbols)
        equity.append(equity[-1] * (1.0 + portfolio_ret))

    return equity, weight_events, base_corr


def main_portfolio():
    cfg = load_config()
    symbols = _resolve_symbols(cfg)
    if not symbols:
        raise SystemExit("no symbols configured")

    portfolio_cfg = cfg.get("portfolio", {})
    corr_limit = float(portfolio_cfg.get("max_corr", 0.8))
    weight_method = str(portfolio_cfg.get("weight_method", "equal")).lower()
    rebalance_mode = str(portfolio_cfg.get("rebalance", "none")).lower()
    min_rebalance_bars = int(portfolio_cfg.get("min_rebalance_bars", 100))
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

    initial_capital = float(cfg.get("backtest", {}).get("initial_capital", 100000))

    norm_map = {s: _normalized_equity(curve_map[s]) for s in symbols}
    min_len = min((len(v) for v in norm_map.values() if v), default=0)
    if min_len == 0:
        raise SystemExit("no aligned equity series")

    symbols = [s for s in symbols if len(norm_map.get(s, [])) >= min_len]
    dates = [curve_map[symbols[0]][i].get("datetime", "") for i in range(min_len)]
    aligned_returns = {s: _returns_from_norm(norm_map[s][:min_len]) for s in symbols}

    portfolio_equity, weight_events, corr = _simulate_portfolio(
        symbols=symbols,
        dates=dates,
        aligned_returns=aligned_returns,
        initial_capital=initial_capital,
        corr_limit=corr_limit,
        weight_method=weight_method,
        rebalance_mode=rebalance_mode,
        min_rebalance_bars=min_rebalance_bars,
    )
    final_weights = weight_events[-1]["weights"] if weight_events else {}
    selected = weight_events[-1]["selected_symbols"] if weight_events else symbols
    combined_pnl = (portfolio_equity[-1] - initial_capital) if portfolio_equity else 0.0
    max_dd = _max_drawdown(portfolio_equity)

    summary = {
        "symbols": symbols,
        "selected_symbols": selected,
        "max_corr": corr_limit,
        "weight_method": weight_method,
        "rebalance_mode": rebalance_mode,
        "min_rebalance_bars": min_rebalance_bars,
        "rebalance_events": max(0, len(weight_events) - 1),
        "weights": final_weights,
        "correlation": corr,
        "initial_capital": initial_capital,
        "final_capital": initial_capital + combined_pnl,
        "total_pnl": combined_pnl,
        "max_drawdown": max_dd,
    }

    summary_path = os.path.join(out_dir, "portfolio_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    events_path = os.path.join(out_dir, "portfolio_weight_events.json")
    with open(events_path, "w", encoding="utf-8") as f:
        json.dump(weight_events, f, ensure_ascii=False, indent=2)

    curve_out = os.path.join(out_dir, "portfolio_equity.csv")
    with open(curve_out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["step", "datetime", "equity"])
        for i, v in enumerate(portfolio_equity):
            writer.writerow([i, dates[i] if i < len(dates) else "", v])

    print(f"[PORTFOLIO] symbols={len(symbols)} selected={len(selected)}")
    print(f"[PORTFOLIO] summary={summary_path}")
    print(f"[PORTFOLIO] events={events_path}")
    print(f"[PORTFOLIO] curve={curve_out}")


if __name__ == "__main__":
    main_portfolio()
