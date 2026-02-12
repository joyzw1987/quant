import csv
import json
import os

from engine.perf_report import build_weekly_metrics


def _read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_rows(path, rows, fallback_headers):
    with open(path, "w", newline="", encoding="utf-8") as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        else:
            writer = csv.writer(f)
            writer.writerow(fallback_headers)


def main():
    perf_path = os.path.join("output", "performance.json")
    curve_path = os.path.join("output", "equity_curve.csv")
    trades_path = os.path.join("output", "trades.csv")
    if not os.path.exists(perf_path):
        raise SystemExit("performance.json not found, run main.py first")
    if not os.path.exists(curve_path):
        raise SystemExit("equity_curve.csv not found, run main.py first")

    with open(perf_path, "r", encoding="utf-8") as f:
        perf = json.load(f)
    equity_rows = _read_csv(curve_path)
    trade_rows = _read_csv(trades_path) if os.path.exists(trades_path) else []
    weekly_rows = build_weekly_metrics(equity_rows, trade_rows)

    daily_text_path = os.path.join("output", "daily_report.txt")
    weekly_csv_path = os.path.join("output", "weekly_report.csv")
    weekly_json_path = os.path.join("output", "weekly_report.json")

    with open(daily_text_path, "w", encoding="utf-8") as f:
        for key in sorted(perf.keys()):
            f.write(f"{key}={perf[key]}\n")

    _write_rows(
        weekly_csv_path,
        weekly_rows,
        fallback_headers=["week", "start_equity", "end_equity", "return_pct", "max_drawdown", "trade_count", "win_rate", "pnl"],
    )

    summary = {
        "weeks": len(weekly_rows),
        "total_pnl": sum(float(row["pnl"]) for row in weekly_rows),
        "avg_return_pct": (
            sum(float(row["return_pct"]) for row in weekly_rows) / len(weekly_rows) if weekly_rows else 0.0
        ),
    }
    with open(weekly_json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": weekly_rows}, f, ensure_ascii=False, indent=2)

    print(f"[REPORT] daily={daily_text_path}")
    print(f"[REPORT] weekly_csv={weekly_csv_path}")
    print(f"[REPORT] weekly_json={weekly_json_path}")


if __name__ == "__main__":
    main()
