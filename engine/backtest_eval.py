from datetime import datetime, time

from engine.backtest_engine import run_backtest
from engine.cost_model import build_cost_model
from engine.execution_sim import SimExecution
from engine.risk import RiskManager
from engine.strategy_factory import create_strategy


def parse_time(value):
    if not value:
        return None
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def parse_schedule(schedule_cfg):
    if not schedule_cfg:
        return None
    sessions = []
    for session_cfg in schedule_cfg.get("sessions", []):
        start = parse_time(session_cfg.get("start"))
        end = parse_time(session_cfg.get("end"))
        if start and end:
            sessions.append((start, end))
    return {"weekdays": schedule_cfg.get("weekdays", []), "sessions": sessions}


def schedule_allows(dt, schedule):
    if schedule is None:
        return True
    weekdays = schedule.get("weekdays", [])
    if weekdays:
        weekday = dt.weekday() + 1
        if weekday not in weekdays:
            return False
    sessions = schedule.get("sessions", [])
    if not sessions:
        return True
    now_t = dt.time()
    for start, end in sessions:
        if start <= now_t <= end:
            return True
    return False


def compute_max_drawdown(equity_curve):
    peak = None
    max_drawdown = 0.0
    for row in equity_curve:
        equity = float(row.get("equity", row.get("cash", 0.0)))
        if peak is None or equity > peak:
            peak = equity
        drawdown = peak - equity
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def build_risk(config):
    risk_cfg = config["risk"]
    return RiskManager(
        stop_loss_percentage=risk_cfg["stop_loss_percentage"],
        daily_loss_limit=risk_cfg["daily_loss_limit"],
        max_drawdown=risk_cfg["max_drawdown"],
        max_drawdown_pct=risk_cfg.get("max_drawdown_pct"),
        max_consecutive_losses=risk_cfg["max_consecutive_losses"],
        risk_per_trade=risk_cfg["risk_per_trade"],
        atr_period=risk_cfg["atr_period"],
        atr_multiplier=risk_cfg["atr_multiplier"],
        take_profit_multiplier=risk_cfg["take_profit_multiplier"],
        max_orders_per_day=risk_cfg.get("max_orders_per_day"),
        loss_streak_reduce_ratio=risk_cfg.get("loss_streak_reduce_ratio", 0.0),
        loss_streak_min_multiplier=risk_cfg.get("loss_streak_min_multiplier", 0.2),
        volatility_halt_atr=risk_cfg.get("volatility_halt_atr"),
        volatility_resume_atr=risk_cfg.get("volatility_resume_atr"),
    )


def run_once(config, bars, strategy_cfg):
    execution = SimExecution(
        slippage=config["contract"]["slippage"],
        contract_multiplier=config["contract"].get("multiplier", 1),
        commission_per_contract=config["contract"].get("commission_per_contract", 0.0),
        commission_min=config["contract"].get("commission_min", 0.0),
        fill_ratio_min=config["contract"].get("fill_ratio_min", 1.0),
        fill_ratio_max=config["contract"].get("fill_ratio_max", 1.0),
        cost_model=build_cost_model(config),
    )
    risk = build_risk(config)
    strategy = create_strategy(strategy_cfg)

    trade_start = parse_time(strategy_cfg.get("trade_start", ""))
    trade_end = parse_time(strategy_cfg.get("trade_end", ""))
    schedule_cfg = config.get("market_hours") or config.get("schedule")
    schedule = parse_schedule(schedule_cfg)

    result = run_backtest(
        bars=bars,
        strategy=strategy,
        risk=risk,
        execution=execution,
        strategy_cfg=strategy_cfg,
        symbol=config["symbol"],
        max_trades_per_day=config["backtest"]["max_trades_per_day"],
        trade_start=trade_start,
        trade_end=trade_end,
        schedule=schedule,
        initial_capital=config["backtest"]["initial_capital"],
        schedule_checker=schedule_allows,
        runtime_update=None,
    )

    total_pnl = sum(trade["pnl"] for trade in execution.trades)
    return {
        "pnl": float(total_pnl),
        "trades": int(len(execution.trades)),
        "max_drawdown": float(compute_max_drawdown(result["equity_curve"])),
    }

