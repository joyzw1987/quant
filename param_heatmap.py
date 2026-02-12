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
    parser.add_argument("--out-dir", default="output")
    args = parser.parse_args()

    cfg = load_config()
    symbol = args.symbol or cfg.get("symbol", "M2609")
    cfg = copy.deepcopy(cfg)
    cfg["symbol"] = symbol
    bars = DataEngine().get_bars(symbol)

    rows = []
    for fast in range(args.fast_min, args.fast_max + 1):
        for slow in range(args.slow_min, args.slow_max + 1, args.slow_step):
            if slow <= fast:
                continue
            strategy_cfg = copy.deepcopy(cfg["strategy"])
            strategy_cfg["fast"] = fast
            strategy_cfg["slow"] = slow
            stats = run_once(cfg, bars, strategy_cfg)
            rows.append(
                {
                    "fast": fast,
                    "slow": slow,
                    "pnl": stats["pnl"],
                    "max_drawdown": stats["max_drawdown"],
                    "trades": stats["trades"],
                    "score": score_of(stats, args.dd_penalty),
                }
            )

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, f"param_heatmap_{symbol}.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["fast", "slow", "pnl", "max_drawdown", "trades", "score"])
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
            f"<td>{row['pnl']:.2f}</td><td>{row['max_drawdown']:.2f}</td><td>{row['trades']}</td></tr>"
        )
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Param Heatmap</title></head><body>"
        f"<h2>Param Heatmap {symbol}</h2>"
        "<table border='1' cellspacing='0' cellpadding='4'>"
        "<tr><th>fast</th><th>slow</th><th>score</th><th>pnl</th><th>max_drawdown</th><th>trades</th></tr>"
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
