import json
import os

import matplotlib.pyplot as plt


def main():
    summary_path = os.path.join("output", "batch_summary.json")
    if not os.path.exists(summary_path):
        raise SystemExit("batch_summary.json not found. Run batch_runner.py first.")

    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    plt.figure(figsize=(10, 4))
    for item in summary:
        symbol = item.get("symbol")
        curve_path = os.path.join("output", symbol, "equity_curve.csv")
        if not os.path.exists(curve_path):
            continue
        equity = []
        with open(curve_path, "r", encoding="utf-8") as f2:
            lines = f2.read().splitlines()[1:]
            for line in lines:
                parts = line.split(",")
                if len(parts) >= 4:
                    equity.append(float(parts[3]))
        if equity:
            plt.plot(equity, label=symbol)

    plt.legend()
    plt.title("Batch Equity Curves")
    out_path = os.path.join("output", "batch_equity.png")
    plt.tight_layout()
    plt.savefig(out_path)
    print(f"[BATCH] saved {out_path}")


if __name__ == "__main__":
    main()
