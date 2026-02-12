import argparse
import json
import os
import subprocess
import sys
import time

from engine.config_validator import report_validation, validate_config
from engine.runtime_state import RuntimeState
from main import main as backtest_main


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _read_perf(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _run_fetch(symbol, out_path, source):
    cmd = [
        sys.executable,
        "data_update_merge.py",
        "--symbol",
        symbol,
        "--out",
        out_path,
        "--source",
        source,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _build_tune_cmd(symbol, tune_cfg):
    return [
        sys.executable,
        "walk_forward_tune.py",
        "--symbol",
        symbol,
        "--train-size",
        str(tune_cfg["train_size"]),
        "--test-size",
        str(tune_cfg["test_size"]),
        "--step-size",
        str(tune_cfg["step_size"]),
        "--fast-min",
        str(tune_cfg["fast_min"]),
        "--fast-max",
        str(tune_cfg["fast_max"]),
        "--slow-min",
        str(tune_cfg["slow_min"]),
        "--slow-max",
        str(tune_cfg["slow_max"]),
        "--slow-step",
        str(tune_cfg["slow_step"]),
        "--dd-penalty",
        str(tune_cfg["dd_penalty"]),
        "--min-positive-windows",
        str(tune_cfg["min_positive_windows"]),
    ]


def _run_tune(symbol, tune_cfg):
    cmd = _build_tune_cmd(symbol=symbol, tune_cfg=tune_cfg)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _snapshot_files(paths):
    snapshot = {}
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                snapshot[path] = f.read()
        else:
            snapshot[path] = None
    return snapshot


def _restore_files(snapshot):
    for path, content in snapshot.items():
        if content is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def _resolve_tune_cfg(cfg, args):
    auto_adjust = cfg.get("auto_adjust") or {}

    def pick(name, fallback):
        value = getattr(args, name)
        return fallback if value is None else value

    enabled = bool(args.auto_adjust or auto_adjust.get("enabled", False))
    return {
        "enabled": enabled,
        "adjust_every_cycles": max(1, int(pick("adjust_every_cycles", auto_adjust.get("adjust_every_cycles", 5)))),
        "train_size": max(60, int(pick("tune_train_size", auto_adjust.get("train_size", 480)))),
        "test_size": max(20, int(pick("tune_test_size", auto_adjust.get("test_size", 120)))),
        "step_size": max(20, int(pick("tune_step_size", auto_adjust.get("step_size", 120)))),
        "fast_min": max(2, int(pick("tune_fast_min", auto_adjust.get("fast_min", 3)))),
        "fast_max": max(3, int(pick("tune_fast_max", auto_adjust.get("fast_max", 10)))),
        "slow_min": max(4, int(pick("tune_slow_min", auto_adjust.get("slow_min", 10)))),
        "slow_max": max(6, int(pick("tune_slow_max", auto_adjust.get("slow_max", 60)))),
        "slow_step": max(1, int(pick("tune_slow_step", auto_adjust.get("slow_step", 2)))),
        "dd_penalty": float(pick("tune_dd_penalty", auto_adjust.get("dd_penalty", 0.5))),
        "min_positive_windows": max(
            1, int(pick("tune_min_positive_windows", auto_adjust.get("min_positive_windows", 1)))
        ),
        "rollback_on_worse": bool(auto_adjust.get("rollback_on_worse", True)),
        "min_improve": float(auto_adjust.get("min_improve", 0.0)),
    }


def _normalize_tune_cfg(tune_cfg):
    if tune_cfg["fast_max"] < tune_cfg["fast_min"]:
        tune_cfg["fast_max"] = tune_cfg["fast_min"]
    if tune_cfg["slow_max"] < tune_cfg["slow_min"]:
        tune_cfg["slow_max"] = tune_cfg["slow_min"]
    if tune_cfg["slow_min"] <= tune_cfg["fast_min"]:
        tune_cfg["slow_min"] = tune_cfg["fast_min"] + 1
    if tune_cfg["slow_max"] <= tune_cfg["fast_max"]:
        tune_cfg["slow_max"] = tune_cfg["fast_max"] + 1
    return tune_cfg


def main():
    parser = argparse.ArgumentParser(description="Quasi realtime simulation runner")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--source", default="akshare")
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means infinite loop")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--data-out", default=None, help="default: data/<symbol>.csv")
    parser.add_argument("--auto-adjust", action="store_true", help="enable automatic strategy tuning")
    parser.add_argument("--adjust-every-cycles", type=int, default=None)
    parser.add_argument("--tune-train-size", type=int, default=None)
    parser.add_argument("--tune-test-size", type=int, default=None)
    parser.add_argument("--tune-step-size", type=int, default=None)
    parser.add_argument("--tune-fast-min", type=int, default=None)
    parser.add_argument("--tune-fast-max", type=int, default=None)
    parser.add_argument("--tune-slow-min", type=int, default=None)
    parser.add_argument("--tune-slow-max", type=int, default=None)
    parser.add_argument("--tune-slow-step", type=int, default=None)
    parser.add_argument("--tune-dd-penalty", type=float, default=None)
    parser.add_argument("--tune-min-positive-windows", type=int, default=None)
    args = parser.parse_args()

    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="paper")
    report_validation(errors, warnings)

    symbol = args.symbol or cfg.get("symbol", "M2609")
    data_out = args.data_out or f"data/{symbol}.csv"
    interval_sec = max(5, int(args.interval_sec))
    runtime = RuntimeState("state/runtime_state.json")
    tune_cfg = _normalize_tune_cfg(_resolve_tune_cfg(cfg, args))

    print(
        f"[SIM_LIVE] start symbol={symbol} source={args.source} interval={interval_sec}s "
        f"max_cycles={args.max_cycles if args.max_cycles else 'infinite'} auto_adjust={tune_cfg['enabled']}"
    )

    cycle = 0
    while True:
        cycle += 1
        runtime.update(
            {
                "event": "sim_live_cycle_start",
                "mode": "sim_live",
                "cycle": cycle,
                "symbol": symbol,
                "source": args.source,
                "auto_adjust": tune_cfg["enabled"],
            }
        )

        fetch_ret = _run_fetch(symbol=symbol, out_path=data_out, source=args.source)
        if fetch_ret.returncode != 0:
            message = (fetch_ret.stderr or fetch_ret.stdout or "").strip()
            runtime.update(
                {
                    "event": "sim_live_fetch_failed",
                    "mode": "sim_live",
                    "cycle": cycle,
                    "symbol": symbol,
                    "error": message,
                }
            )
            print(f"[SIM_LIVE] cycle={cycle} fetch failed: {message}")
        else:
            fetch_text = (fetch_ret.stdout or "").strip()
            if fetch_text:
                print(fetch_text)

            snapshot = None
            tune_changed = False
            baseline_pnl = None
            tune_cycle = tune_cfg["enabled"] and cycle % tune_cfg["adjust_every_cycles"] == 0

            if tune_cycle and tune_cfg["rollback_on_worse"]:
                try:
                    backtest_main(symbol_override=symbol, output_dir=args.output_dir)
                    baseline_perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                    baseline_pnl = _to_float(baseline_perf.get("total_pnl"))
                    runtime.update(
                        {
                            "event": "sim_live_baseline_done",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "baseline_pnl": baseline_pnl,
                        }
                    )
                    print(f"[SIM_LIVE] cycle={cycle} baseline pnl={baseline_pnl}")
                except Exception as exc:
                    runtime.update(
                        {
                            "event": "sim_live_baseline_failed",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "error": str(exc),
                        }
                    )
                    print(f"[SIM_LIVE] cycle={cycle} baseline failed: {exc}")

            if tune_cycle:
                snapshot = _snapshot_files(["config.json", "state/strategy_state.json"])
                old_cfg = load_config()
                old_strategy = old_cfg.get("strategy", {})
                runtime.update(
                    {
                        "event": "sim_live_tune_start",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "old_fast": old_strategy.get("fast"),
                        "old_slow": old_strategy.get("slow"),
                    }
                )
                tune_ret = _run_tune(symbol=symbol, tune_cfg=tune_cfg)
                if tune_ret.returncode != 0:
                    tune_error = (tune_ret.stderr or tune_ret.stdout or "").strip()
                    runtime.update(
                        {
                            "event": "sim_live_tune_failed",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "error": tune_error,
                        }
                    )
                    print(f"[SIM_LIVE] cycle={cycle} tune failed: {tune_error}")
                else:
                    tune_log = (tune_ret.stdout or "").strip()
                    new_cfg = load_config()
                    new_strategy = new_cfg.get("strategy", {})
                    tune_changed = (
                        old_strategy.get("fast") != new_strategy.get("fast")
                        or old_strategy.get("slow") != new_strategy.get("slow")
                    )
                    runtime.update(
                        {
                            "event": "sim_live_tune_done",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "changed": tune_changed,
                            "new_fast": new_strategy.get("fast"),
                            "new_slow": new_strategy.get("slow"),
                        }
                    )
                    if tune_log:
                        print(tune_log)
                    print(
                        f"[SIM_LIVE] cycle={cycle} tune done changed={tune_changed} "
                        f"fast={new_strategy.get('fast')} slow={new_strategy.get('slow')}"
                    )

            try:
                backtest_main(symbol_override=symbol, output_dir=args.output_dir)
            except Exception as exc:
                runtime.update(
                    {
                        "event": "sim_live_backtest_failed",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "error": str(exc),
                    }
                )
                print(f"[SIM_LIVE] cycle={cycle} backtest failed: {exc}")
            else:
                perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                current_pnl = _to_float(perf.get("total_pnl"))

                if (
                    tune_changed
                    and tune_cfg["rollback_on_worse"]
                    and snapshot is not None
                    and baseline_pnl is not None
                    and current_pnl is not None
                    and current_pnl < (baseline_pnl + tune_cfg["min_improve"])
                ):
                    _restore_files(snapshot)
                    runtime.update(
                        {
                            "event": "sim_live_tune_rollback",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "baseline_pnl": baseline_pnl,
                            "new_pnl": current_pnl,
                        }
                    )
                    print(
                        f"[SIM_LIVE] cycle={cycle} rollback tune: baseline_pnl={baseline_pnl} "
                        f"new_pnl={current_pnl}"
                    )
                    backtest_main(symbol_override=symbol, output_dir=args.output_dir)
                    perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                    current_pnl = _to_float(perf.get("total_pnl"))

                runtime.update(
                    {
                        "event": "sim_live_cycle_done",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "total_pnl": perf.get("total_pnl"),
                        "win_rate": perf.get("win_rate"),
                        "total_trades": perf.get("total_trades"),
                    }
                )
                print(
                    f"[SIM_LIVE] cycle={cycle} done pnl={current_pnl} "
                    f"trades={perf.get('total_trades')}"
                )

        if args.max_cycles > 0 and cycle >= args.max_cycles:
            runtime.update(
                {
                    "event": "sim_live_finished",
                    "mode": "sim_live",
                    "cycle": cycle,
                    "symbol": symbol,
                }
            )
            print(f"[SIM_LIVE] finished cycles={cycle}")
            break

        runtime.update(
            {
                "event": "sim_live_sleeping",
                "mode": "sim_live",
                "cycle": cycle,
                "symbol": symbol,
                "sleep_sec": interval_sec,
            }
        )
        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
