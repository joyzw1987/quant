import argparse
import copy
import csv
import json
import os

from engine.backtest_eval import run_once
from engine.data_engine import DataEngine


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def score_of(stats, dd_penalty):
    return float(stats["pnl"]) - float(dd_penalty) * float(stats["max_drawdown"])


def stability_of(scores, stability_penalty):
    if not scores:
        return 0.0, 0.0, 0.0
    avg_score = sum(scores) / len(scores)
    variance = sum((v - avg_score) ** 2 for v in scores) / len(scores)
    std_score = variance ** 0.5
    stable_score = avg_score - stability_penalty * std_score
    return avg_score, std_score, stable_score


def build_windows(bars, window_bars, window_step):
    total = len(bars)
    if total <= 0:
        return []
    if window_bars is None or window_bars <= 0 or window_bars >= total:
        return [bars]
    step = window_step if window_step and window_step > 0 else window_bars
    windows = []
    start = 0
    while start + window_bars <= total:
        windows.append(bars[start : start + window_bars])
        start += step
    if not windows:
        windows.append(bars)
    elif windows[-1][-1]["datetime"] != bars[-1]["datetime"]:
        windows.append(bars[-window_bars:])
    return windows


def _color(score, min_score, max_score):
    if max_score <= min_score:
        return "#f0f0f0"
    ratio = (score - min_score) / (max_score - min_score)
    ratio = max(0.0, min(1.0, ratio))
    r = int(255 * (1.0 - ratio))
    g = int(180 + 75 * ratio)
    b = int(120 * (1.0 - ratio))
    return f"#{r:02x}{g:02x}{b:02x}"


def main():
    parser = argparse.ArgumentParser(description="Generate parameter stability heatmap for fast/slow.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--fast-min", type=int, default=3)
    parser.add_argument("--fast-max", type=int, default=12)
    parser.add_argument("--slow-min", type=int, default=10)
    parser.add_argument("--slow-max", type=int, default=80)
    parser.add_argument("--slow-step", type=int, default=2)
    parser.add_argument("--dd-penalty", type=float, default=0.4)
    parser.add_argument("--window-bars", type=int, default=0, help="0 means full sample only")
    parser.add_argument("--window-step", type=int, default=0, help="0 means same as window-bars")
    parser.add_argument("--stability-penalty", type=float, default=0.5)
    parser.add_argument("--out-dir", default="output")
    args = parser.parse_args()

    cfg = load_config()
    symbol = args.symbol or cfg.get("symbol", "M2609")
    cfg = copy.deepcopy(cfg)
    cfg["symbol"] = symbol
    bars = DataEngine().get_bars(symbol)
    windows = build_windows(bars, args.window_bars, args.window_step)

    rows = []
    for fast in range(args.fast_min, args.fast_max + 1):
        for slow in range(args.slow_min, args.slow_max + 1, args.slow_step):
            if slow <= fast:
                continue
            strategy_cfg = copy.deepcopy(cfg["strategy"])
            strategy_cfg["fast"] = fast
            strategy_cfg["slow"] = slow
            window_scores = []
            window_pnls = []
            window_drawdowns = []
            window_trades = []
            for wb in windows:
                stats = run_once(cfg, wb, strategy_cfg)
                window_scores.append(score_of(stats, args.dd_penalty))
                window_pnls.append(float(stats["pnl"]))
                window_drawdowns.append(float(stats["max_drawdown"]))
                window_trades.append(float(stats["trades"]))
            avg_score, std_score, stable_score = stability_of(window_scores, args.stability_penalty)
            positive_windows = sum(1 for s in window_scores if s > 0)
            rows.append(
                {
                    "fast": fast,
                    "slow": slow,
                    "score": stable_score,
                    "avg_score": avg_score,
                    "std_score": std_score,
                    "stable_score": stable_score,
                    "window_count": len(window_scores),
                    "positive_window_ratio": (positive_windows / len(window_scores) * 100.0) if window_scores else 0.0,
                    "avg_pnl": (sum(window_pnls) / len(window_pnls)) if window_pnls else 0.0,
                    "avg_max_drawdown": (sum(window_drawdowns) / len(window_drawdowns)) if window_drawdowns else 0.0,
                    "avg_trades": (sum(window_trades) / len(window_trades)) if window_trades else 0.0,
                }
            )

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, f"param_heatmap_{symbol}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
            if rows
            else ["fast", "slow", "score", "avg_score", "std_score", "stable_score", "window_count", "positive_window_ratio", "avg_pnl", "avg_max_drawdown", "avg_trades"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    if not rows:
        print("No rows generated")
        return

    min_score = min(r["score"] for r in rows)
    max_score = max(r["score"] for r in rows)
    table_rows = []
    for row in rows:
        color = _color(row["score"], min_score, max_score)
        table_rows.append(
            f"<tr style='background:{color}'><td>{row['fast']}</td><td>{row['slow']}</td><td>{row['score']:.2f}</td>"
            f"<td>{row['avg_score']:.2f}</td><td>{row['std_score']:.2f}</td><td>{row['positive_window_ratio']:.1f}%</td>"
            f"<td>{row['avg_pnl']:.2f}</td><td>{row['avg_max_drawdown']:.2f}</td><td>{row['avg_trades']:.1f}</td></tr>"
        )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Param Heatmap</title></head><body>"
        f"<h2>Param Heatmap {symbol}</h2>"
        f"<div>window_count={len(windows)} stability_penalty={args.stability_penalty}</div>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>fast</th><th>slow</th><th>stable_score</th><th>avg_score</th><th>std_score</th><th>positive_ratio</th>"
        "<th>avg_pnl</th><th>avg_max_drawdown</th><th>avg_trades</th></tr>"
        + "".join(table_rows)
        + "</table></body></html>"
    )
    html_path = os.path.join(args.out_dir, f"param_heatmap_{symbol}.html")
    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html)

    print("Param heatmap completed")
    print(f"symbol={symbol}")
    print(f"rows={len(rows)}")
    print(f"csv={csv_path}")
    print(f"html={html_path}")


if __name__ == "__main__":
    main()
