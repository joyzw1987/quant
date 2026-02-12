import argparse
import json
import os
import subprocess
import sys
import time


def _run_step(name, cmd):
    start = time.time()
    ret = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    elapsed = time.time() - start
    return {
        "name": name,
        "cmd": cmd,
        "returncode": ret.returncode,
        "elapsed_sec": round(elapsed, 3),
        "stdout": (ret.stdout or "").strip(),
        "stderr": (ret.stderr or "").strip(),
    }


def main():
    parser = argparse.ArgumentParser(description="End-to-end regression: OOS -> backtest -> reports")
    parser.add_argument("--symbol", default="M2609")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--quick", action="store_true")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    out_path = os.path.join(args.output_dir, "e2e_regression_report.json")
    data_path = os.path.join("data", f"{args.symbol}.csv")
    if not os.path.exists(data_path):
        raise SystemExit(f"data file not found: {data_path}")

    steps = []
    strict_cmd = [
        sys.executable,
        "strict_oos_validate.py",
        "--symbol",
        args.symbol,
    ]
    if args.quick:
        strict_cmd.extend(["--holdout-bars", "120", "--max-candidates", "80", "--min-trades", "2"])

    steps.append(_run_step("strict_oos", strict_cmd))
    steps.append(_run_step("backtest_main", [sys.executable, "main.py", "--symbol", args.symbol, "--output-dir", args.output_dir]))
    steps.append(_run_step("weekly_report", [sys.executable, "daily_weekly_report.py"]))
    steps.append(_run_step("monthly_report", [sys.executable, "monthly_report.py"]))
    steps.append(_run_step("single_report", [sys.executable, "single_report.py"]))

    required_files = [
        os.path.join(args.output_dir, "performance.json"),
        os.path.join(args.output_dir, "equity_curve.csv"),
        os.path.join(args.output_dir, "weekly_report.json"),
        os.path.join(args.output_dir, "monthly_report.json"),
        os.path.join(args.output_dir, "report.html"),
    ]
    checks = {path: os.path.exists(path) for path in required_files}
    ok = all(s["returncode"] == 0 for s in steps) and all(checks.values())

    report = {
        "symbol": args.symbol,
        "quick": bool(args.quick),
        "ok": ok,
        "steps": steps,
        "checks": checks,
    }
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(f"[E2E] report={out_path}")
    print(f"[E2E] ok={ok}")
    if not ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

