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


def load_market_schedule(config):
    market_cfg = config.get("market_hours") or {}
    sessions_cfg = market_cfg.get("sessions") or []
    sessions = []
    for item in sessions_cfg:
        start = parse_time_hhmm(item.get("start"))
        end = parse_time_hhmm(item.get("end"))
        if start and end:
            sessions.append((start, end))
    sessions.sort(key=lambda x: (x[0].hour, x[0].minute))

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

    return {
        "sessions": sessions,
        "weekdays": weekdays,
        "holidays": holidays,
    }


def is_market_open(now, schedule):
    date_str = now.strftime("%Y-%m-%d")
    if date_str in schedule["holidays"]:
        return False

    wd = now.weekday() + 1
    if schedule["weekdays"] and wd not in schedule["weekdays"]:
        return False

    sessions = schedule["sessions"]
    if not sessions:
        return True

    t = now.time()
    for start, end in sessions:
        if start <= t <= end:
            return True
    return False


def next_market_open(now, schedule, max_days=14):
    if is_market_open(now, schedule):
        return now

    sessions = schedule["sessions"]
    weekdays = schedule["weekdays"]
    holidays = schedule["holidays"]

    for i in range(max_days + 1):
        day = (now + timedelta(days=i)).date()
        wd = day.weekday() + 1
        date_str = day.strftime("%Y-%m-%d")
        if weekdays and wd not in weekdays:
            continue
        if date_str in holidays:
            continue

        if sessions:
            for start, _ in sessions:
                dt = datetime.combine(day, start)
                if dt > now:
                    return dt
        else:
            dt = datetime.combine(day, time(0, 0))
            if dt > now:
                return dt
    return None
