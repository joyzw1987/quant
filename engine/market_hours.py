from datetime import datetime, time


class MarketHours:
    def __init__(self, sessions=None, holidays=None):
        self.sessions = sessions or []
        self.holidays = set(holidays or [])

    def is_open(self, dt: datetime):
        if dt.strftime("%Y-%m-%d") in self.holidays:
            return False
        if not self.sessions:
            return True
        t = dt.time()
        for start, end in self.sessions:
            if start <= t <= end:
                return True
        return False
