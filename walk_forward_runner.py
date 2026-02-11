import argparse
import csv
import json
import os

from engine.data_engine import DataEngine
from engine.walk_forward import run_walk_forward


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if not rows:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "window",
                    "train_start",
                    "train_end",
                    "test_start",
                    "test_end",
                    "best_fast",
                    "best_slow",
                    "train_score",
                    "train_pnl",
                    "train_max_drawdown",
                    "train_trades",
                    "test_pnl",
                    "test_max_drawdown",
                    "test_trades",
                ]
            )
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description="Run walk-forward validation for strategy params.")
    parser.add_argument("--symbol", default=None, help="contract symbol, default from config")
    parser.add_argument("--train-size", type=int, default=480, help="train window bars")
    parser.add_argument("--test-size", type=int, default=120, help="test window bars")
    parser.add_argument("--step-size", type=int, default=120, help="rolling step bars")
    parser.add_argument("--out-dir", default="output", help="output directory")
    args = parser.parse_args()

    cfg = load_config()
    symbol = args.symbol or cfg["symbol"]
    auto_tune_cfg = cfg.get("auto_tune", {})
    candidates = auto_tune_cfg.get("candidates", [])
    if not candidates:
        raise ValueError("auto_tune.candidates is empty")

    objective = auto_tune_cfg.get("objective", "pnl")
    dd_penalty = auto_tune_cfg.get("dd_penalty", 0.0)
    min_trades = auto_tune_cfg.get("min_trades", 0)

    data = DataEngine()
    prices = data.get_price_series(symbol)

    result = run_walk_forward(
        prices=prices,
        candidates=candidates,
        train_size=args.train_size,
        test_size=args.test_size,
        step_size=args.step_size,
        objective=objective,
        dd_penalty=dd_penalty,
        min_trades=min_trades,
    )

    os.makedirs(args.out_dir, exist_ok=True)
    csv_path = os.path.join(args.out_dir, f"walk_forward_{symbol}.csv")
    json_path = os.path.join(args.out_dir, f"walk_forward_{symbol}.json")
    write_csv(csv_path, result["rows"])
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result["summary"], f, ensure_ascii=False, indent=2)

    print("Walk-forward completed")
    print(f"symbol={symbol}")
    print(f"windows_total={result['summary']['windows_total']}")
    print(f"windows_valid={result['summary']['windows_valid']}")
    print(f"test_total_pnl={result['summary']['test_total_pnl']}")
    print(f"csv={csv_path}")
    print(f"json={json_path}")


if __name__ == "__main__":
    main()
