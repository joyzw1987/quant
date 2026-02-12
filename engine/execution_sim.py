import hashlib
from engine.execution_base import ExecutionBase


def _parse_hhmm(value):
    if not value or ":" not in str(value):
        return None
    parts = str(value).split(":")
    if len(parts) != 2:
        return None
    if not parts[0].isdigit() or not parts[1].isdigit():
        return None
    hh = int(parts[0])
    mm = int(parts[1])
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return None
    return hh * 60 + mm


def _time_from_bar(bar_time):
    if not bar_time:
        return None
    text = str(bar_time)
    if " " in text:
        text = text.split(" ", 1)[1]
    return _parse_hhmm(text)


def _in_session(now_minutes, start_minutes, end_minutes):
    if now_minutes is None or start_minutes is None or end_minutes is None:
        return False
    if start_minutes <= end_minutes:
        return start_minutes <= now_minutes <= end_minutes
    return now_minutes >= start_minutes or now_minutes <= end_minutes


def _clamp(value, min_value, max_value):
    return max(min_value, min(max_value, value))


class SimExecution(ExecutionBase):
    def __init__(
        self,
        slippage=1,
        contract_multiplier=1,
        commission_per_contract=0.0,
        commission_min=0.0,
        fill_ratio_min=1.0,
        fill_ratio_max=1.0,
        cost_model=None,
    ):
        self.slippage = slippage
        self.contract_multiplier = contract_multiplier
        self.commission_per_contract = commission_per_contract
        self.commission_min = commission_min
        self.fill_ratio_min = fill_ratio_min
        self.fill_ratio_max = fill_ratio_max
        self.cost_model = cost_model or {}
        self.position = None
        self.trades = []

    def _stable_unit(self, key):
        h = hashlib.md5(key.encode("utf-8")).hexdigest()
        return int(h[:8], 16) / float(0xFFFFFFFF)

    def _resolve_profile(self, bar_time):
        now_minutes = _time_from_bar(bar_time)
        profile = {
            "name": "default",
            "slippage": float(self.slippage),
            "commission_multiplier": 1.0,
            "fill_ratio_min": float(self.fill_ratio_min),
            "fill_ratio_max": float(self.fill_ratio_max),
            "reject_prob": 0.0,
        }
        if not self.cost_model:
            return profile
        profiles = self.cost_model.get("profiles") or []
        for item in profiles:
            start = _parse_hhmm((item or {}).get("start"))
            end = _parse_hhmm((item or {}).get("end"))
            if _in_session(now_minutes, start, end):
                profile["name"] = str(item.get("name", "profile"))
                if item.get("slippage") is not None:
                    profile["slippage"] = float(item.get("slippage"))
                if item.get("commission_multiplier") is not None:
                    profile["commission_multiplier"] = float(item.get("commission_multiplier"))
                if item.get("fill_ratio_min") is not None:
                    profile["fill_ratio_min"] = float(item.get("fill_ratio_min"))
                if item.get("fill_ratio_max") is not None:
                    profile["fill_ratio_max"] = float(item.get("fill_ratio_max"))
                if item.get("reject_prob") is not None:
                    profile["reject_prob"] = float(item.get("reject_prob"))
                break
        profile["fill_ratio_min"] = _clamp(profile["fill_ratio_min"], 0.0, 1.0)
        profile["fill_ratio_max"] = _clamp(profile["fill_ratio_max"], 0.0, 1.0)
        profile["reject_prob"] = _clamp(profile["reject_prob"], 0.0, 1.0)
        if profile["fill_ratio_max"] < profile["fill_ratio_min"]:
            profile["fill_ratio_max"] = profile["fill_ratio_min"]
        return profile

    def _pick_fill_ratio(self, symbol, direction, size, bar_time, profile):
        lo = profile["fill_ratio_min"]
        hi = profile["fill_ratio_max"]
        if hi <= lo:
            return lo
        key = f"{symbol}|{direction}|{size}|{bar_time}|{profile['name']}"
        u = self._stable_unit(key)
        return lo + (hi - lo) * u

    def send_order(self, symbol, signal, price, size, atr=None, risk=None, contract_multiplier=None, bar_time=None):
        if self.position is not None:
            return False
        direction = "LONG" if signal > 0 else "SHORT"
        profile = self._resolve_profile(bar_time)

        reject_key = f"reject|{symbol}|{direction}|{size}|{bar_time}|{profile['name']}"
        if self._stable_unit(reject_key) < profile["reject_prob"]:
            return False

        fill_ratio = self._pick_fill_ratio(symbol, direction, size, bar_time, profile)
        filled_size = max(0.0, float(size) * float(fill_ratio))
        if filled_size <= 0:
            return False

        slip = profile["slippage"]
        fill_price = price + slip if direction == "LONG" else price - slip
        stop_price = risk.get_stop_price(fill_price, direction, atr) if risk else None
        take_profit = risk.get_take_profit_price(fill_price, direction, atr) if risk else None
        self.position = {
            "symbol": symbol,
            "direction": direction,
            "entry_price": fill_price,
            "requested_size": size,
            "fill_ratio": fill_ratio,
            "size": filled_size,
            "contract_multiplier": contract_multiplier or self.contract_multiplier,
            "stop_price": stop_price,
            "take_profit": take_profit,
            "entry_time": bar_time,
            "cost_profile": profile["name"],
            "commission_multiplier": profile["commission_multiplier"],
        }
        return True

    def _calc_round_trip_commission(self, size, commission_multiplier=1.0):
        per_contract = self.commission_per_contract * commission_multiplier
        open_fee = max(per_contract * size, self.commission_min)
        close_fee = max(per_contract * size, self.commission_min)
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
        commission_multiplier = self.position.get("commission_multiplier", 1.0)

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
        commission = self._calc_round_trip_commission(size, commission_multiplier=commission_multiplier)
        pnl = gross_pnl - commission
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": exit_price,
            "requested_size": self.position.get("requested_size", size),
            "fill_ratio": self.position.get("fill_ratio", 1.0),
            "size": size,
            "contract_multiplier": contract_multiplier,
            "cost_profile": self.position.get("cost_profile", "default"),
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
        commission_multiplier = self.position.get("commission_multiplier", 1.0)
        gross_pnl = (
            (price - entry) * size * contract_multiplier
            if direction == "LONG"
            else (entry - price) * size * contract_multiplier
        )
        commission = self._calc_round_trip_commission(size, commission_multiplier=commission_multiplier)
        pnl = gross_pnl - commission
        trade = {
            "direction": direction,
            "entry_price": entry,
            "exit_price": price,
            "requested_size": self.position.get("requested_size", size),
            "fill_ratio": self.position.get("fill_ratio", 1.0),
            "size": size,
            "contract_multiplier": contract_multiplier,
            "cost_profile": self.position.get("cost_profile", "default"),
            "gross_pnl": gross_pnl,
            "commission": commission,
            "pnl": pnl,
            "entry_time": self.position.get("entry_time"),
            "exit_time": bar_time,
        }
        self.trades.append(trade)
        self.position = None
        return pnl



