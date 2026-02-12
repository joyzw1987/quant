from pathlib import Path

import pandas as pd


def _normalize_sessions(config):
    market_hours = (config or {}).get("market_hours") or {}
    sessions = market_hours.get("sessions") or []
    normalized = []
    for item in sessions:
        start = (item or {}).get("start", "")
        end = (item or {}).get("end", "")
        if isinstance(start, str) and isinstance(end, str) and start and end:
            normalized.append((start, end))
    return normalized


def _in_session(value, start, end):
    if start <= end:
        return start <= value <= end
    return value >= start or value <= end


def _session_name(start, end, index):
    start_code = start.replace(":", "")
    end_code = end.replace(":", "")
    return f"s{index + 1}_{start_code}_{end_code}"


def _classify_session(dt_series, sessions):
    if not sessions:
        return pd.Series(["all_day"] * len(dt_series), index=dt_series.index)

    labels = []
    for value in dt_series.dt.strftime("%H:%M"):
        hit = None
        for idx, (start, end) in enumerate(sessions):
            if _in_session(value, start, end):
                hit = _session_name(start, end, idx)
                break
        labels.append(hit or "other")
    return pd.Series(labels, index=dt_series.index)


def save_raw_minutes_by_date_session(df, symbol, raw_root, config):
    if df is None or df.empty:
        return []

    root = Path(raw_root)
    sessions = _normalize_sessions(config)

    working = df.copy()
    working["datetime"] = pd.to_datetime(working["datetime"])
    working = working.sort_values("datetime")
    working["trade_date"] = working["datetime"].dt.strftime("%Y-%m-%d")
    working["session"] = _classify_session(working["datetime"], sessions)
    working["datetime"] = working["datetime"].dt.strftime("%Y-%m-%d %H:%M")

    saved = []
    for (trade_date, session), group in working.groupby(["trade_date", "session"]):
        day_dir = root / trade_date
        day_dir.mkdir(parents=True, exist_ok=True)
        file_path = day_dir / f"{symbol}_{session}.csv"

        content = group[["datetime", "open", "high", "low", "close"]].copy()
        if file_path.exists():
            old = pd.read_csv(file_path)
            content = pd.concat([old, content], ignore_index=True)
            content = content.drop_duplicates(subset=["datetime"]).sort_values("datetime")

        content.to_csv(file_path, index=False, encoding="utf-8-sig")
        saved.append(str(file_path))

    return saved
