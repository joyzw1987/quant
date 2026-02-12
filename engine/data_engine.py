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
        raw_total = len(bars)
        report = {
            "raw_total": raw_total,
            "total": 0,
            "missing": 0,
            "duplicates": 0,
            "max_jump_ratio": 0.0,
            "coverage_ratio": 1.0,
            "start": bars[0]["datetime"] if bars else "",
            "end": bars[-1]["datetime"] if bars else "",
        }
        if not bars:
            return report

        # Deduplicate by datetime for stable gap/jump analysis.
        seen = set()
        unique = []
        duplicate_count = 0
        for b in bars:
            dt = b.get("datetime")
            if dt in seen:
                duplicate_count += 1
                continue
            seen.add(dt)
            unique.append(b)
        report["duplicates"] = duplicate_count
        report["total"] = len(unique)
        if not unique:
            report["coverage_ratio"] = 0.0
            return report

        try:
            parsed = []
            for b in unique:
                parsed.append((datetime.strptime(b["datetime"], "%Y-%m-%d %H:%M"), float(b["close"])))
            parsed.sort(key=lambda x: x[0])

            prev, prev_close = parsed[0]
            miss = 0
            max_jump = 0.0
            for cur, cur_close in parsed[1:]:
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

                if prev_close != 0:
                    jump = abs(cur_close - prev_close) / abs(prev_close)
                    if jump > max_jump:
                        max_jump = jump
                prev = cur
                prev_close = cur_close

            report["missing"] = miss
            report["max_jump_ratio"] = max_jump
            expected_open = report["total"] + report["missing"]
            report["coverage_ratio"] = (float(report["total"]) / float(expected_open)) if expected_open > 0 else 1.0
        except Exception:
            report["missing"] = 0
            report["max_jump_ratio"] = 0.0
            report["coverage_ratio"] = 1.0
        return report

    def write_data_report(self, report, path):
        lines = [
            f"raw_total={report.get('raw_total', report.get('total', 0))}",
            f"total={report.get('total', 0)}",
            f"missing={report.get('missing', 0)}",
            f"duplicates={report.get('duplicates', 0)}",
            f"max_jump_ratio={report.get('max_jump_ratio', 0.0)}",
            f"coverage_ratio={report.get('coverage_ratio', 1.0)}",
            f"start={report.get('start', '')}",
            f"end={report.get('end', '')}",
        ]
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
