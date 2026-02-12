import argparse
import json
import os

import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description="Build single html report")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    out_dir = args.output_dir
    perf_path = os.path.join(out_dir, "performance.json")
    curve_path = os.path.join(out_dir, "equity_curve.csv")
    if not os.path.exists(perf_path) or not os.path.exists(curve_path):
        raise SystemExit("performance.json or equity_curve.csv not found. Run main.py first.")

    with open(perf_path, "r", encoding="utf-8") as f:
        perf = json.load(f)

    equity = []
    with open(curve_path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()[1:]
        for line in lines:
            parts = line.split(",")
            if len(parts) >= 4:
                equity.append(float(parts[3]))

    img_path = os.path.join(out_dir, "equity_curve.png")
    if equity:
        plt.figure(figsize=(8, 3))
        plt.plot(equity)
        plt.title("Equity Curve")
        plt.tight_layout()
        plt.savefig(img_path)

    html = f"""
<!doctype html>
<html>
<head><meta charset='utf-8'><title>Single Report</title></head>
<body>
<h1>Performance</h1>
<pre>{json.dumps(perf, ensure_ascii=False, indent=2)}</pre>
<h2>Equity Curve</h2>
<img src="equity_curve.png" style="max-width:100%;" />
</body>
</html>
"""

    out_path = os.path.join(out_dir, "report.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[REPORT] saved {out_path}")


if __name__ == "__main__":
    main()
