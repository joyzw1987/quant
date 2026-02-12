from datetime import datetime, time, timedelta


def parse_time_hhmm(value):
    if not value or not isinstance(value, str) or ":" not in value:
        return None
    parts = value.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        return None
    hour = int(parts[0])
    minute = int(parts[1])
    if hour < 0 or hour > 23 or minute < 0 or minute > 59:
        return None
    return time(hour, minute)


def _parse_sessions(items):
    sessions = []
    for item in items or []:
        if not isinstance(item, dict):
            continue
        start = parse_time_hhmm(item.get("start"))
        end = parse_time_hhmm(item.get("end"))
        if start and end:
            sessions.append((start, end))
    sessions.sort(key=lambda x: (x[0].hour, x[0].minute))
    return sessions


def _parse_closures(items):
    closure_map = {}
    full_days = set()
    for item in items or []:
        if not isinstance(item, dict):
            continue
        date = item.get("date")
        if not isinstance(date, str) or not date:
            continue
        start = parse_time_hhmm(item.get("start"))
        end = parse_time_hhmm(item.get("end"))
        if start and end:
            closure_map.setdefault(date, []).append((start, end))
        else:
            full_days.add(date)
    for date in closure_map:
        closure_map[date].sort(key=lambda x: (x[0].hour, x[0].minute))
    return full_days, closure_map


def load_market_schedule(config):
    market_cfg = config.get("market_hours") or {}
    sessions = _parse_sessions(market_cfg.get("sessions") or [])

    weekdays = market_cfg.get("weekdays")
    if not isinstance(weekdays, list) or not weekdays:
        weekdays = [1, 2, 3, 4, 5]

    holidays_cfg = market_cfg.get("holidays") or {}
    holidays = set()
    for d in holidays_cfg.get("dates") or []:
        if isinstance(d, str) and d:
            holidays.add(d)

    holiday_file = holidays_cfg.get("file")
    if isinstance(holiday_file, str) and holiday_file:
        try:
            with open(holiday_file, "r", encoding="utf-8") as f:
                for line in f:
                    token = line.strip()
                    if token and not token.startswith("#"):
                        holidays.add(token)
        except Exception:
            pass

    special_sessions_cfg = market_cfg.get("special_sessions") or []
    special_sessions = {}
    for item in special_sessions_cfg:
        if not isinstance(item, dict):
            continue
        date = item.get("date")
        if not isinstance(date, str) or not date:
            continue
        one = _parse_sessions([item])
        if one:
            special_sessions.setdefault(date, []).extend(one)
    for date in special_sessions:
        special_sessions[date].sort(key=lambda x: (x[0].hour, x[0].minute))

    full_closures, partial_closures = _parse_closures(market_cfg.get("special_closures") or [])

    return {
        "sessions": sessions,
        "weekdays": weekdays,
        "holidays": holidays,
        "special_sessions": special_sessions,
        "full_closures": full_closures,
        "partial_closures": partial_closures,
    }


def _is_in_ranges(t, ranges):
    for start, end in ranges or []:
        if start <= t <= end:
            return True
    return False


def _sessions_for_date(day, schedule):
    date_str = day.strftime("%Y-%m-%d")
    special = schedule.get("special_sessions", {}).get(date_str)
    if special:
        return special
    return schedule.get("sessions", [])


def _day_openable(day, schedule):
    date_str = day.strftime("%Y-%m-%d")
    if date_str in schedule.get("full_closures", set()):
        return False
    if date_str in schedule.get("holidays", set()) and date_str not in schedule.get("special_sessions", {}):
        return False
    wd = day.weekday() + 1
    if schedule.get("weekdays") and wd not in schedule["weekdays"] and date_str not in schedule.get("special_sessions", {}):
        return False
    return True


def is_market_open(now, schedule):
    date_str = now.strftime("%Y-%m-%d")
    if date_str in schedule.get("full_closures", set()):
        return False

    if not _day_openable(now.date(), schedule):
        return False

    sessions = _sessions_for_date(now.date(), schedule)
    if not sessions:
        return True

    t = now.time()
    if not _is_in_ranges(t, sessions):
        return False
    closures = schedule.get("partial_closures", {}).get(date_str, [])
    return not _is_in_ranges(t, closures)


def next_market_open(now, schedule, max_days=14):
    if is_market_open(now, schedule):
        return now

    for i in range(max_days + 1):
        day = (now + timedelta(days=i)).date()
        if not _day_openable(day, schedule):
            continue

        sessions = _sessions_for_date(day, schedule)
        date_str = day.strftime("%Y-%m-%d")
        closures = schedule.get("partial_closures", {}).get(date_str, [])
        if sessions:
            for start, _ in sessions:
                dt = datetime.combine(day, start)
                if dt > now and not _is_in_ranges(start, closures):
                    return dt
        else:
            dt = datetime.combine(day, time(0, 0))
            if dt > now:
                return dt
    return None
