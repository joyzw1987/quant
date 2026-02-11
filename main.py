import csv
import json
import os
from datetime import datetime, time

from engine.execution_sim import SimExecution
from engine.strategy_factory import create_strategy
from engine.risk import RiskManager
from engine.data_engine import DataEngine
from engine.logger import Logger
from engine.alert_manager import AlertManager
from engine.market_hours import MarketHours
from engine.param_optimizer import pick_best_params
from engine.strategy_state import StrategyState
from engine.runtime_state import RuntimeState
from engine.config_validator import validate_config, report_validation
from engine.backtest_engine import run_backtest


_gui_started = False


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def parse_time(value):
    if not value:
        return None
    hour, minute = value.split(":")
    return time(int(hour), int(minute))


def parse_schedule(schedule_cfg):
    if not schedule_cfg:
        return None
    sessions = []
    for s in schedule_cfg.get("sessions", []):
        start = parse_time(s.get("start"))
        end = parse_time(s.get("end"))
        if start and end:
            sessions.append((start, end))
    return {"timezone": schedule_cfg.get("timezone", ""), "weekdays": schedule_cfg.get("weekdays", []), "sessions": sessions}


def schedule_allows(dt, schedule):
    if schedule is None:
        return True
    weekdays = schedule.get("weekdays", [])
    if weekdays:
        wd = dt.weekday() + 1
        if wd not in weekdays:
            return False
    sessions = schedule.get("sessions", [])
    if not sessions:
        return True
    t = dt.time()
    for start, end in sessions:
        if start <= t <= end:
            return True
    return False


def compute_stats(trades):
    total_trades = len(trades)
    total_pnl = sum(t["pnl"] for t in trades)
    win_trades = [t for t in trades if t["pnl"] > 0]
    loss_trades = [t for t in trades if t["pnl"] <= 0]
    win_rate = (len(win_trades) / total_trades * 100) if total_trades else 0
    avg_win = sum(t["pnl"] for t in win_trades) / len(win_trades) if win_trades else 0
    avg_loss = sum(t["pnl"] for t in loss_trades) / len(loss_trades) if loss_trades else 0
    profit_factor = (sum(t["pnl"] for t in win_trades) / abs(sum(t["pnl"] for t in loss_trades))) if loss_trades else 0.0
    expectancy = (total_pnl / total_trades) if total_trades else 0.0
    return total_trades, total_pnl, win_rate, avg_win, avg_loss, profit_factor, expectancy


def compute_max_drawdown(equity_curve):
    peak = None
    max_drawdown = 0.0
    for row in equity_curve:
        equity = float(row.get("equity", row.get("cash", 0.0)))
        if peak is None or equity > peak:
            peak = equity
        drawdown = peak - equity
        row["drawdown"] = drawdown
        if drawdown > max_drawdown:
            max_drawdown = drawdown
    return max_drawdown


def main(symbol_override=None, output_dir="output"):
    config = load_config()
    errors, warnings = validate_config(config, mode="paper")
    report_validation(errors, warnings)

    symbol = symbol_override or config["symbol"]

    data = DataEngine()
    os.makedirs(output_dir, exist_ok=True)
    bars = data.get_bars(symbol)
    data_report = data.validate_bars(bars)
    data.write_data_report(data_report, os.path.join(output_dir, "data_quality_report.txt"))

    strategy_cfg = config["strategy"]
    strategy = create_strategy(strategy_cfg)

    auto_tune_cfg = config.get("auto_tune", {"enabled": False})
    last_tune_date = None
    last_tune_step = None

    state_store = StrategyState("state/strategy_state.json")
    last_state = state_store.load()
    if last_state.get("params"):
        params = last_state["params"]
        strategy.set_params(
            fast=params.get("fast"),
            slow=params.get("slow"),
            mode=params.get("mode"),
            min_diff=params.get("min_diff"),
            trend_filter=params.get("trend_filter"),
            trend_window=params.get("trend_window"),
            rsi_period=params.get("rsi_period"),
            rsi_overbought=params.get("rsi_overbought"),
            rsi_oversold=params.get("rsi_oversold"),
        )
    else:
        state_store.save_params({
            "fast": getattr(strategy, "fast", None),
            "slow": getattr(strategy, "slow", None),
            "mode": getattr(strategy, "mode", None),
            "min_diff": getattr(strategy, "min_diff", None),
        })

    trade_start = parse_time(strategy_cfg.get("trade_start", ""))
    trade_end = parse_time(strategy_cfg.get("trade_end", ""))

    # Prefer market_hours in config, keep backward compatibility with legacy schedule.
    schedule_cfg = config.get("market_hours") or config.get("schedule")
    schedule = parse_schedule(schedule_cfg)

    risk_cfg = config["risk"]
    risk = RiskManager(
        stop_loss_percentage=risk_cfg["stop_loss_percentage"],
        daily_loss_limit=risk_cfg["daily_loss_limit"],
        max_drawdown=risk_cfg["max_drawdown"],
        max_drawdown_pct=risk_cfg.get("max_drawdown_pct"),
        max_consecutive_losses=risk_cfg["max_consecutive_losses"],
        risk_per_trade=risk_cfg["risk_per_trade"],
        atr_period=risk_cfg["atr_period"],
        atr_multiplier=risk_cfg["atr_multiplier"],
        take_profit_multiplier=risk_cfg["take_profit_multiplier"],
    )

    execution = SimExecution(
        slippage=config["contract"]["slippage"],
        contract_multiplier=config["contract"].get("multiplier", 1),
        commission_per_contract=config["contract"].get("commission_per_contract", 0.0),
        commission_min=config["contract"].get("commission_min", 0.0),
    )

    logger = Logger(config.get("monitor", {}).get("log_file", "logs/runtime.log"))
    alert = AlertManager(config.get("monitor", {}).get("alert_file", "logs/alerts.log"))
    runtime = RuntimeState("state/runtime_state.json")

    initial_capital = config["backtest"]["initial_capital"]
    capital = initial_capital
    equity_curve = []
    daily_trade_count = 0
    max_trades_per_day = config["backtest"]["max_trades_per_day"]

    def update_runtime(extra=None):
        payload = {
            "symbol": symbol,
            "capital": capital,
            "position": execution.position,
            "trades": len(execution.trades),
            "halt_reason": risk.halt_reason,
        }
        if extra:
            payload.update(extra)
        runtime.update(payload)

    result = run_backtest(
        bars=bars,
        strategy=strategy,
        risk=risk,
        execution=execution,
        strategy_cfg=strategy_cfg,
        symbol=symbol,
        max_trades_per_day=max_trades_per_day,
        trade_start=trade_start,
        trade_end=trade_end,
        schedule=schedule,
        initial_capital=initial_capital,
        schedule_checker=schedule_allows,
        runtime_update=update_runtime,
    )
    capital = result["capital"]
    equity_curve = result["equity_curve"]

    total_trades, total_pnl, win_rate, avg_win, avg_loss, profit_factor, expectancy = compute_stats(execution.trades)
    final_capital = initial_capital + total_pnl
    max_drawdown = compute_max_drawdown(equity_curve)

    with open(os.path.join(output_dir, "equity_curve.csv"), "w", newline="", encoding="utf-8") as f:
        fieldnames = ["step", "cash", "unrealized", "equity", "drawdown", "datetime"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in equity_curve:
            writer.writerow(row)

    with open(os.path.join(output_dir, "trades.csv"), "w", newline="", encoding="utf-8") as f:
        if execution.trades:
            fieldnames = list(execution.trades[0].keys())
        else:
            fieldnames = ["direction", "entry_price", "exit_price", "size", "pnl"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for t in execution.trades:
            writer.writerow(t)

    performance = {
        "initial_capital": initial_capital,
        "final_capital": final_capital,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "total_pnl": total_pnl,
        "max_drawdown": max_drawdown,
        "profit_factor": profit_factor,
        "sharpe": 0.0,
        "avg_win": avg_win,
        "avg_loss": avg_loss,
        "expectancy": expectancy,
        "r_multiple_avg": 0.0,
        "r_multiple_sum": 0.0,
    }
    with open(os.path.join(output_dir, "performance.json"), "w", encoding="utf-8") as f:
        json.dump(performance, f, ensure_ascii=False, indent=2)

    print("\n===== PERFORMANCE =====")
    print(f"Initial Capital: {initial_capital}")
    print(f"Final Capital: {final_capital}")
    print(f"Total Trades: {total_trades}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Total PnL: {total_pnl}")


if __name__ == "__main__":
    main()
