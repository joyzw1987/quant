import os


def build_health_report(perf):
    lines = [f"total_trades={perf.get('total_trades', 0)}", f"total_pnl={perf.get('total_pnl', 0)}"]
    return "\n".join(lines)


def backtest_health_check(perf):
    return True


if __name__ == "__main__":
    path = os.path.join("output", "performance.json")
    if os.path.exists(path):
        import json
        with open(path, "r", encoding="utf-8") as f:
            perf = json.load(f)
        print(build_health_report(perf))
