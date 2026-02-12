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


def main():
    parser = argparse.ArgumentParser(description="Quasi realtime simulation runner")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--source", default="akshare")
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means infinite loop")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--data-out", default=None, help="default: data/<symbol>.csv")
    args = parser.parse_args()

    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="paper")
    report_validation(errors, warnings)

    symbol = args.symbol or cfg.get("symbol", "M2609")
    data_out = args.data_out or f"data/{symbol}.csv"
    interval_sec = max(5, int(args.interval_sec))
    runtime = RuntimeState("state/runtime_state.json")

    print(
        f"[SIM_LIVE] start symbol={symbol} source={args.source} interval={interval_sec}s "
        f"max_cycles={args.max_cycles if args.max_cycles else 'infinite'}"
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
                    f"[SIM_LIVE] cycle={cycle} done pnl={perf.get('total_pnl')} "
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
