import random


class SimExecution:
    def __init__(self, slippage=1):
        self.slippage = slippage
        self.position = None
        self.trades = []

    def send_order(self, symbol, signal, price, size, atr=None, risk=None, contract_multiplier=1):
        if self.position is not None:
            return False
        direction = "LONG" if signal > 0 else "SHORT"
        fill_price = price + self.slippage if direction == "LONG" else price - self.slippage
        stop_price = risk.get_stop_price(fill_price, direction, atr) if risk else None
        take_profit = risk.get_take_profit_price(fill_price, direction, atr) if risk else None
        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": fill_price,
            "size": size,
            "stop_price": stop_price,
            "take_profit": take_profit,
            "entry_time": None,
        }
        return True

    def check_exit(self, price, risk=None):
        if self.position is None:
            return False, 0.0
        direction = self.position["direction"]
        entry = self.position["entry_price"]
        size = self.position["size"]
        stop_price = self.position.get("stop_price")
        take_profit = self.position.get("take_profit")

        exit_flag = False
        exit_price = price
        if direction == "LONG":
            if stop_price is not None and price <= stop_price:
                exit_flag = True
                exit_price = stop_price
            if take_profit is not None and price >= take_profit:
                exit_flag = True
                exit_price = take_profit
        else:
            if stop_price is not None and price >= stop_price:
                exit_flag = True
                exit_price = stop_price
            if take_profit is not None and price <= take_profit:
                exit_flag = True
                exit_price = take_profit

        if not exit_flag:
            return False, 0.0

        pnl = (exit_price - entry) * size if direction == "LONG" else (entry - exit_price) * size
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "size": size,
            "pnl": pnl,
        }
        self.trades.append(trade)
        self.position = None
        return True, pnl

    def force_close(self, price):
        if self.position is None:
            return 0.0
        direction = self.position["direction"]
        entry = self.position["entry_price"]
        size = self.position["size"]
        pnl = (price - entry) * size if direction == "LONG" else (entry - price) * size
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": price,
            "size": size,
            "pnl": pnl,
        }
        self.trades.append(trade)
        self.position = None
        return pnl
