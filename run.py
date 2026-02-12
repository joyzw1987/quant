import argparse
import json

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
    parser = argparse.ArgumentParser(description="Unified runner: sim/ctp")
    parser.add_argument("--mode", default=None, choices=["sim", "sim_gui", "ctp"])
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--auto-start", action="store_true", help="for sim_gui mode")
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
    else:
        run_sim(config, symbol=symbol, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
