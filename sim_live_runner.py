import argparse
import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime

from engine.alert_manager import AlertManager
from engine.config_validator import report_validation, validate_config
from engine.cost_model import build_cost_model
from engine.data_engine import DataEngine
from engine.data_quality_gate import evaluate_data_quality
from engine.execution_sim import SimExecution
from engine.market_scheduler import is_market_open, load_market_schedule, next_market_open
from engine.risk import RiskManager
from engine.runtime_state import RuntimeState
from engine.strategy_factory import create_strategy
from main import main as backtest_main
from paper_consistency_check import build_report as build_paper_check_report
from paper_consistency_check import check_trades
from paper_consistency_check import write_report as write_paper_check_report


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _read_perf(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _run_fetch(symbol, out_path, source):
    cmd = [
        sys.executable,
        "data_update_merge.py",
        "--symbol",
        symbol,
        "--out",
        out_path,
        "--source",
        source,
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _read_latest_bar_time(path):
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            lines = [line.strip() for line in f if line.strip()]
        if len(lines) <= 1:
            return ""
        # csv: datetime,open,high,low,close
        return lines[-1].split(",")[0]
    except Exception:
        return ""


def _read_bars(path):
    if not os.path.exists(path):
        return []
    bars = []
    with open(path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            normalized = {(k or "").replace("\ufeff", ""): v for k, v in row.items()}
            bars.append(
                {
                    "datetime": normalized["datetime"],
                    "open": float(normalized["open"]),
                    "high": float(normalized["high"]),
                    "low": float(normalized["low"]),
                    "close": float(normalized["close"]),
                }
            )
    return bars


def _parse_hhmm(value):
    if not value:
        return None
    text = str(value).strip()
    if ":" not in text:
        return None
    hh, mm = text.split(":", 1)
    if not hh.isdigit() or not mm.isdigit():
        return None
    h, m = int(hh), int(mm)
    if h < 0 or h > 23 or m < 0 or m > 59:
        return None
    return h, m


def _in_trade_window(bar_dt, start_hm, end_hm):
    if start_hm is None and end_hm is None:
        return True
    cur = bar_dt.hour * 60 + bar_dt.minute
    if start_hm is not None:
        s = start_hm[0] * 60 + start_hm[1]
        if cur < s:
            return False
    if end_hm is not None:
        e = end_hm[0] * 60 + end_hm[1]
        if cur > e:
            return False
    return True


def compute_runtime_metrics(initial_capital, capital, trades, equity_curve):
    total_pnl = float(capital) - float(initial_capital)
    total_trades = len(trades or [])
    win_trades = sum(1 for t in (trades or []) if float((t or {}).get("pnl", 0.0)) > 0)
    win_rate = (win_trades / total_trades * 100.0) if total_trades > 0 else 0.0
    peak = None
    max_dd = 0.0
    for row in equity_curve or []:
        eq = float(row.get("equity", row.get("cash", capital)))
        if peak is None or eq > peak:
            peak = eq
        dd = peak - eq
        if dd > max_dd:
            max_dd = dd
    return {
        "total_pnl": total_pnl,
        "win_rate": win_rate,
        "runtime_drawdown": max_dd,
    }


class ContinuousPaperSession:
    def __init__(self, cfg, symbol, output_dir):
        self.cfg = cfg
        self.symbol = symbol
        self.output_dir = output_dir
        self.strategy_cfg = cfg.get("strategy", {})
        self.strategy = create_strategy(self.strategy_cfg)

        risk_cfg = cfg["risk"]
        self.risk = RiskManager(
            stop_loss_percentage=risk_cfg["stop_loss_percentage"],
            daily_loss_limit=risk_cfg["daily_loss_limit"],
            max_drawdown=risk_cfg["max_drawdown"],
            max_drawdown_pct=risk_cfg.get("max_drawdown_pct"),
            max_consecutive_losses=risk_cfg["max_consecutive_losses"],
            risk_per_trade=risk_cfg["risk_per_trade"],
            atr_period=risk_cfg["atr_period"],
            atr_multiplier=risk_cfg["atr_multiplier"],
            take_profit_multiplier=risk_cfg["take_profit_multiplier"],
            max_position_size=risk_cfg.get("max_position_size"),
            max_orders_per_day=risk_cfg.get("max_orders_per_day"),
            min_seconds_between_orders=risk_cfg.get("min_seconds_between_orders", 0),
            max_total_position=risk_cfg.get("max_total_position"),
            max_symbol_position=risk_cfg.get("max_symbol_position"),
            max_total_notional=risk_cfg.get("max_total_notional"),
            max_symbol_notional=risk_cfg.get("max_symbol_notional"),
            max_total_exposure_pct=risk_cfg.get("max_total_exposure_pct"),
            max_symbol_exposure_pct=risk_cfg.get("max_symbol_exposure_pct"),
            max_slippage=risk_cfg.get("max_slippage"),
            loss_streak_reduce_ratio=risk_cfg.get("loss_streak_reduce_ratio", 0.0),
            loss_streak_min_multiplier=risk_cfg.get("loss_streak_min_multiplier", 0.2),
            volatility_halt_atr=risk_cfg.get("volatility_halt_atr"),
            volatility_resume_atr=risk_cfg.get("volatility_resume_atr"),
        )

        self.execution = SimExecution(
            slippage=cfg["contract"]["slippage"],
            contract_multiplier=cfg["contract"].get("multiplier", 1),
            commission_per_contract=cfg["contract"].get("commission_per_contract", 0.0),
            commission_min=cfg["contract"].get("commission_min", 0.0),
            fill_ratio_min=cfg["contract"].get("fill_ratio_min", 1.0),
            fill_ratio_max=cfg["contract"].get("fill_ratio_max", 1.0),
            cost_model=build_cost_model(cfg),
        )

        self.initial_capital = cfg["backtest"]["initial_capital"]
        self.capital = self.initial_capital
        self.max_trades_per_day = cfg["backtest"]["max_trades_per_day"]
        self.current_date = None
        self.daily_trade_count = 0
        self.last_gate_reason = None
        self.equity_curve = []
        self.last_processed_idx = -1
        self.trade_start = _parse_hhmm(self.strategy_cfg.get("trade_start", ""))
        self.trade_end = _parse_hhmm(self.strategy_cfg.get("trade_end", ""))

    def _append_equity(self, idx, bar):
        self.equity_curve.append(
            {
                "step": idx,
                "cash": self.capital,
                "unrealized": 0.0,
                "equity": self.capital,
                "drawdown": 0.0,
                "datetime": bar["datetime"],
            }
        )

    def _runtime_metrics(self):
        return compute_runtime_metrics(
            initial_capital=self.initial_capital,
            capital=self.capital,
            trades=self.execution.trades,
            equity_curve=self.equity_curve,
        )

    def process_bars(self, bars, start_idx, runtime):
        processed = 0
        for idx in range(start_idx, len(bars)):
            bar = bars[idx]
            bar_dt = datetime.strptime(bar["datetime"], "%Y-%m-%d %H:%M")
            bar_date = bar_dt.date()
            price = bar["close"]
            processed += 1

            if self.current_date is None or bar_date != self.current_date:
                self.current_date = bar_date
                self.daily_trade_count = 0
                self.risk.on_new_day()
                if hasattr(self.strategy, "on_new_day"):
                    self.strategy.on_new_day()
                runtime.update(
                    {
                        "event": "new_day",
                        "mode": "sim_live",
                        "symbol": self.symbol,
                        "trading_day": str(bar_date),
                        "capital": self.capital,
                        "position": self.execution.position,
                        "trades": len(self.execution.trades),
                    }
                )

            atr = self.risk.update_atr(bars[: idx + 1])
            if hasattr(self.risk, "update_volatility_pause"):
                self.risk.update_volatility_pause(atr)
            metrics = self._runtime_metrics()

            runtime.update(
                {
                    "event": "tick",
                    "mode": "sim_live",
                    "symbol": self.symbol,
                    "last_step": idx,
                    "last_bar_time": bar["datetime"],
                    "last_price": price,
                    "capital": self.capital,
                    "position": self.execution.position,
                    "trades": len(self.execution.trades),
                    "halt_reason": self.risk.halt_reason,
                    "gate_reason": self.last_gate_reason,
                    "total_pnl": metrics["total_pnl"],
                    "win_rate": metrics["win_rate"],
                    "runtime_drawdown": metrics["runtime_drawdown"],
                }
            )

            if self.execution.position is not None:
                closed, pnl = self.execution.check_exit(price, self.risk, bar_time=bar["datetime"])
                if closed:
                    self.capital += pnl
                    self.risk.update_after_trade(pnl, self.capital)
                    if hasattr(self.strategy, "on_trade_close"):
                        self.strategy.on_trade_close(pnl, idx)
                    metrics = self._runtime_metrics()
                    runtime.update(
                        {
                            "event": "trade_close",
                            "mode": "sim_live",
                            "symbol": self.symbol,
                            "last_step": idx,
                            "last_bar_time": bar["datetime"],
                            "last_price": price,
                            "capital": self.capital,
                            "position": self.execution.position,
                            "trades": len(self.execution.trades),
                            "last_trade": self.execution.trades[-1] if self.execution.trades else None,
                            "halt_reason": self.risk.halt_reason,
                            "total_pnl": metrics["total_pnl"],
                            "win_rate": metrics["win_rate"],
                            "runtime_drawdown": metrics["runtime_drawdown"],
                        }
                    )
                self._append_equity(idx, bar)
                continue

            if self.daily_trade_count >= self.max_trades_per_day:
                self.last_gate_reason = "MAX_TRADES_PER_DAY"
                self._append_equity(idx, bar)
                continue

            if not _in_trade_window(bar_dt, self.trade_start, self.trade_end):
                self.last_gate_reason = "OUTSIDE_TRADE_WINDOW"
                self._append_equity(idx, bar)
                continue

            if not self.risk.allow_trade():
                self.last_gate_reason = "RISK_NOT_ALLOWED"
                self._append_equity(idx, bar)
                continue

            if atr is not None and atr < self.strategy_cfg.get("min_atr", 0.0):
                self.last_gate_reason = "MIN_ATR"
                self._append_equity(idx, bar)
                continue

            prices = [b["close"] for b in bars[: idx + 1]]
            signal = self.strategy.generate_signal(prices, step=idx)
            if signal == 0:
                self.last_gate_reason = "NO_SIGNAL"
                self._append_equity(idx, bar)
                continue

            position_size = self.risk.calc_position_size(self.capital, price, atr)
            if position_size <= 0:
                self.last_gate_reason = "POSITION_SIZE_ZERO"
                self._append_equity(idx, bar)
                continue

            if hasattr(self.risk, "can_open_order") and not self.risk.can_open_order(position_size):
                self.last_gate_reason = "RISK_ORDER_LIMIT"
                self._append_equity(idx, bar)
                continue

            opened = self.execution.send_order(
                self.symbol,
                signal,
                price,
                position_size,
                atr=atr,
                risk=self.risk,
                bar_time=bar["datetime"],
            )
            if opened:
                self.last_gate_reason = None
                self.daily_trade_count += 1
                if hasattr(self.risk, "record_order"):
                    self.risk.record_order()
                metrics = self._runtime_metrics()
                runtime.update(
                    {
                        "event": "trade_open",
                        "mode": "sim_live",
                        "symbol": self.symbol,
                        "signal": signal,
                        "last_step": idx,
                        "last_bar_time": bar["datetime"],
                        "last_price": price,
                        "capital": self.capital,
                        "position": self.execution.position,
                        "trades": len(self.execution.trades),
                        "halt_reason": self.risk.halt_reason,
                        "total_pnl": metrics["total_pnl"],
                        "win_rate": metrics["win_rate"],
                        "runtime_drawdown": metrics["runtime_drawdown"],
                    }
                )

            self._append_equity(idx, bar)

        self.last_processed_idx = len(bars) - 1
        return processed

    def _compute_max_drawdown(self):
        peak = None
        max_dd = 0.0
        for row in self.equity_curve:
            eq = float(row.get("equity", row.get("cash", 0.0)))
            if peak is None or eq > peak:
                peak = eq
            dd = peak - eq
            row["drawdown"] = dd
            if dd > max_dd:
                max_dd = dd
        return max_dd

    def _compute_stats(self):
        total_trades = len(self.execution.trades)
        total_pnl = sum(t["pnl"] for t in self.execution.trades)
        win_trades = sum(1 for t in self.execution.trades if t["pnl"] > 0)
        win_rate = (win_trades / total_trades * 100.0) if total_trades else 0.0
        final_capital = self.initial_capital + total_pnl
        max_drawdown = self._compute_max_drawdown()
        return {
            "initial_capital": self.initial_capital,
            "final_capital": final_capital,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "total_pnl": total_pnl,
            "max_drawdown": max_drawdown,
        }

    def flush_outputs(self):
        os.makedirs(self.output_dir, exist_ok=True)

        with open(os.path.join(self.output_dir, "equity_curve.csv"), "w", newline="", encoding="utf-8") as f:
            fieldnames = ["step", "cash", "unrealized", "equity", "drawdown", "datetime"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for row in self.equity_curve:
                writer.writerow(row)

        with open(os.path.join(self.output_dir, "trades.csv"), "w", newline="", encoding="utf-8") as f:
            if self.execution.trades:
                fieldnames = list(self.execution.trades[0].keys())
            else:
                fieldnames = ["direction", "entry_price", "exit_price", "size", "pnl"]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for trade in self.execution.trades:
                writer.writerow(trade)

        perf = self._compute_stats()
        with open(os.path.join(self.output_dir, "performance.json"), "w", encoding="utf-8") as f:
            json.dump(perf, f, ensure_ascii=False, indent=2)

        trades_path = os.path.join(self.output_dir, "trades.csv")
        paper_errors = check_trades(trades_path)
        paper_report_path = os.path.join(self.output_dir, "paper_check_report.json")
        write_paper_check_report(paper_report_path, build_paper_check_report(trades_path, paper_errors))
        return perf, paper_errors


def _build_tune_cmd(symbol, tune_cfg):
    return [
        sys.executable,
        "walk_forward_tune.py",
        "--symbol",
        symbol,
        "--train-size",
        str(tune_cfg["train_size"]),
        "--test-size",
        str(tune_cfg["test_size"]),
        "--step-size",
        str(tune_cfg["step_size"]),
        "--fast-min",
        str(tune_cfg["fast_min"]),
        "--fast-max",
        str(tune_cfg["fast_max"]),
        "--slow-min",
        str(tune_cfg["slow_min"]),
        "--slow-max",
        str(tune_cfg["slow_max"]),
        "--slow-step",
        str(tune_cfg["slow_step"]),
        "--dd-penalty",
        str(tune_cfg["dd_penalty"]),
        "--min-positive-windows",
        str(tune_cfg["min_positive_windows"]),
    ]


def _run_tune(symbol, tune_cfg):
    cmd = _build_tune_cmd(symbol=symbol, tune_cfg=tune_cfg)
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")


def _snapshot_files(paths):
    snapshot = {}
    for path in paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                snapshot[path] = f.read()
        else:
            snapshot[path] = None
    return snapshot


def _restore_files(snapshot):
    for path, content in snapshot.items():
        if content is None:
            if os.path.exists(path):
                os.remove(path)
            continue
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def get_drawdown_alert_threshold(cfg):
    monitor_cfg = (cfg or {}).get("monitor", {})
    value = monitor_cfg.get("drawdown_alert_threshold")
    if value is None:
        return None
    try:
        threshold = float(value)
    except Exception:
        return None
    return threshold if threshold >= 0 else None


def _resolve_tune_cfg(cfg, args):
    auto_adjust = cfg.get("auto_adjust") or {}

    def pick(name, fallback):
        value = getattr(args, name)
        return fallback if value is None else value

    enabled = bool(args.auto_adjust or auto_adjust.get("enabled", False))
    return {
        "enabled": enabled,
        "adjust_every_cycles": max(1, int(pick("adjust_every_cycles", auto_adjust.get("adjust_every_cycles", 5)))),
        "train_size": max(60, int(pick("tune_train_size", auto_adjust.get("train_size", 480)))),
        "test_size": max(20, int(pick("tune_test_size", auto_adjust.get("test_size", 120)))),
        "step_size": max(20, int(pick("tune_step_size", auto_adjust.get("step_size", 120)))),
        "fast_min": max(2, int(pick("tune_fast_min", auto_adjust.get("fast_min", 3)))),
        "fast_max": max(3, int(pick("tune_fast_max", auto_adjust.get("fast_max", 10)))),
        "slow_min": max(4, int(pick("tune_slow_min", auto_adjust.get("slow_min", 10)))),
        "slow_max": max(6, int(pick("tune_slow_max", auto_adjust.get("slow_max", 60)))),
        "slow_step": max(1, int(pick("tune_slow_step", auto_adjust.get("slow_step", 2)))),
        "dd_penalty": float(pick("tune_dd_penalty", auto_adjust.get("dd_penalty", 0.5))),
        "min_positive_windows": max(
            1, int(pick("tune_min_positive_windows", auto_adjust.get("min_positive_windows", 1)))
        ),
        "rollback_on_worse": bool(auto_adjust.get("rollback_on_worse", True)),
        "min_improve": float(auto_adjust.get("min_improve", 0.0)),
    }


def _normalize_tune_cfg(tune_cfg):
    if tune_cfg["fast_max"] < tune_cfg["fast_min"]:
        tune_cfg["fast_max"] = tune_cfg["fast_min"]
    if tune_cfg["slow_max"] < tune_cfg["slow_min"]:
        tune_cfg["slow_max"] = tune_cfg["slow_min"]
    if tune_cfg["slow_min"] <= tune_cfg["fast_min"]:
        tune_cfg["slow_min"] = tune_cfg["fast_min"] + 1
    if tune_cfg["slow_max"] <= tune_cfg["fast_max"]:
        tune_cfg["slow_max"] = tune_cfg["fast_max"] + 1
    return tune_cfg


def _build_dq_report(bars, schedule=None):
    return DataEngine().validate_bars(bars, schedule=schedule)


def get_no_new_data_error_threshold(cfg):
    monitor_cfg = (cfg or {}).get("monitor", {})
    value = monitor_cfg.get("no_new_data_error_threshold", 3)
    try:
        threshold = int(value)
    except Exception:
        return 3
    return max(1, threshold)


def get_no_new_data_alert_level(streak, cfg):
    return "ERROR" if int(streak) >= get_no_new_data_error_threshold(cfg) else "WARN"


def main():
    parser = argparse.ArgumentParser(description="Quasi realtime simulation runner")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--source", default="akshare")
    parser.add_argument("--interval-sec", type=int, default=60)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means infinite loop")
    parser.add_argument("--output-dir", default="output")
    parser.add_argument("--data-out", default=None, help="default: data/<symbol>.csv")
    parser.add_argument("--ignore-market-hours", action="store_true", help="run even outside market sessions")
    parser.add_argument("--auto-adjust", action="store_true", help="enable automatic strategy tuning")
    parser.add_argument("--adjust-every-cycles", type=int, default=None)
    parser.add_argument("--tune-train-size", type=int, default=None)
    parser.add_argument("--tune-test-size", type=int, default=None)
    parser.add_argument("--tune-step-size", type=int, default=None)
    parser.add_argument("--tune-fast-min", type=int, default=None)
    parser.add_argument("--tune-fast-max", type=int, default=None)
    parser.add_argument("--tune-slow-min", type=int, default=None)
    parser.add_argument("--tune-slow-max", type=int, default=None)
    parser.add_argument("--tune-slow-step", type=int, default=None)
    parser.add_argument("--tune-dd-penalty", type=float, default=None)
    parser.add_argument("--tune-min-positive-windows", type=int, default=None)
    args = parser.parse_args()

    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="paper")
    report_validation(errors, warnings)

    symbol = args.symbol or cfg.get("symbol", "M2609")
    data_out = args.data_out or f"data/{symbol}.csv"
    interval_sec = max(5, int(args.interval_sec))
    runtime = RuntimeState("state/runtime_state.json")
    alert = AlertManager(
        cfg.get("monitor", {}).get("alert_file", "logs/alerts.log"),
        cfg.get("monitor", {}).get("webhook_url", ""),
    )
    tune_cfg = _normalize_tune_cfg(_resolve_tune_cfg(cfg, args))
    schedule = load_market_schedule(cfg)
    use_market_hours = not args.ignore_market_hours
    last_bar_time_seen = _read_latest_bar_time(data_out)
    no_new_data_streak = 0
    drawdown_alert_active = False

    print(
        f"[SIM_LIVE] start symbol={symbol} source={args.source} interval={interval_sec}s "
        f"max_cycles={args.max_cycles if args.max_cycles else 'infinite'} auto_adjust={tune_cfg['enabled']} "
        f"use_market_hours={use_market_hours}"
    )

    cycle = 0
    session = None
    while True:
        if use_market_hours:
            while True:
                now = datetime.now()
                if is_market_open(now, schedule):
                    break
                nxt = next_market_open(now, schedule)
                wait_sec = 30
                next_text = ""
                if nxt is not None:
                    wait_sec = max(5, min(300, int((nxt - now).total_seconds())))
                    next_text = nxt.strftime("%Y-%m-%d %H:%M:%S")
                runtime.update(
                    {
                        "event": "sim_live_wait_market",
                        "mode": "sim_live",
                        "symbol": symbol,
                        "next_open": next_text,
                        "sleep_sec": wait_sec,
                    }
                )
                print(f"[SIM_LIVE] market closed, next_open={next_text or '-'} sleep={wait_sec}s")
                time.sleep(wait_sec)

        cycle += 1
        runtime.update(
            {
                "event": "sim_live_cycle_start",
                "mode": "sim_live",
                "cycle": cycle,
                "symbol": symbol,
                "source": args.source,
                "auto_adjust": tune_cfg["enabled"],
            }
        )

        fetch_ret = _run_fetch(symbol=symbol, out_path=data_out, source=args.source)
        if fetch_ret.returncode != 0:
            message = (fetch_ret.stderr or fetch_ret.stdout or "").strip()
            runtime.update(
                {
                    "event": "sim_live_fetch_failed",
                    "mode": "sim_live",
                    "cycle": cycle,
                    "symbol": symbol,
                    "error": message,
                }
            )
            alert.send_event(
                event="sim_live_fetch_failed",
                level="ERROR",
                message=f"cycle={cycle} symbol={symbol} source={args.source}",
                data={"error": message},
            )
            print(f"[SIM_LIVE] cycle={cycle} fetch failed: {message}")
        else:
            fetch_text = (fetch_ret.stdout or "").strip()
            if fetch_text:
                print(fetch_text)
            newest_bar_time = _read_latest_bar_time(data_out)
            no_data_marked = False
            if newest_bar_time and newest_bar_time == last_bar_time_seen:
                no_new_data_streak += 1
                level = get_no_new_data_alert_level(no_new_data_streak, cfg)
                runtime.update(
                    {
                        "event": "sim_live_no_new_data",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "last_bar_time": newest_bar_time,
                        "no_new_data_streak": no_new_data_streak,
                        "alert_level": level,
                    }
                )
                alert.send_event(
                    event="sim_live_no_new_data",
                    level=level,
                    message=f"cycle={cycle} symbol={symbol}",
                    data={"last_bar_time": newest_bar_time, "streak": no_new_data_streak},
                )
                no_data_marked = True
            elif newest_bar_time and newest_bar_time != last_bar_time_seen:
                no_new_data_streak = 0
            if newest_bar_time:
                last_bar_time_seen = newest_bar_time

            bars_for_quality = _read_bars(data_out)
            dq_report = _build_dq_report(bars_for_quality, schedule=schedule)
            ok_dq, dq_errors, dq_warnings = evaluate_data_quality(dq_report, cfg.get("data_quality", {}))
            for w in dq_warnings:
                print(f"[SIM_LIVE][WARN] {w}")
            if dq_warnings:
                runtime.update(
                    {
                        "event": "sim_live_data_quality_warn",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "warning_count": len(dq_warnings),
                    }
                )
                alert.send_event(
                    event="sim_live_data_quality_warn",
                    level="WARN",
                    message=f"cycle={cycle} symbol={symbol}",
                    data={"warnings": dq_warnings[:5], "report": dq_report},
                )
            if not ok_dq:
                runtime.update(
                    {
                        "event": "sim_live_data_quality_block",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "errors": dq_errors,
                    }
                )
                alert.send_event(
                    event="sim_live_data_quality_block",
                    level="ERROR",
                    message=f"cycle={cycle} symbol={symbol}",
                    data={"errors": dq_errors},
                )
                print(f"[SIM_LIVE] cycle={cycle} data quality blocked: {dq_errors}")
                if args.max_cycles > 0 and cycle >= args.max_cycles:
                    runtime.update(
                        {
                            "event": "sim_live_finished",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                        }
                    )
                    break
                runtime.update(
                    {
                        "event": "sim_live_sleeping",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "sleep_sec": interval_sec,
                    }
                )
                time.sleep(interval_sec)
                continue

            if not tune_cfg["enabled"]:
                if session is None:
                    session = ContinuousPaperSession(cfg=cfg, symbol=symbol, output_dir=args.output_dir)

                bars = bars_for_quality
                start_idx = session.last_processed_idx + 1
                if start_idx >= len(bars):
                    if not no_data_marked:
                        no_new_data_streak += 1
                    level = get_no_new_data_alert_level(no_new_data_streak, cfg)
                    runtime.update(
                        {
                            "event": "sim_live_no_new_data",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "capital": session.capital,
                            "position": session.execution.position,
                            "trades": len(session.execution.trades),
                            "halt_reason": session.risk.halt_reason,
                            "no_new_data_streak": no_new_data_streak,
                            "alert_level": level,
                        }
                    )
                    if not no_data_marked:
                        alert.send_event(
                            event="sim_live_no_new_data",
                            level=level,
                            message=f"cycle={cycle} symbol={symbol}",
                            data={"streak": no_new_data_streak, "reason": "no_new_bars_after_merge"},
                        )
                    print(f"[SIM_LIVE] cycle={cycle} no new bars")
                else:
                    no_new_data_streak = 0
                    processed = session.process_bars(bars=bars, start_idx=start_idx, runtime=runtime)
                    perf, paper_errors = session.flush_outputs()
                    max_dd = _to_float(perf.get("max_drawdown"))
                    threshold = get_drawdown_alert_threshold(cfg)
                    if threshold is not None and max_dd is not None:
                        if max_dd >= threshold and not drawdown_alert_active:
                            drawdown_alert_active = True
                            runtime.update(
                                {
                                    "event": "sim_live_drawdown_threshold_reached",
                                    "mode": "sim_live",
                                    "cycle": cycle,
                                    "symbol": symbol,
                                    "max_drawdown": max_dd,
                                    "threshold": threshold,
                                }
                            )
                            alert.send_event(
                                event="sim_live_drawdown_threshold_reached",
                                level="WARN",
                                message=f"cycle={cycle} symbol={symbol}",
                                data={"max_drawdown": max_dd, "threshold": threshold},
                            )
                        elif max_dd < threshold:
                            drawdown_alert_active = False
                    strategy_name = session.strategy_cfg.get("name", "ma")
                    runtime.update(
                        {
                            "event": "sim_live_cycle_done",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "bars_processed": processed,
                            "capital": session.capital,
                            "position": session.execution.position,
                            "trades": len(session.execution.trades),
                            "halt_reason": session.risk.halt_reason,
                            "gate_reason": session.last_gate_reason,
                            "total_pnl": perf.get("total_pnl"),
                            "win_rate": perf.get("win_rate"),
                            "total_trades": perf.get("total_trades"),
                            "strategy_params": {
                                "name": strategy_name,
                                "fast": getattr(session.strategy, "fast", None),
                                "slow": getattr(session.strategy, "slow", None),
                                "mode": getattr(session.strategy, "mode", None),
                                "min_diff": getattr(session.strategy, "min_diff", None),
                            },
                        }
                    )
                    if paper_errors:
                        runtime.update(
                            {
                                "event": "sim_live_paper_check_failed",
                                "mode": "sim_live",
                                "cycle": cycle,
                                "symbol": symbol,
                                "paper_error_count": len(paper_errors),
                            }
                        )
                        alert.send_event(
                            event="sim_live_paper_check_failed",
                            level="ERROR",
                            message=f"cycle={cycle} symbol={symbol}",
                            data={"error_count": len(paper_errors), "errors": paper_errors[:5]},
                        )
                    print(
                        f"[SIM_LIVE] cycle={cycle} incremental done bars={processed} "
                        f"pnl={perf.get('total_pnl')} trades={perf.get('total_trades')} "
                        f"position={'HOLD' if session.execution.position else 'FLAT'}"
                    )
                if args.max_cycles > 0 and cycle >= args.max_cycles:
                    runtime.update(
                        {
                            "event": "sim_live_finished",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                        }
                    )
                    print(f"[SIM_LIVE] finished cycles={cycle}")
                    break
                runtime.update(
                    {
                        "event": "sim_live_sleeping",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "sleep_sec": interval_sec,
                        "capital": session.capital,
                        "position": session.execution.position,
                        "trades": len(session.execution.trades),
                        "halt_reason": session.risk.halt_reason,
                    }
                )
                time.sleep(interval_sec)
                continue

            snapshot = None
            tune_changed = False
            baseline_pnl = None
            tune_cycle = tune_cfg["enabled"] and cycle % tune_cfg["adjust_every_cycles"] == 0

            if tune_cycle and tune_cfg["rollback_on_worse"]:
                try:
                    backtest_main(symbol_override=symbol, output_dir=args.output_dir)
                    baseline_perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                    baseline_pnl = _to_float(baseline_perf.get("total_pnl"))
                    runtime.update(
                        {
                            "event": "sim_live_baseline_done",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "baseline_pnl": baseline_pnl,
                        }
                    )
                    print(f"[SIM_LIVE] cycle={cycle} baseline pnl={baseline_pnl}")
                except Exception as exc:
                    runtime.update(
                        {
                            "event": "sim_live_baseline_failed",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "error": str(exc),
                        }
                    )
                    alert.send_event(
                        event="sim_live_baseline_failed",
                        level="ERROR",
                        message=f"cycle={cycle} symbol={symbol}",
                        data={"error": str(exc)},
                    )
                    print(f"[SIM_LIVE] cycle={cycle} baseline failed: {exc}")

            if tune_cycle:
                snapshot = _snapshot_files(["config.json", "state/strategy_state.json"])
                old_cfg = load_config()
                old_strategy = old_cfg.get("strategy", {})
                runtime.update(
                    {
                        "event": "sim_live_tune_start",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "old_fast": old_strategy.get("fast"),
                        "old_slow": old_strategy.get("slow"),
                    }
                )
                tune_ret = _run_tune(symbol=symbol, tune_cfg=tune_cfg)
                if tune_ret.returncode != 0:
                    tune_error = (tune_ret.stderr or tune_ret.stdout or "").strip()
                    runtime.update(
                        {
                            "event": "sim_live_tune_failed",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "error": tune_error,
                        }
                    )
                    alert.send_event(
                        event="sim_live_tune_failed",
                        level="ERROR",
                        message=f"cycle={cycle} symbol={symbol}",
                        data={"error": tune_error},
                    )
                    print(f"[SIM_LIVE] cycle={cycle} tune failed: {tune_error}")
                else:
                    tune_log = (tune_ret.stdout or "").strip()
                    new_cfg = load_config()
                    new_strategy = new_cfg.get("strategy", {})
                    tune_changed = (
                        old_strategy.get("fast") != new_strategy.get("fast")
                        or old_strategy.get("slow") != new_strategy.get("slow")
                    )
                    runtime.update(
                        {
                            "event": "sim_live_tune_done",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "changed": tune_changed,
                            "new_fast": new_strategy.get("fast"),
                            "new_slow": new_strategy.get("slow"),
                        }
                    )
                    if tune_log:
                        print(tune_log)
                    print(
                        f"[SIM_LIVE] cycle={cycle} tune done changed={tune_changed} "
                        f"fast={new_strategy.get('fast')} slow={new_strategy.get('slow')}"
                    )

            try:
                backtest_main(symbol_override=symbol, output_dir=args.output_dir)
            except Exception as exc:
                runtime.update(
                    {
                        "event": "sim_live_backtest_failed",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "error": str(exc),
                    }
                )
                alert.send_event(
                    event="sim_live_backtest_failed",
                    level="ERROR",
                    message=f"cycle={cycle} symbol={symbol}",
                    data={"error": str(exc)},
                )
                print(f"[SIM_LIVE] cycle={cycle} backtest failed: {exc}")
            else:
                perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                current_pnl = _to_float(perf.get("total_pnl"))

                if (
                    tune_changed
                    and tune_cfg["rollback_on_worse"]
                    and snapshot is not None
                    and baseline_pnl is not None
                    and current_pnl is not None
                    and current_pnl < (baseline_pnl + tune_cfg["min_improve"])
                ):
                    _restore_files(snapshot)
                    runtime.update(
                        {
                            "event": "sim_live_tune_rollback",
                            "mode": "sim_live",
                            "cycle": cycle,
                            "symbol": symbol,
                            "baseline_pnl": baseline_pnl,
                            "new_pnl": current_pnl,
                        }
                    )
                    alert.send_event(
                        event="sim_live_tune_rollback",
                        level="WARN",
                        message=f"cycle={cycle} symbol={symbol}",
                        data={"baseline_pnl": baseline_pnl, "new_pnl": current_pnl},
                    )
                    print(
                        f"[SIM_LIVE] cycle={cycle} rollback tune: baseline_pnl={baseline_pnl} "
                        f"new_pnl={current_pnl}"
                    )
                    backtest_main(symbol_override=symbol, output_dir=args.output_dir)
                    perf = _read_perf(os.path.join(args.output_dir, "performance.json"))
                    current_pnl = _to_float(perf.get("total_pnl"))

                runtime.update(
                    {
                        "event": "sim_live_cycle_done",
                        "mode": "sim_live",
                        "cycle": cycle,
                        "symbol": symbol,
                        "total_pnl": perf.get("total_pnl"),
                        "win_rate": perf.get("win_rate"),
                        "total_trades": perf.get("total_trades"),
                    }
                )
                max_dd = _to_float(perf.get("max_drawdown"))
                threshold = get_drawdown_alert_threshold(cfg)
                if threshold is not None and max_dd is not None:
                    if max_dd >= threshold and not drawdown_alert_active:
                        drawdown_alert_active = True
                        runtime.update(
                            {
                                "event": "sim_live_drawdown_threshold_reached",
                                "mode": "sim_live",
                                "cycle": cycle,
                                "symbol": symbol,
                                "max_drawdown": max_dd,
                                "threshold": threshold,
                            }
                        )
                        alert.send_event(
                            event="sim_live_drawdown_threshold_reached",
                            level="WARN",
                            message=f"cycle={cycle} symbol={symbol}",
                            data={"max_drawdown": max_dd, "threshold": threshold},
                        )
                    elif max_dd < threshold:
                        drawdown_alert_active = False
                print(
                    f"[SIM_LIVE] cycle={cycle} done pnl={current_pnl} "
                    f"trades={perf.get('total_trades')}"
                )

        if args.max_cycles > 0 and cycle >= args.max_cycles:
            runtime.update(
                {
                    "event": "sim_live_finished",
                    "mode": "sim_live",
                    "cycle": cycle,
                    "symbol": symbol,
                }
            )
            print(f"[SIM_LIVE] finished cycles={cycle}")
            break

        runtime.update(
            {
                "event": "sim_live_sleeping",
                "mode": "sim_live",
                "cycle": cycle,
                "symbol": symbol,
                "sleep_sec": interval_sec,
            }
        )
        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
