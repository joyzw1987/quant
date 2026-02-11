class SimExecution:
    def __init__(self, slippage=1, contract_multiplier=1, commission_per_contract=0.0, commission_min=0.0):
        self.slippage = slippage
        self.contract_multiplier = contract_multiplier
        self.commission_per_contract = commission_per_contract
        self.commission_min = commission_min
        self.position = None
        self.trades = []

    def send_order(self, symbol, signal, price, size, atr=None, risk=None, contract_multiplier=None, bar_time=None):
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
            "contract_multiplier": contract_multiplier or self.contract_multiplier,
            "stop_price": stop_price,
            "take_profit": take_profit,
            "entry_time": bar_time,
        }
        return True

    def _calc_round_trip_commission(self, size):
        open_fee = max(self.commission_per_contract * size, self.commission_min)
        close_fee = max(self.commission_per_contract * size, self.commission_min)
        return open_fee + close_fee

    def check_exit(self, price, risk=None, bar_time=None):
        if self.position is None:
            return False, 0.0

        direction = self.position["direction"]
        entry = self.position["entry_price"]
        size = self.position["size"]
        contract_multiplier = self.position.get("contract_multiplier", self.contract_multiplier)
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

        gross_pnl = (
            (exit_price - entry) * size * contract_multiplier
            if direction == "LONG"
            else (entry - exit_price) * size * contract_multiplier
        )
        commission = self._calc_round_trip_commission(size)
        pnl = gross_pnl - commission
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "size": size,
            "contract_multiplier": contract_multiplier,
            "gross_pnl": gross_pnl,
            "commission": commission,
            "pnl": pnl,
            "entry_time": self.position.get("entry_time"),
            "exit_time": bar_time,
        }
        self.trades.append(trade)
        self.position = None
        return True, pnl

    def force_close(self, price, bar_time=None):
        if self.position is None:
            return 0.0

        direction = self.position["direction"]
        entry = self.position["entry_price"]
        size = self.position["size"]
        contract_multiplier = self.position.get("contract_multiplier", self.contract_multiplier)
        gross_pnl = (
            (price - entry) * size * contract_multiplier
            if direction == "LONG"
            else (entry - price) * size * contract_multiplier
        )
        commission = self._calc_round_trip_commission(size)
        pnl = gross_pnl - commission
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": price,
            "size": size,
            "contract_multiplier": contract_multiplier,
            "gross_pnl": gross_pnl,
            "commission": commission,
            "pnl": pnl,
            "entry_time": self.position.get("entry_time"),
            "exit_time": bar_time,
        }
        self.trades.append(trade)
        self.position = None
        return pnl
