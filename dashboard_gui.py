import json
import os
import threading
import tkinter as tk
from tkinter import ttk

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
    def __init__(self, root):
        self.root = root
        self.root.title("Quant Realtime Monitor")
        self.root.geometry("1100x700")

        self.runtime_path = os.path.join("state", "runtime_state.json")
        self.perf_path = os.path.join("output", "performance.json")
        self.worker = None
        self.worker_error = None
        self.last_runtime_ts = ""
        self.last_trade_key = ""

        cfg = _read_json("config.json")
        default_symbol = cfg.get("symbol", "M2609")

        self.var_symbol = tk.StringVar(value=default_symbol)
        self.var_status = tk.StringVar(value="idle")
        self.var_time = tk.StringVar(value="-")
        self.var_step = tk.StringVar(value="-")
        self.var_price = tk.StringVar(value="-")
        self.var_capital = tk.StringVar(value="-")
        self.var_position = tk.StringVar(value="-")
        self.var_trades = tk.StringVar(value="0")
        self.var_pnl = tk.StringVar(value="-")
        self.var_win_rate = tk.StringVar(value="-")
        self.var_drawdown = tk.StringVar(value="-")

        self._build_layout()
        self._poll()

    def _build_layout(self):
        top = ttk.Frame(self.root, padding=10)
        top.pack(fill=tk.X)

        ttk.Label(top, text="Symbol").pack(side=tk.LEFT)
        ttk.Entry(top, width=12, textvariable=self.var_symbol).pack(side=tk.LEFT, padx=(8, 12))

        self.btn_run = ttk.Button(top, text="Run", command=self._start_run)
        self.btn_run.pack(side=tk.LEFT)

        ttk.Label(top, textvariable=self.var_status, foreground="#0a4").pack(side=tk.LEFT, padx=(14, 0))

        stats = ttk.Frame(self.root, padding=10)
        stats.pack(fill=tk.X)

        self._stat_cell(stats, "Bar Time", self.var_time, 0, 0)
        self._stat_cell(stats, "Step", self.var_step, 0, 1)
        self._stat_cell(stats, "Price", self.var_price, 0, 2)
        self._stat_cell(stats, "Capital", self.var_capital, 0, 3)
        self._stat_cell(stats, "Position", self.var_position, 1, 0)
        self._stat_cell(stats, "Trades", self.var_trades, 1, 1)
        self._stat_cell(stats, "PnL", self.var_pnl, 1, 2)
        self._stat_cell(stats, "WinRate", self.var_win_rate, 1, 3)
        self._stat_cell(stats, "MaxDD", self.var_drawdown, 1, 4)

        mid = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        mid.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        left = ttk.Frame(mid)
        right = ttk.Frame(mid)
        mid.add(left, weight=3)
        mid.add(right, weight=2)

        ttk.Label(left, text="Latest Trades").pack(anchor=tk.W)
        columns = ("exit_time", "direction", "entry_price", "exit_price", "size", "pnl")
        self.trade_table = ttk.Treeview(left, columns=columns, show="headings", height=18)
        for col in columns:
            self.trade_table.heading(col, text=col)
            width = 120 if col == "exit_time" else 90
            self.trade_table.column(col, width=width, anchor=tk.CENTER)
        self.trade_table.pack(fill=tk.BOTH, expand=True)

        ttk.Label(right, text="Runtime Log").pack(anchor=tk.W)
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

    def _start_run(self):
        if self.worker and self.worker.is_alive():
            return
        symbol = self.var_symbol.get().strip() or "M2609"
        self.var_status.set("running")
        self.worker_error = None
        self.btn_run.configure(state=tk.DISABLED)
        self._append_log(f"run start symbol={symbol}")

        def _worker():
            try:
                run_backtest_main(symbol_override=symbol, output_dir="output")
            except Exception as exc:
                self.worker_error = str(exc)

        self.worker = threading.Thread(target=_worker, daemon=True)
        self.worker.start()

    def _update_from_runtime(self, runtime):
        self.var_time.set(runtime.get("last_bar_time", "-"))
        self.var_step.set(str(runtime.get("last_step", "-")))
        self.var_price.set(_format_num(runtime.get("last_price")))
        self.var_capital.set(_format_num(runtime.get("capital")))
        self.var_position.set("OPEN" if runtime.get("position") else "FLAT")
        self.var_trades.set(str(runtime.get("trades", 0)))

        ts = runtime.get("updated_at", "")
        if ts and ts != self.last_runtime_ts:
            self.last_runtime_ts = ts
            event = runtime.get("event", "tick")
            self._append_log(
                f"{ts} event={event} step={runtime.get('last_step', '-')} "
                f"price={_format_num(runtime.get('last_price'))} cap={_format_num(runtime.get('capital'))}"
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
                        trade.get("direction", "-"),
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

    def _poll(self):
        runtime = _read_json(self.runtime_path)
        if runtime:
            self._update_from_runtime(runtime)
        self._update_from_performance()

        if self.worker and not self.worker.is_alive() and self.btn_run["state"] == tk.DISABLED:
            self.btn_run.configure(state=tk.NORMAL)
            if self.worker_error:
                self.var_status.set("failed")
                self._append_log(f"run failed: {self.worker_error}")
            else:
                self.var_status.set("finished")
                self._append_log("run finished")

        self.root.after(400, self._poll)


def main():
    root = tk.Tk()
    MonitorUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
