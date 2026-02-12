import argparse
import json
import sys

from engine.config_validator import report_validation, validate_config


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_sim(config, symbol=None, output_dir="output"):
    from main import main as backtest_main

    target_symbol = symbol or config.get("symbol")
    print(f"[RUN] mode=sim symbol={target_symbol}")
    backtest_main(symbol_override=target_symbol, output_dir=output_dir)


def run_sim_with_gui(config, symbol=None, auto_start=True):
    from dashboard_gui import main as gui_main

    target_symbol = symbol or config.get("symbol")
    print(f"[RUN] mode=sim_gui symbol={target_symbol} auto_start={auto_start}")
    gui_main(default_symbol=target_symbol, auto_start=auto_start)


def run_ctp(config):
    from ctp_runner import main as ctp_main

    print(f"[RUN] mode=ctp symbol={config.get('symbol', '')}")
    ctp_main()


def main():
    parser = argparse.ArgumentParser(description="Unified runner: sim/sim_live/ctp")
    parser.add_argument("--mode", default=None, choices=["sim", "sim_gui", "sim_live", "ctp"])
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--auto-start", action="store_true", help="for sim_gui mode")
    parser.add_argument("--source", default="akshare", help="for sim_live mode")
    parser.add_argument("--interval-sec", type=int, default=60, help="for sim_live mode")
    parser.add_argument("--max-cycles", type=int, default=0, help="for sim_live mode, 0=infinite")
    parser.add_argument("--ignore-market-hours", action="store_true", help="for sim_live mode")
    parser.add_argument("--auto-adjust", action="store_true", help="for sim_live mode")
    parser.add_argument("--adjust-every-cycles", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-train-size", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-test-size", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-step-size", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-fast-min", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-fast-max", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-slow-min", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-slow-max", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-slow-step", type=int, default=None, help="for sim_live mode")
    parser.add_argument("--tune-dd-penalty", type=float, default=None, help="for sim_live mode")
    parser.add_argument("--tune-min-positive-windows", type=int, default=None, help="for sim_live mode")
    args = parser.parse_args()

    config = load_config()
    mode = args.mode or config.get("run_mode", "sim")
    symbol = args.symbol or config.get("symbol")

    if mode == "ctp":
        errors, warnings = validate_config(config, mode="ctp")
        report_validation(errors, warnings)
        run_ctp(config)
        return

    errors, warnings = validate_config(config, mode="paper")
    report_validation(errors, warnings)

    if mode == "sim_gui":
        run_sim_with_gui(config, symbol=symbol, auto_start=args.auto_start)
    elif mode == "sim_live":
        from sim_live_runner import main as sim_live_main

        argv_backup = sys.argv[:]
        try:
            sys.argv = [
                "sim_live_runner.py",
                "--symbol",
                symbol,
                "--source",
                args.source,
                "--interval-sec",
                str(args.interval_sec),
                "--max-cycles",
                str(args.max_cycles),
                "--output-dir",
                args.output_dir,
            ]
            if args.auto_adjust:
                sys.argv.append("--auto-adjust")
            if args.ignore_market_hours:
                sys.argv.append("--ignore-market-hours")
            optional_pairs = [
                ("--adjust-every-cycles", args.adjust_every_cycles),
                ("--tune-train-size", args.tune_train_size),
                ("--tune-test-size", args.tune_test_size),
                ("--tune-step-size", args.tune_step_size),
                ("--tune-fast-min", args.tune_fast_min),
                ("--tune-fast-max", args.tune_fast_max),
                ("--tune-slow-min", args.tune_slow_min),
                ("--tune-slow-max", args.tune_slow_max),
                ("--tune-slow-step", args.tune_slow_step),
                ("--tune-dd-penalty", args.tune_dd_penalty),
                ("--tune-min-positive-windows", args.tune_min_positive_windows),
            ]
            for key, value in optional_pairs:
                if value is not None:
                    sys.argv.extend([key, str(value)])
            sim_live_main()
        finally:
            sys.argv = argv_backup
    else:
        run_sim(config, symbol=symbol, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
