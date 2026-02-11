import os


def main():
    perf_path = os.path.join("output", "performance.json")
    if not os.path.exists(perf_path):
        raise SystemExit("performance.json not found")
    with open(perf_path, "r", encoding="utf-8") as f:
        content = f.read()
    out_daily = os.path.join("output", "daily_report.txt")
    out_weekly = os.path.join("output", "weekly_report.txt")
    with open(out_daily, "w", encoding="utf-8") as f:
        f.write(content)
    with open(out_weekly, "w", encoding="utf-8") as f:
        f.write(content)
    print("[REPORT] daily/weekly saved")


if __name__ == "__main__":
    main()
