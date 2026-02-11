import json
import os


def main():
    summary_path = os.path.join("output", "batch_summary.json")
    if not os.path.exists(summary_path):
        raise SystemExit("batch_summary.json not found. Run batch_runner.py first.")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    rows = "\n".join(
        f"<tr><td>{item.get('symbol')}</td><td>{item.get('total_pnl', 0):.2f}</td><td>{item.get('return_pct', 0):.2f}%</td><td>{item.get('max_drawdown', 0):.2f}</td></tr>"
        for item in summary
    )

    html = f"""
<!doctype html>
<html>
<head><meta charset='utf-8'><title>Batch Report</title></head>
<body>
<h1>Batch Report</h1>
<table border='1' cellpadding='6' cellspacing='0'>
<tr><th>Symbol</th><th>PNL</th><th>Return%</th><th>Max Drawdown</th></tr>
{rows}
</table>
</body>
</html>
"""

    out_path = os.path.join("output", "batch_report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[BATCH] saved {out_path}")


if __name__ == "__main__":
    main()
