import argparse
import json
import subprocess
import sys
from pathlib import Path


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def normalize_hhmm(value):
    text = str(value or "").strip()
    parts = text.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time: {value}")
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        raise ValueError(f"Invalid time: {value}")
    return f"{hour:02d}:{minute:02d}"


def build_tr(workdir, python_exe, script_args):
    ps = (
        f"Set-Location -LiteralPath '{workdir}'; "
        f"& '{python_exe}' {script_args}"
    )
    return f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{ps}"'


def run(command, dry_run=False):
    if dry_run:
        print("DRYRUN:", " ".join(command))
        return 0
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0:
        print(result.stdout.strip())
        print(result.stderr.strip())
    return result.returncode


def create_task(task_name, days, hhmm, tr, dry_run=False):
    command = [
        "schtasks",
        "/Create",
        "/F",
        "/TN",
        task_name,
        "/SC",
        "WEEKLY",
        "/D",
        days,
        "/ST",
        hhmm,
        "/TR",
        tr,
    ]
    return run(command, dry_run=dry_run)


def delete_task(task_name, dry_run=False):
    command = ["schtasks", "/Delete", "/F", "/TN", task_name]
    return run(command, dry_run=dry_run)


def query_task(task_name, dry_run=False):
    command = ["schtasks", "/Query", "/TN", task_name, "/V", "/FO", "LIST"]
    return run(command, dry_run=dry_run)


def build_plan(config):
    symbol = config.get("symbol", "M2609")
    scheduler = config.get("scheduler") or {}
    source = scheduler.get("source", "akshare")
    days = scheduler.get("days", "MON,TUE,WED,THU,FRI")
    task_prefix = scheduler.get("task_prefix", f"Quant_{symbol}")
    fetch_times = scheduler.get("fetch_times", ["11:35", "15:05", "23:05"])
    research_time = scheduler.get("research_time", "23:20")

    fetch_times = [normalize_hhmm(t) for t in fetch_times]
    research_time = normalize_hhmm(research_time)

    workdir = str(Path(__file__).resolve().parent)
    python_exe = sys.executable

    plan = []
    for hhmm in fetch_times:
        suffix = hhmm.replace(":", "")
        task_name = f"{task_prefix}_fetch_{suffix}"
        script_args = f'data_update_merge.py --symbol {symbol} --out data/{symbol}.csv --source {source}'
        tr = build_tr(workdir=workdir, python_exe=python_exe, script_args=script_args)
        plan.append({"name": task_name, "days": days, "time": hhmm, "tr": tr, "kind": "fetch"})

    task_name = f"{task_prefix}_research"
    script_args = f"run.py --mode research_cycle --symbol {symbol}"
    tr = build_tr(workdir=workdir, python_exe=python_exe, script_args=script_args)
    plan.append({"name": task_name, "days": days, "time": research_time, "tr": tr, "kind": "research"})
    return plan


def main():
    parser = argparse.ArgumentParser(description="Manage Windows scheduled tasks for data + research cycle.")
    parser.add_argument("--action", choices=["install", "uninstall", "status", "show"], default="show")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = load_config()
    plan = build_plan(config)

    if args.action == "show":
        print("Task plan:")
        for item in plan:
            print(f"- {item['name']} {item['days']} {item['time']} {item['kind']}")
            print(f"  TR={item['tr']}")
        return

    if args.action == "install":
        failed = 0
        for item in plan:
            code = create_task(
                task_name=item["name"],
                days=item["days"],
                hhmm=item["time"],
                tr=item["tr"],
                dry_run=args.dry_run,
            )
            failed += 0 if code == 0 else 1
        if failed:
            raise SystemExit(1)
        print("Installed all tasks")
        return

    if args.action == "uninstall":
        failed = 0
        for item in plan:
            code = delete_task(item["name"], dry_run=args.dry_run)
            failed += 0 if code == 0 else 1
        if failed:
            raise SystemExit(1)
        print("Uninstalled all tasks")
        return

    if args.action == "status":
        failed = 0
        for item in plan:
            code = query_task(item["name"], dry_run=args.dry_run)
            failed += 0 if code == 0 else 1
        if failed:
            raise SystemExit(1)
        return


if __name__ == "__main__":
    main()
