from engine.strategy import Strategy, StrategyComposite, RSIMAStrategy


def create_strategy(strategy_cfg):
    name = strategy_cfg.get("name", "ma")
    if name in ("ma", "default"):
        return Strategy(
            fast=strategy_cfg["fast"],
            slow=strategy_cfg["slow"],
            mode=strategy_cfg["mode"],
            min_diff=strategy_cfg["min_diff"],
            cooldown_bars=strategy_cfg.get("cooldown_bars", 0),
            max_consecutive_losses=strategy_cfg.get("max_consecutive_losses"),
            trend_filter=strategy_cfg.get("trend_filter", False),
            trend_window=strategy_cfg.get("trend_window", 50),
        )
    if name in ("rsi_ma", "rsi"):
        return RSIMAStrategy(
            rsi_period=strategy_cfg.get("rsi_period", 14),
            rsi_overbought=strategy_cfg.get("rsi_overbought", 70),
            rsi_oversold=strategy_cfg.get("rsi_oversold", 30),
            fast=strategy_cfg.get("fast", 5),
            slow=strategy_cfg.get("slow", 20),
            min_diff=strategy_cfg.get("min_diff", 0.0),
            cooldown_bars=strategy_cfg.get("cooldown_bars", 0),
            max_consecutive_losses=strategy_cfg.get("max_consecutive_losses"),
            trend_filter=strategy_cfg.get("trend_filter", False),
            trend_window=strategy_cfg.get("trend_window", 50),
        )
    if name in ("multi", "ensemble"):
        members_cfg = strategy_cfg.get("members", [])
        if not members_cfg:
            raise ValueError("StrategyComposite requires members")
        members = [create_strategy(cfg) for cfg in members_cfg]
        return StrategyComposite(
            members=members,
            weights=strategy_cfg.get("weights"),
            threshold=strategy_cfg.get("threshold", 0.0),
        )
    raise ValueError(f"Unknown strategy name: {name}")
