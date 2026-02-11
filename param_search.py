import json

from engine.param_optimizer import pick_best_params_scored
from engine.data_engine import DataEngine
from engine.strategy_state import StrategyState


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    cfg = load_config()
    data = DataEngine()
    prices = data.get_price_series(cfg["symbol"])
    candidates = cfg.get("auto_tune", {}).get("candidates", [])
    objective = cfg.get("auto_tune", {}).get("objective", "pnl")
    dd_penalty = cfg.get("auto_tune", {}).get("dd_penalty", 0.0)
    min_trades = cfg.get("auto_tune", {}).get("min_trades", 0)

    best, score, stats = pick_best_params_scored(prices, candidates, objective=objective, dd_penalty=dd_penalty, min_trades=min_trades)
    if not best:
        print("No suitable params found")
        return

    cfg["strategy"]["fast"] = best["fast"]
    cfg["strategy"]["slow"] = best["slow"]
    with open("config.json", "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    StrategyState("state/strategy_state.json").save_params({
        "fast": best["fast"],
        "slow": best["slow"],
        "mode": cfg["strategy"].get("mode"),
        "min_diff": cfg["strategy"].get("min_diff"),
    })

    print(f"best={best} score={score} stats={stats}")


if __name__ == "__main__":
    main()
