import argparse
import json
from copy import deepcopy
from datetime import datetime

from engine.data_engine import DataEngine
from engine.backtest_eval import run_once
from engine.param_version_store import ParamVersionStore


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def frange(start, end, step):
    values = []
    x = float(start)
    while x <= float(end) + 1e-9:
        values.append(round(x, 6))
        x += float(step)
    return values


def build_candidates(config, top_n=400):
    strategy = config.get("strategy", {})
    name = strategy.get("name", "ma")
    auto_cfg = config.get("auto_adjust", {})

    candidates = []
    fast_min = int(auto_cfg.get("fast_min", 3))
    fast_max = int(auto_cfg.get("fast_max", 10))
    slow_min = int(auto_cfg.get("slow_min", 10))
    slow_max = int(auto_cfg.get("slow_max", 60))
    slow_step = int(auto_cfg.get("slow_step", 2))

    min_diff_values = [strategy.get("min_diff", 0.0)]
    if name in ("rsi_ma", "rsi"):
        min_diff_values = frange(0.2, 1.2, 0.2)
        rsi_period_values = [10, 12, 14, 16]
        rsi_ob_values = [58, 60, 62, 65]
        rsi_os_values = [35, 38, 40, 42]
    else:
        rsi_period_values = [strategy.get("rsi_period", 14)]
        rsi_ob_values = [strategy.get("rsi_overbought", 70)]
        rsi_os_values = [strategy.get("rsi_oversold", 30)]

    for fast in range(fast_min, fast_max + 1):
        for slow in range(slow_min, slow_max + 1, slow_step):
            if slow <= fast:
                continue
            for min_diff in min_diff_values:
                base = deepcopy(strategy)
                base["fast"] = fast
                base["slow"] = slow
                base["min_diff"] = min_diff
                if name in ("rsi_ma", "rsi"):
                    for rsi_period in rsi_period_values:
                        for rsi_ob in rsi_ob_values:
                            for rsi_os in rsi_os_values:
                                if rsi_os >= rsi_ob:
                                    continue
                                item = deepcopy(base)
                                item["rsi_period"] = rsi_period
                                item["rsi_overbought"] = rsi_ob
                                item["rsi_oversold"] = rsi_os
                                candidates.append(item)
                else:
                    candidates.append(base)

    if len(candidates) <= top_n:
        return candidates

    # Keep candidate pool bounded for runtime control.
    stride = max(1, len(candidates) // top_n)
    slim = [candidates[i] for i in range(0, len(candidates), stride)]
    return slim[:top_n]


def score_of(stats, dd_penalty):
    return float(stats["pnl"]) - float(dd_penalty) * float(stats["max_drawdown"])


def choose_winner(
    baseline_stats,
    baseline_score,
    tuned_stats,
    tuned_score,
    min_holdout_trades,
    min_score_improve,
    require_positive_holdout=False,
):
    score_improve = float(tuned_score) - float(baseline_score)
    reasons = []
    gate_pass = True

    if tuned_score <= baseline_score:
        gate_pass = False
        reasons.append("tuned_score_not_better_than_baseline")
    if int(tuned_stats.get("trades", 0)) < int(min_holdout_trades):
        gate_pass = False
        reasons.append("holdout_trades_below_threshold")
    if score_improve < float(min_score_improve):
        gate_pass = False
        reasons.append("score_improve_below_threshold")
    if require_positive_holdout and float(tuned_stats.get("pnl", 0.0)) <= 0:
        gate_pass = False
        reasons.append("holdout_pnl_not_positive")

    winner = "tuned" if gate_pass else "baseline"
    if gate_pass:
        reasons.append("gate_passed")

    return {
        "winner": winner,
        "gate_pass": gate_pass,
        "score_improve": score_improve,
        "reasons": reasons,
    }


def pick_best(config, bars, candidates, dd_penalty=0.4, min_trades=4):
    best = None
    best_stats = None
    best_score = None
    for candidate in candidates:
        stats = run_once(config, bars, candidate)
        if stats["trades"] < min_trades:
            continue
        score = score_of(stats, dd_penalty)
        if best_score is None or score > best_score:
            best = candidate
            best_stats = stats
            best_score = score
    return best, best_stats, best_score


def main():
    parser = argparse.ArgumentParser(description="Strict out-of-sample validation.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--holdout-bars", type=int, default=240, help="final unseen segment bars")
    parser.add_argument("--dd-penalty", type=float, default=0.4)
    parser.add_argument("--min-trades", type=int, default=4)
    parser.add_argument("--max-candidates", type=int, default=400)
    parser.add_argument("--min-holdout-trades", type=int, default=4)
    parser.add_argument("--min-score-improve", type=float, default=0.0)
    parser.add_argument("--require-positive-holdout", action="store_true")
    parser.add_argument("--apply-best", action="store_true")
    args = parser.parse_args()

    config = load_config()
    if args.symbol:
        config["symbol"] = args.symbol

    bars = DataEngine().get_bars(config["symbol"])
    holdout_bars = max(60, int(args.holdout_bars))
    if len(bars) <= holdout_bars + 120:
        raise SystemExit("Not enough bars for strict OOS split.")

    train_bars = bars[:-holdout_bars]
    oos_bars = bars[-holdout_bars:]
    baseline_cfg = deepcopy(config["strategy"])

    candidates = build_candidates(config, top_n=max(50, int(args.max_candidates)))
    best_cfg, best_train_stats, best_train_score = pick_best(
        config=config,
        bars=train_bars,
        candidates=candidates,
        dd_penalty=args.dd_penalty,
        min_trades=max(0, int(args.min_trades)),
    )
    if not best_cfg:
        raise SystemExit("No candidate passed constraints on train segment.")

    baseline_oos_stats = run_once(config, oos_bars, baseline_cfg)
    baseline_oos_score = score_of(baseline_oos_stats, args.dd_penalty)
    best_oos_stats = run_once(config, oos_bars, best_cfg)
    best_oos_score = score_of(best_oos_stats, args.dd_penalty)

    decision = choose_winner(
        baseline_stats=baseline_oos_stats,
        baseline_score=baseline_oos_score,
        tuned_stats=best_oos_stats,
        tuned_score=best_oos_score,
        min_holdout_trades=max(0, int(args.min_holdout_trades)),
        min_score_improve=float(args.min_score_improve),
        require_positive_holdout=bool(args.require_positive_holdout),
    )
    winner = decision["winner"]
    winner_cfg = baseline_cfg if winner == "baseline" else best_cfg

    if args.apply_best and winner == "tuned":
        config["strategy"] = winner_cfg
        with open("config.json", "w", encoding="utf-8") as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        version = ParamVersionStore("state/param_versions.json").append(
            symbol=config["symbol"],
            params={
                "fast": winner_cfg.get("fast"),
                "slow": winner_cfg.get("slow"),
                "mode": winner_cfg.get("mode"),
                "min_diff": winner_cfg.get("min_diff"),
                "trend_filter": winner_cfg.get("trend_filter"),
                "trend_window": winner_cfg.get("trend_window"),
                "rsi_period": winner_cfg.get("rsi_period"),
                "rsi_overbought": winner_cfg.get("rsi_overbought"),
                "rsi_oversold": winner_cfg.get("rsi_oversold"),
            },
            source="strict_oos_validate",
            metrics={
                "baseline_holdout_score": baseline_oos_score,
                "tuned_holdout_score": best_oos_score,
                "score_improve": decision.get("score_improve"),
            },
            note="applied by strict_oos_validate",
        )
    else:
        version = None

    report = {
        "symbol": config["symbol"],
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "split": {
            "total_bars": len(bars),
            "train_bars": len(train_bars),
            "holdout_bars": len(oos_bars),
            "holdout_start": oos_bars[0]["datetime"],
            "holdout_end": oos_bars[-1]["datetime"],
        },
        "search": {
            "candidate_count": len(candidates),
            "dd_penalty": args.dd_penalty,
            "min_trades": args.min_trades,
            "min_holdout_trades": args.min_holdout_trades,
            "min_score_improve": args.min_score_improve,
            "require_positive_holdout": bool(args.require_positive_holdout),
        },
        "baseline": {
            "params": baseline_cfg,
            "holdout_stats": baseline_oos_stats,
            "holdout_score": baseline_oos_score,
        },
        "tuned": {
            "params": best_cfg,
            "train_stats": best_train_stats,
            "train_score": best_train_score,
            "holdout_stats": best_oos_stats,
            "holdout_score": best_oos_score,
        },
        "decision": decision,
        "winner": winner,
        "applied": bool(args.apply_best and winner == "tuned"),
        "version": version,
    }
    with open("output/strict_oos_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print("Strict OOS validation completed")
    print(f"symbol={config['symbol']}")
    print(f"train_bars={len(train_bars)} holdout_bars={len(oos_bars)}")
    print(f"baseline_holdout={baseline_oos_stats}")
    print(f"tuned_holdout={best_oos_stats}")
    print(f"decision={decision}")
    print(f"winner={winner} applied={report['applied']}")


if __name__ == "__main__":
    main()
