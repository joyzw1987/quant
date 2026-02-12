import argparse
import json
import os
import subprocess
import sys
from datetime import datetime


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_command(command):
    started = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    finished = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return {
        "command": command,
        "started_at": started,
        "finished_at": finished,
        "returncode": result.returncode,
        "stdout": (result.stdout or "").strip(),
        "stderr": (result.stderr or "").strip(),
    }


def main():
    parser = argparse.ArgumentParser(description="Automated research cycle: build -> strict OOS -> backtest")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--max-days", type=int, default=None)
    parser.add_argument("--min-dataset-days", type=int, default=None)
    parser.add_argument("--holdout-bars", type=int, default=None)
    parser.add_argument("--max-candidates", type=int, default=None)
    parser.add_argument("--dd-penalty", type=float, default=None)
    parser.add_argument("--min-trades", type=int, default=None)
    parser.add_argument("--min-holdout-trades", type=int, default=None)
    parser.add_argument("--min-score-improve", type=float, default=None)
    parser.add_argument("--require-positive-holdout", action="store_true")
    parser.add_argument("--no-apply-best", action="store_true")
    parser.add_argument("--skip-backtest", action="store_true")
    args = parser.parse_args()

    cfg = load_config()
    cycle_cfg = cfg.get("research_cycle") or {}
    symbol = args.symbol or cfg.get("symbol", "M2609")
    max_days = args.max_days if args.max_days is not None else int(cycle_cfg.get("max_days", 120))
    min_dataset_days = (
        args.min_dataset_days if args.min_dataset_days is not None else int(cycle_cfg.get("min_dataset_days", 60))
    )
    holdout_bars = (
        args.holdout_bars if args.holdout_bars is not None else int(cycle_cfg.get("holdout_bars", 240))
    )
    max_candidates = (
        args.max_candidates if args.max_candidates is not None else int(cycle_cfg.get("max_candidates", 400))
    )
    dd_penalty = args.dd_penalty if args.dd_penalty is not None else float(cycle_cfg.get("dd_penalty", 0.4))
    min_trades = args.min_trades if args.min_trades is not None else int(cycle_cfg.get("min_trades", 4))
    min_holdout_trades = (
        args.min_holdout_trades
        if args.min_holdout_trades is not None
        else int(cycle_cfg.get("min_holdout_trades", 4))
    )
    min_score_improve = (
        args.min_score_improve
        if args.min_score_improve is not None
        else float(cycle_cfg.get("min_score_improve", 0.0))
    )
    require_positive_holdout = bool(
        args.require_positive_holdout or cycle_cfg.get("require_positive_holdout", False)
    )
    apply_best = bool(cycle_cfg.get("apply_best", True)) and not args.no_apply_best
    run_backtest_after = bool(cycle_cfg.get("run_backtest_after", True)) and not args.skip_backtest

    os.makedirs("output", exist_ok=True)
    summary = {
        "started_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "config": {
            "max_days": max_days,
            "min_dataset_days": min_dataset_days,
            "holdout_bars": holdout_bars,
            "max_candidates": max_candidates,
            "dd_penalty": dd_penalty,
            "min_trades": min_trades,
            "min_holdout_trades": min_holdout_trades,
            "min_score_improve": min_score_improve,
            "require_positive_holdout": require_positive_holdout,
            "apply_best": apply_best,
            "run_backtest_after": run_backtest_after,
        },
        "steps": [],
        "status": "running",
    }

    cmd_build = [
        sys.executable,
        "build_dataset_from_archive.py",
        "--symbol",
        symbol,
        "--out",
        f"data/{symbol}.csv",
        "--max-days",
        str(max_days),
        "--report-out",
        "output/dataset_build_report.json",
    ]
    build_result = run_command(cmd_build)
    summary["steps"].append({"name": "build_dataset", **build_result})
    if build_result["returncode"] != 0:
        summary["status"] = "failed"
        summary["failed_step"] = "build_dataset"
        with open("output/research_cycle_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(build_result["stdout"])
        print(build_result["stderr"])
        raise SystemExit(build_result["returncode"])

    build_report = {}
    try:
        with open("output/dataset_build_report.json", "r", encoding="utf-8") as f:
            build_report = json.load(f)
    except Exception:
        build_report = {}
    summary["dataset_report"] = build_report
    days = int(build_report.get("days", 0)) if build_report else 0
    if days < min_dataset_days:
        summary["status"] = "failed"
        summary["failed_step"] = "dataset_coverage_gate"
        summary["dataset_gate"] = {
            "passed": False,
            "days": days,
            "min_dataset_days": min_dataset_days,
            "reason": "dataset_days_below_threshold",
        }
        with open("output/research_cycle_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(
            f"[GATE] dataset coverage not enough: days={days}, "
            f"min_dataset_days={min_dataset_days}"
        )
        raise SystemExit(2)
    summary["dataset_gate"] = {
        "passed": True,
        "days": days,
        "min_dataset_days": min_dataset_days,
    }

    cmd_oos = [
        sys.executable,
        "strict_oos_validate.py",
        "--symbol",
        symbol,
        "--holdout-bars",
        str(holdout_bars),
        "--max-candidates",
        str(max_candidates),
        "--dd-penalty",
        str(dd_penalty),
        "--min-trades",
        str(min_trades),
        "--min-holdout-trades",
        str(min_holdout_trades),
        "--min-score-improve",
        str(min_score_improve),
    ]
    if require_positive_holdout:
        cmd_oos.append("--require-positive-holdout")
    if apply_best:
        cmd_oos.append("--apply-best")
    oos_result = run_command(cmd_oos)
    summary["steps"].append({"name": "strict_oos_validate", **oos_result})
    if oos_result["returncode"] != 0:
        summary["status"] = "failed"
        summary["failed_step"] = "strict_oos_validate"
        with open("output/research_cycle_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        print(oos_result["stdout"])
        print(oos_result["stderr"])
        raise SystemExit(oos_result["returncode"])

    if run_backtest_after:
        cmd_backtest = [sys.executable, "main.py", "--symbol", symbol]
        backtest_result = run_command(cmd_backtest)
        summary["steps"].append({"name": "backtest", **backtest_result})
        if backtest_result["returncode"] != 0:
            summary["status"] = "failed"
            summary["failed_step"] = "backtest"
            with open("output/research_cycle_summary.json", "w", encoding="utf-8") as f:
                json.dump(summary, f, ensure_ascii=False, indent=2)
            print(backtest_result["stdout"])
            print(backtest_result["stderr"])
            raise SystemExit(backtest_result["returncode"])

    summary["status"] = "ok"
    summary["finished_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("output/research_cycle_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    print("Research cycle completed")
    print(f"symbol={symbol}")
    print(f"summary=output/research_cycle_summary.json")
    for step in summary["steps"]:
        print(f"{step['name']}: returncode={step['returncode']}")


if __name__ == "__main__":
    main()
