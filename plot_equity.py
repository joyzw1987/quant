import os
import matplotlib.pyplot as plt


def main():
    path = os.path.join("output", "equity_curve.csv")
    if not os.path.exists(path):
        raise SystemExit("equity_curve.csv not found")
    equity = []
    with open(path, "r", encoding="utf-8") as f:
        lines = f.read().splitlines()[1:]
        for line in lines:
            parts = line.split(",")
            if len(parts) >= 4:
                equity.append(float(parts[3]))
    if not equity:
        raise SystemExit("no equity data")
    plt.figure(figsize=(8, 3))
    plt.plot(equity)
    plt.title("Equity Curve")
    plt.tight_layout()
    out = os.path.join("output", "equity_curve.png")
    plt.savefig(out)
    print(f"saved {out}")


if __name__ == "__main__":
    main()
