import argparse
import json

from engine.data_engine import DataEngine
from engine.rsi_tuner import evaluate_candidate_walk_forward
from engine.strategy_state import StrategyState
from engine.walk_forward import run_walk_forward


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_config(cfg, path="config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def build_candidates(fast_min, fast_max, slow_min, slow_max, slow_step):
    candidates = []
    for fast in range(fast_min, fast_max + 1):
        for slow in range(slow_min, slow_max + 1, slow_step):
            if slow > fast:
                candidates.append({"fast": fast, "slow": slow})
    return candidates


def main():
    parser = argparse.ArgumentParser(description="Tune fast/slow by walk-forward result.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--train-size", type=int, default=480)
    parser.add_argument("--test-size", type=int, default=120)
    parser.add_argument("--step-size", type=int, default=120)
    parser.add_argument("--fast-min", type=int, default=3)
    parser.add_argument("--fast-max", type=int, default=10)
    parser.add_argument("--slow-min", type=int, default=10)
    parser.add_argument("--slow-max", type=int, default=60)
    parser.add_argument("--slow-step", type=int, default=2)
    parser.add_argument("--dd-penalty", type=float, default=0.5)
    parser.add_argument("--min-positive-windows", type=int, default=1)
    parser.add_argument("--allow-non-ma", action="store_true", help="allow tune for unsupported strategy names")
    args = parser.parse_args()

    cfg = load_config()
    strategy_name = cfg.get("strategy", {}).get("name", "ma")
    if strategy_name not in ("ma", "default", "rsi_ma", "rsi") and not args.allow_non_ma:
        print(f"Skip tune: unsupported strategy.name={strategy_name}")
        return

    symbol = args.symbol or cfg["symbol"]
    prices = DataEngine().get_price_series(symbol)

    candidates = build_candidates(
        fast_min=args.fast_min,
        fast_max=args.fast_max,
        slow_min=args.slow_min,
        slow_max=args.slow_max,
        slow_step=args.slow_step,
    )
    if not candidates:
        raise ValueError("No candidates generated")

    base_params = {
        "rsi_period": cfg["strategy"].get("rsi_period", 14),
        "rsi_overbought": cfg["strategy"].get("rsi_overbought", 70),
        "rsi_oversold": cfg["strategy"].get("rsi_oversold", 30),
        "min_diff": cfg["strategy"].get("min_diff", 0.0),
        "cooldown_bars": cfg["strategy"].get("cooldown_bars", 0),
        "max_consecutive_losses": cfg["strategy"].get("max_consecutive_losses"),
        "trend_filter": cfg["strategy"].get("trend_filter", False),
        "trend_window": cfg["strategy"].get("trend_window", 50),
    }

    best = None
    best_score = None
    best_summary = None
    for candidate in candidates:
        if strategy_name in ("rsi_ma", "rsi"):
            summary = evaluate_candidate_walk_forward(
                prices=prices,
                candidate=candidate,
                train_size=args.train_size,
                test_size=args.test_size,
                step_size=args.step_size,
                base_params=base_params,
                min_trades=0,
            )
        else:
            result = run_walk_forward(
                prices=prices,
                candidates=[candidate],
                train_size=args.train_size,
                test_size=args.test_size,
                step_size=args.step_size,
                objective="pnl",
                dd_penalty=0.0,
                min_trades=0,
            )
            summary = result["summary"]

        if summary["windows_valid"] == 0:
            continue
        if summary["windows_positive"] < args.min_positive_windows:
            continue
        score = float(summary["test_total_pnl"]) - args.dd_penalty * float(summary["test_avg_drawdown"])
        if best_score is None or score > best_score:
            best_score = score
            best = candidate
            best_summary = summary

    if not best:
        print("No suitable parameters found")
        return

    cfg["strategy"]["fast"] = best["fast"]
    cfg["strategy"]["slow"] = best["slow"]
    save_config(cfg, "config.json")

    StrategyState("state/strategy_state.json").save_params(
        {
            "fast": best["fast"],
            "slow": best["slow"],
            "mode": cfg["strategy"].get("mode"),
            "min_diff": cfg["strategy"].get("min_diff"),
            "trend_filter": cfg["strategy"].get("trend_filter"),
            "trend_window": cfg["strategy"].get("trend_window"),
            "rsi_period": cfg["strategy"].get("rsi_period"),
            "rsi_overbought": cfg["strategy"].get("rsi_overbought"),
            "rsi_oversold": cfg["strategy"].get("rsi_oversold"),
        }
    )

    print("Walk-forward tune completed")
    print(f"strategy_name={strategy_name}")
    print(f"symbol={symbol}")
    print(f"best_fast={best['fast']}")
    print(f"best_slow={best['slow']}")
    print(f"score={best_score}")
    print(f"summary={best_summary}")


if __name__ == "__main__":
    main()
