import csv
import json
import os

from engine.perf_report import build_monthly_metrics


def _read_csv(path):
    with open(path, "r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    curve_path = os.path.join("output", "equity_curve.csv")
    trades_path = os.path.join("output", "trades.csv")
    if not os.path.exists(curve_path):
        raise SystemExit("equity_curve.csv not found, run main.py first")

    equity_rows = _read_csv(curve_path)
    trade_rows = _read_csv(trades_path) if os.path.exists(trades_path) else []
    monthly_rows = build_monthly_metrics(equity_rows, trade_rows)

    csv_path = os.path.join("output", "monthly_report.csv")
    json_path = os.path.join("output", "monthly_report.json")

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        if monthly_rows:
            writer = csv.DictWriter(f, fieldnames=list(monthly_rows[0].keys()))
            writer.writeheader()
            writer.writerows(monthly_rows)
        else:
            writer = csv.writer(f)
            writer.writerow(
                ["month", "start_equity", "end_equity", "return_pct", "max_drawdown", "trade_count", "win_rate", "pnl"]
            )

    summary = {
        "months": len(monthly_rows),
        "total_pnl": sum(float(row["pnl"]) for row in monthly_rows),
        "avg_return_pct": (
            sum(float(row["return_pct"]) for row in monthly_rows) / len(monthly_rows) if monthly_rows else 0.0
        ),
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": monthly_rows}, f, ensure_ascii=False, indent=2)

    print(f"[MONTHLY] rows={len(monthly_rows)}")
    print(f"[MONTHLY] csv={csv_path}")
    print(f"[MONTHLY] json={json_path}")


if __name__ == "__main__":
    main()
