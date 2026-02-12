import json
import os
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk

from engine.data_policy import assert_source_allowed, get_data_policy
from main import main as run_backtest_main


def _read_json(path):
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _format_num(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


class MonitorUI:
    def __init__(self, root, default_symbol=None, auto_start=False):
        self.root = root
        self.root.title("量化实时监控")
        self.root.geometry("1180x760")

        self.runtime_path = os.path.join("state", "runtime_state.json")
        self.perf_path = os.path.join("output", "performance.json")
        self.config_path = "config.json"
        self.worker = None
        self.fetch_worker = None
        self.portfolio_worker = None
        self.worker_error = None
        self.fetch_error = None
        self.portfolio_error = None
        self.last_runtime_ts = ""
        self.last_trade_key = ""

        self.cfg = _read_json(self.config_path)
        if not default_symbol:
            default_symbol = self.cfg.get("symbol", "M2609")

        self.var_symbol = tk.StringVar(value=default_symbol)
        self.var_source = tk.StringVar(value="akshare")
        self.var_days = tk.StringVar(value="20")
        self.var_status = tk.StringVar(value="空闲")
        self.var_policy = tk.StringVar(value="-")
        self.var_time = tk.StringVar(value="-")
        self.var_step = tk.StringVar(value="-")
        self.var_price = tk.StringVar(value="-")
        self.var_capital = tk.StringVar(value="-")
        self.var_position = tk.StringVar(value="-")
        self.var_trades = tk.StringVar(value="0")
        self.var_pnl = tk.StringVar(value="-")
        self.var_win_rate = tk.StringVar(value="-")
        self.var_drawdown = tk.StringVar(value="-")
        self.var_portfolio_pnl = tk.StringVar(value="-")
        self.var_portfolio_dd = tk.StringVar(value="-")
        self.var_portfolio_symbols = tk.StringVar(value="-")
        self.var_portfolio_method = tk.StringVar(value="-")
        self.var_portfolio_rebalance = tk.StringVar(value="-")

        self._build_layout()
        self._update_policy_text()
        self._poll()
        if auto_start:
            self._start_run()

    def _build_layout(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="合约").pack(side=tk.LEFT)
        ttk.Entry(top, width=10, textvariable=self.var_symbol).pack(side=tk.LEFT, padx=(6, 10))

        ttk.Label(top, text="数据源").pack(side=tk.LEFT)
        source_box = ttk.Combobox(
            top,
            width=14,
            state="readonly",
            textvariable=self.var_source,
            values=["akshare", "licensed_vendor", "tdx_local", "ctp"],
        )
        source_box.pack(side=tk.LEFT, padx=(6, 10))

        ttk.Label(top, text="天数").pack(side=tk.LEFT)
        ttk.Entry(top, width=6, textvariable=self.var_days).pack(side=tk.LEFT, padx=(6, 10))

        self.btn_fetch = ttk.Button(top, text="抓取数据", command=self._start_fetch)
        self.btn_fetch.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_run = ttk.Button(top, text="运行回测", command=self._start_run)
        self.btn_run.pack(side=tk.LEFT, padx=(0, 10))

        self.btn_portfolio = ttk.Button(top, text="运行组合", command=self._start_portfolio_run)
        self.btn_portfolio.pack(side=tk.LEFT, padx=(0, 10))

        ttk.Label(top, text="模式").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.var_policy).pack(side=tk.LEFT, padx=(6, 16))

        ttk.Label(top, text="状态").pack(side=tk.LEFT)
        ttk.Label(top, textvariable=self.var_status, foreground="#0a4").pack(side=tk.LEFT, padx=(6, 0))

        stats = ttk.Frame(self.root, padding=10)
        stats.pack(fill=tk.X)
        self._stat_cell(stats, "K线时间", self.var_time, 0, 0)
        self._stat_cell(stats, "步骤", self.var_step, 0, 1)
        self._stat_cell(stats, "价格", self.var_price, 0, 2)
        self._stat_cell(stats, "资金", self.var_capital, 0, 3)
        self._stat_cell(stats, "持仓", self.var_position, 1, 0)
        self._stat_cell(stats, "交易数", self.var_trades, 1, 1)
        self._stat_cell(stats, "总盈亏", self.var_pnl, 1, 2)
        self._stat_cell(stats, "胜率", self.var_win_rate, 1, 3)
        self._stat_cell(stats, "最大回撤", self.var_drawdown, 1, 4)
        self._stat_cell(stats, "组合盈亏", self.var_portfolio_pnl, 2, 0)
        self._stat_cell(stats, "组合回撤", self.var_portfolio_dd, 2, 1)
        self._stat_cell(stats, "组合品种", self.var_portfolio_symbols, 2, 2)
        self._stat_cell(stats, "权重方式", self.var_portfolio_method, 2, 3)
        self._stat_cell(stats, "再平衡次数", self.var_portfolio_rebalance, 2, 4)

        mid = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(mid)
        right = ttk.Frame(mid)
        mid.add(left, weight=3)
        mid.add(right, weight=2)

        ttk.Label(left, text="最近成交").pack(anchor=tk.W)
        columns = ("平仓时间", "方向", "开仓价", "平仓价", "手数", "盈亏")
        self.trade_table = ttk.Treeview(left, columns=columns, show="headings", height=18)
        for col in columns:
            self.trade_table.heading(col, text=col)
            width = 120 if col == "平仓时间" else 90
            self.trade_table.column(col, width=width, anchor=tk.CENTER)
        self.trade_table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="运行日志").pack(anchor=tk.W)
        self.log_box = tk.Text(right, height=20, state=tk.DISABLED)
        self.log_box.pack(fill=tk.BOTH, expand=True)

    def _stat_cell(self, parent, title, var, row, col):
        frm = ttk.Frame(parent, padding=(4, 6))
        frm.grid(row=row, column=col, sticky="w")
        ttk.Label(frm, text=f"{title}: ").pack(side=tk.LEFT)
        ttk.Label(frm, textvariable=var).pack(side=tk.LEFT)

    def _append_log(self, text):
        self.log_box.configure(state=tk.NORMAL)
        self.log_box.insert(tk.END, text + "\n")
        self.log_box.see(tk.END)
        self.log_box.configure(state=tk.DISABLED)

    def _event_text(self, event):
        mapping = {
            "new_day": "新交易日",
            "trade_open": "开仓",
            "trade_close": "平仓",
            "force_close": "强平",
            "finished": "结束",
            "tick": "行情",
        }
        return mapping.get(event, str(event))

    def _position_text(self, position):
        return "持仓中" if position else "空仓"

    def _direction_text(self, direction):
        if direction == "LONG":
            return "多"
        if direction == "SHORT":
            return "空"
        return str(direction) if direction is not None else "-"

    def _update_policy_text(self):
        policy = get_data_policy(self.cfg)
        mode = policy.get("mode", "research")
        approved = ",".join(policy.get("approved_sources", [])) or "-"
        mode_text = "研究模式" if mode == "research" else "商用模式"
        self.var_policy.set(f"{mode_text} | 白名单: {approved}")

    def _is_source_allowed(self, source):
        try:
            assert_source_allowed(self.cfg, source)
            return True, ""
        except SystemExit as exc:
            return False, str(exc)

    def _start_fetch(self):
        if self.fetch_worker and self.fetch_worker.is_alive():
            return

        symbol = self.var_symbol.get().strip() or "M2609"
        source = self.var_source.get().strip() or "akshare"
        days_text = self.var_days.get().strip() or "20"
        if not days_text.isdigit():
            self.var_status.set("参数错误")
            self._append_log("抓取失败：天数必须是整数")
            return
        days = int(days_text)

        ok, reason = self._is_source_allowed(source)
        if not ok:
            self.var_status.set("已拦截")
            self._append_log(f"抓取被阻断：{reason}")
            return

        self.fetch_error = None
        self.var_status.set("抓取中")
        self.btn_fetch.configure(state=tk.DISABLED)
        self._append_log(f"开始抓取：symbol={symbol} source={source} days={days}")

        def _fetch_worker():
            try:
                cmd = [
                    sys.executable,
                    "data_update.py",
                    "--symbol",
                    symbol,
                    "--days",
                    str(days),
                    "--out",
                    f"data/{symbol}.csv",
                    "--source",
                    source,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                if result.returncode != 0:
                    self.fetch_error = (result.stderr or result.stdout or "").strip()
                else:
                    out_text = (result.stdout or "").strip()
                    if out_text:
                        self._append_log(out_text)
            except Exception as exc:
                self.fetch_error = str(exc)

        self.fetch_worker = threading.Thread(target=_fetch_worker, daemon=True)
        self.fetch_worker.start()

    def _start_run(self):
        if self.worker and self.worker.is_alive():
            return
        symbol = self.var_symbol.get().strip() or "M2609"
        self.var_status.set("运行中")
        self.worker_error = None
        self.btn_run.configure(state=tk.DISABLED)
        self._append_log(f"开始回测：symbol={symbol}")

        def _worker():
            try:
                run_backtest_main(symbol_override=symbol, output_dir="output")
            except Exception as exc:
                self.worker_error = str(exc)

        self.worker = threading.Thread(target=_worker, daemon=True)
        self.worker.start()

    def _start_portfolio_run(self):
        if self.portfolio_worker and self.portfolio_worker.is_alive():
            return
        self.var_status.set("组合运行中")
        self.portfolio_error = None
        self.btn_portfolio.configure(state=tk.DISABLED)
        self._append_log("开始组合回测")

        def _worker():
            try:
                cmd = [sys.executable, "portfolio_runner.py"]
                result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
                if result.returncode != 0:
                    self.portfolio_error = (result.stderr or result.stdout or "").strip()
                else:
                    out_text = (result.stdout or "").strip()
                    if out_text:
                        self._append_log(out_text)
            except Exception as exc:
                self.portfolio_error = str(exc)

        self.portfolio_worker = threading.Thread(target=_worker, daemon=True)
        self.portfolio_worker.start()

    def _update_from_runtime(self, runtime):
        self.var_time.set(runtime.get("last_bar_time", "-"))
        self.var_step.set(str(runtime.get("last_step", "-")))
        self.var_price.set(_format_num(runtime.get("last_price")))
        self.var_capital.set(_format_num(runtime.get("capital")))
        self.var_position.set(self._position_text(runtime.get("position")))
        self.var_trades.set(str(runtime.get("trades", 0)))

        ts = runtime.get("updated_at", "")
        if ts and ts != self.last_runtime_ts:
            self.last_runtime_ts = ts
            event = self._event_text(runtime.get("event", "tick"))
            self._append_log(
                f"{ts} 事件={event} 步骤={runtime.get('last_step', '-')} "
                f"价格={_format_num(runtime.get('last_price'))} 资金={_format_num(runtime.get('capital'))}"
            )

        trade = runtime.get("last_trade")
        if isinstance(trade, dict):
            key = f"{trade.get('exit_time','')}_{trade.get('pnl','')}_{trade.get('direction','')}"
            if key and key != self.last_trade_key:
                self.last_trade_key = key
                self.trade_table.insert(
                    "",
                    0,
                    values=(
                        trade.get("exit_time", "-"),
                        self._direction_text(trade.get("direction", "-")),
                        _format_num(trade.get("entry_price")),
                        _format_num(trade.get("exit_price")),
                        trade.get("size", "-"),
                        _format_num(trade.get("pnl")),
                    ),
                )
                if len(self.trade_table.get_children()) > 50:
                    children = self.trade_table.get_children()
                    self.trade_table.delete(children[-1])

    def _update_from_performance(self):
        perf = _read_json(self.perf_path)
        if not perf:
            return
        self.var_pnl.set(_format_num(perf.get("total_pnl")))
        self.var_win_rate.set(f"{float(perf.get('win_rate', 0.0)):.2f}%")
        self.var_drawdown.set(_format_num(perf.get("max_drawdown")))

    def _update_from_portfolio(self):
        portfolio_cfg = self.cfg.get("portfolio", {})
        portfolio_dir = portfolio_cfg.get("output_dir", os.path.join("output", "portfolio"))
        summary_path = os.path.join(portfolio_dir, "portfolio_summary.json")
        summary = _read_json(summary_path)
        if not summary:
            return
        self.var_portfolio_pnl.set(_format_num(summary.get("total_pnl")))
        self.var_portfolio_dd.set(_format_num(summary.get("max_drawdown")))
        self.var_portfolio_symbols.set(str(len(summary.get("selected_symbols", []))))
        self.var_portfolio_method.set(str(summary.get("weight_method", "-")))
        self.var_portfolio_rebalance.set(str(summary.get("rebalance_events", 0)))

    def _poll(self):
        runtime = _read_json(self.runtime_path)
        if runtime:
            self._update_from_runtime(runtime)
        self._update_from_performance()
        self._update_from_portfolio()

        if self.fetch_worker and not self.fetch_worker.is_alive() and self.btn_fetch["state"] == tk.DISABLED:
            self.btn_fetch.configure(state=tk.NORMAL)
            if self.fetch_error:
                self.var_status.set("抓取失败")
                self._append_log(f"抓取失败：{self.fetch_error}")
            else:
                self.var_status.set("抓取完成")
                self._append_log("抓取完成")

        if self.worker and not self.worker.is_alive() and self.btn_run["state"] == tk.DISABLED:
            self.btn_run.configure(state=tk.NORMAL)
            if self.worker_error:
                self.var_status.set("运行失败")
                self._append_log(f"回测失败：{self.worker_error}")
            else:
                self.var_status.set("运行完成")
                self._append_log("回测完成")

        if self.portfolio_worker and not self.portfolio_worker.is_alive() and self.btn_portfolio["state"] == tk.DISABLED:
            self.btn_portfolio.configure(state=tk.NORMAL)
            if self.portfolio_error:
                self.var_status.set("组合失败")
                self._append_log(f"组合回测失败：{self.portfolio_error}")
            else:
                self.var_status.set("组合完成")
                self._append_log("组合回测完成")

        self.root.after(400, self._poll)


def main(default_symbol=None, auto_start=False):
    root = tk.Tk()
    MonitorUI(root, default_symbol=default_symbol, auto_start=auto_start)
    root.mainloop()


if __name__ == "__main__":
    main()
