import csv
import os
from datetime import datetime, timedelta

from engine.market_scheduler import is_market_open


class DataEngine:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir

    def _path(self, symbol):
        return os.path.join(self.data_dir, f"{symbol}.csv")

    def get_bars(self, symbol):
        path = self._path(symbol)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Data file not found: {path}")
        bars = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Handle BOM headers such as "\ufeffdatetime".
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

    def get_price_series(self, symbol):
        return [b["close"] for b in self.get_bars(symbol)]

    def validate_bars(self, bars, schedule=None):
        report = {
            "total": len(bars),
            "missing": 0,
            "start": bars[0]["datetime"] if bars else "",
            "end": bars[-1]["datetime"] if bars else "",
        }
        if not bars:
            report["missing"] = 0
            return report

        # Count missing bars by minute. When schedule is provided, only count
        # minutes expected to be open (ignore lunch breaks and closed sessions).
        try:
            prev = datetime.strptime(bars[0]["datetime"], "%Y-%m-%d %H:%M")
            miss = 0
            for b in bars[1:]:
                cur = datetime.strptime(b["datetime"], "%Y-%m-%d %H:%M")
                delta = (cur - prev).total_seconds() / 60.0
                if delta > 1:
                    if schedule is None:
                        miss += int(delta - 1)
                    else:
                        probe = prev + timedelta(minutes=1)
                        while probe < cur:
                            if is_market_open(probe, schedule):
                                miss += 1
                            probe += timedelta(minutes=1)
                prev = cur
            report["missing"] = miss
        except Exception:
            report["missing"] = 0
        return report

    def write_data_report(self, report, path):
        lines = [
            f"total={report.get('total', 0)}",
            f"missing={report.get('missing', 0)}",
            f"start={report.get('start', '')}",
            f"end={report.get('end', '')}",
        ]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
