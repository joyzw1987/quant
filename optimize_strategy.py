import argparse
import json
from copy import deepcopy
from datetime import datetime

from engine.data_engine import DataEngine
from engine.backtest_eval import run_once
from engine.strategy_state import StrategyState


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def save_config(cfg, path="config.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def frange(start, end, step):
    values = []
    x = start
    while x <= end + 1e-9:
        values.append(round(x, 6))
        x += step
    return values


def main():
    parser = argparse.ArgumentParser(description="Two-stage strategy optimizer for current dataset.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--score-dd-penalty", type=float, default=0.4)
    parser.add_argument("--min-trades", type=int, default=4)
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--apply", action="store_true", default=True)
    parser.add_argument("--no-apply", action="store_true")
    args = parser.parse_args()

    config = load_config()
    if args.symbol:
        config["symbol"] = args.symbol

    bars = DataEngine().get_bars(config["symbol"])
    base_strategy = deepcopy(config["strategy"])
    strategy_name = base_strategy.get("name", "ma")
    if strategy_name not in ("rsi_ma", "rsi"):
        raise SystemExit(f"Only rsi_ma/rsi supported in this optimizer, got: {strategy_name}")

    penalty = args.score_dd_penalty
    min_trades = max(0, int(args.min_trades))

    stage1_results = []
    for fast in range(3, 10):
        for slow in range(20, 71, 4):
            if slow <= fast:
                continue
            for min_diff in frange(0.2, 1.2, 0.2):
                cfg = deepcopy(base_strategy)
                cfg["fast"] = fast
                cfg["slow"] = slow
                cfg["min_diff"] = float(min_diff)
                stats = run_once(config, bars, cfg)
                if stats["trades"] < min_trades:
                    continue
                score = stats["pnl"] - penalty * stats["max_drawdown"]
                stage1_results.append((score, cfg, stats))

    if not stage1_results:
        raise SystemExit("No candidate passed stage-1 constraints.")

    stage1_results.sort(key=lambda x: x[0], reverse=True)
    top_stage1 = stage1_results[: max(1, int(args.top_k))]

    stage2_results = []
    for _, cfg0, _ in top_stage1:
        for rsi_period in [10, 12, 14, 16]:
            for rsi_overbought in [58, 60, 62, 65]:
                for rsi_oversold in [35, 38, 40, 42]:
                    if rsi_oversold >= rsi_overbought:
                        continue
                    cfg = deepcopy(cfg0)
                    cfg["rsi_period"] = rsi_period
                    cfg["rsi_overbought"] = rsi_overbought
                    cfg["rsi_oversold"] = rsi_oversold
                    stats = run_once(config, bars, cfg)
                    if stats["trades"] < min_trades:
                        continue
                    score = stats["pnl"] - penalty * stats["max_drawdown"]
                    stage2_results.append((score, cfg, stats))

    if not stage2_results:
        raise SystemExit("No candidate passed stage-2 constraints.")

    stage2_results.sort(key=lambda x: x[0], reverse=True)
    best_score, best_cfg, best_stats = stage2_results[0]

    baseline_stats = run_once(config, bars, base_strategy)
    baseline_score = baseline_stats["pnl"] - penalty * baseline_stats["max_drawdown"]

    report = {
        "symbol": config["symbol"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "baseline": {
            "params": base_strategy,
            "stats": baseline_stats,
            "score": baseline_score,
        },
        "best": {
            "params": best_cfg,
            "stats": best_stats,
            "score": best_score,
        },
        "search": {
            "stage1_candidates": len(stage1_results),
            "stage2_candidates": len(stage2_results),
            "dd_penalty": penalty,
            "min_trades": min_trades,
        },
    }

    with open("output/strategy_optimization.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    apply = not args.no_apply
    if apply:
        config["strategy"].update(
            {
                "fast": best_cfg["fast"],
                "slow": best_cfg["slow"],
                "min_diff": best_cfg["min_diff"],
                "rsi_period": best_cfg["rsi_period"],
                "rsi_overbought": best_cfg["rsi_overbought"],
                "rsi_oversold": best_cfg["rsi_oversold"],
            }
        )
        save_config(config, "config.json")
        StrategyState("state/strategy_state.json").save_params(
            {
                "fast": best_cfg["fast"],
                "slow": best_cfg["slow"],
                "mode": config["strategy"].get("mode"),
                "min_diff": best_cfg["min_diff"],
                "trend_filter": config["strategy"].get("trend_filter"),
                "trend_window": config["strategy"].get("trend_window"),
                "rsi_period": best_cfg["rsi_period"],
                "rsi_overbought": best_cfg["rsi_overbought"],
                "rsi_oversold": best_cfg["rsi_oversold"],
            }
        )

    print("Optimization completed")
    print(f"baseline_score={baseline_score}")
    print(f"baseline_stats={baseline_stats}")
    print(f"best_score={best_score}")
    print(f"best_stats={best_stats}")
    print(f"best_params={best_cfg}")
    print(f"applied={apply}")


if __name__ == "__main__":
    main()
