import os
from datetime import datetime

from engine.data_policy import validate_data_policy


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_time_string(value):
    if not isinstance(value, str):
        return False
    if not value:
        return True
    if ":" not in value:
        return False
    parts = value.split(":")
    if len(parts) != 2:
        return False
    if not parts[0].isdigit() or not parts[1].isdigit():
        return False
    hour = int(parts[0])
    minute = int(parts[1])
    return 0 <= hour <= 23 and 0 <= minute <= 59


def _time_to_minutes(value):
    if not _is_time_string(value) or value == "":
        return None
    hour, minute = value.split(":")
    return int(hour) * 60 + int(minute)


def _is_date_string(value):
    if not isinstance(value, str) or not value:
        return False
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except Exception:
        return False


def validate_config(config, mode="paper"):
    errors = []
    warnings = []

    def push_error(msg):
        errors.append(msg)

    def push_warn(msg):
        warnings.append(msg)

    if not isinstance(config, dict):
        push_error("Config must be a JSON object.")
        return errors, warnings

    symbol = config.get("symbol", "")
    if not isinstance(symbol, str) or not symbol:
        push_error("symbol is required and must be a non-empty string.")

    contract = config.get("contract", {})
    if contract:
        multiplier = contract.get("multiplier")
        if not _is_number(multiplier) or multiplier <= 0:
            push_error("contract.multiplier must be > 0.")
        slippage = contract.get("slippage")
        if slippage is None or not _is_number(slippage) or slippage < 0:
            push_error("contract.slippage must be >= 0.")
        fill_ratio_min = contract.get("fill_ratio_min")
        fill_ratio_max = contract.get("fill_ratio_max")
        if fill_ratio_min is not None and (not _is_number(fill_ratio_min) or fill_ratio_min < 0 or fill_ratio_min > 1):
            push_error("contract.fill_ratio_min must be between 0 and 1.")
        if fill_ratio_max is not None and (not _is_number(fill_ratio_max) or fill_ratio_max < 0 or fill_ratio_max > 1):
            push_error("contract.fill_ratio_max must be between 0 and 1.")

    risk = config.get("risk", {})
    if risk:
        stop_loss = risk.get("stop_loss_percentage")
        if not _is_number(stop_loss) or stop_loss < 0 or stop_loss > 1:
            push_error("risk.stop_loss_percentage must be between 0 and 1.")

        loss_ratio = risk.get("loss_streak_reduce_ratio")
        if loss_ratio is not None and (not _is_number(loss_ratio) or loss_ratio < 0 or loss_ratio > 1):
            push_error("risk.loss_streak_reduce_ratio must be between 0 and 1.")

        loss_min = risk.get("loss_streak_min_multiplier")
        if loss_min is not None and (not _is_number(loss_min) or loss_min < 0 or loss_min > 1):
            push_error("risk.loss_streak_min_multiplier must be between 0 and 1.")

        halt_atr = risk.get("volatility_halt_atr")
        if halt_atr is not None and (not _is_number(halt_atr) or halt_atr <= 0):
            push_error("risk.volatility_halt_atr must be > 0.")

        resume_atr = risk.get("volatility_resume_atr")
        if resume_atr is not None and (not _is_number(resume_atr) or resume_atr < 0):
            push_error("risk.volatility_resume_atr must be >= 0.")
        if _is_number(halt_atr) and _is_number(resume_atr) and resume_atr > halt_atr:
            push_error("risk.volatility_resume_atr must be <= risk.volatility_halt_atr.")

    strategy = config.get("strategy", {})
    if strategy:
        fast = strategy.get("fast")
        slow = strategy.get("slow")
        if not isinstance(fast, int) or fast < 1:
            push_error("strategy.fast must be an integer >= 1.")
        if not isinstance(slow, int) or slow < 1:
            push_error("strategy.slow must be an integer >= 1.")
        if isinstance(fast, int) and isinstance(slow, int) and fast >= slow:
            push_error("strategy.fast must be less than strategy.slow.")
        mode_value = strategy.get("mode")
        if mode_value not in ("trend", "reversal"):
            push_error("strategy.mode must be 'trend' or 'reversal'.")
        min_diff = strategy.get("min_diff")
        if not _is_number(min_diff) or min_diff < 0:
            push_error("strategy.min_diff must be >= 0.")
        if not _is_time_string(strategy.get("trade_start", "")):
            push_error("strategy.trade_start must be HH:MM or empty.")
        if not _is_time_string(strategy.get("trade_end", "")):
            push_error("strategy.trade_end must be HH:MM or empty.")

    market_hours = config.get("market_hours", {})
    if market_hours:
        holidays_cfg = market_hours.get("holidays")
        if holidays_cfg is not None and not isinstance(holidays_cfg, dict):
            push_error("market_hours.holidays must be an object.")
        elif isinstance(holidays_cfg, dict):
            holiday_dates = holidays_cfg.get("dates")
            if holiday_dates is not None and not isinstance(holiday_dates, list):
                push_error("market_hours.holidays.dates must be a list.")
            if isinstance(holiday_dates, list):
                for idx, date in enumerate(holiday_dates):
                    if not _is_date_string(date):
                        push_error(f"market_hours.holidays.dates[{idx}] must be YYYY-MM-DD.")
            holiday_file = holidays_cfg.get("file")
            if holiday_file is not None and not isinstance(holiday_file, str):
                push_error("market_hours.holidays.file must be a string.")

        extra_workdays = market_hours.get("extra_workdays")
        if extra_workdays is not None and not isinstance(extra_workdays, list):
            push_error("market_hours.extra_workdays must be a list.")
        if isinstance(extra_workdays, list):
            for idx, date in enumerate(extra_workdays):
                if not _is_date_string(date):
                    push_error(f"market_hours.extra_workdays[{idx}] must be YYYY-MM-DD.")

        for key in ("special_closures", "special_sessions"):
            items = market_hours.get(key)
            if items is None:
                continue
            if not isinstance(items, list):
                push_error(f"market_hours.{key} must be a list.")
                continue
            for idx, item in enumerate(items):
                if not isinstance(item, dict):
                    push_error(f"market_hours.{key}[{idx}] must be an object.")
                    continue
                date = item.get("date")
                if not _is_date_string(date):
                    push_error(f"market_hours.{key}[{idx}].date must be YYYY-MM-DD.")
                start = item.get("start")
                end = item.get("end")
                if start is not None and not _is_time_string(start):
                    push_error(f"market_hours.{key}[{idx}].start must be HH:MM.")
                if end is not None and not _is_time_string(end):
                    push_error(f"market_hours.{key}[{idx}].end must be HH:MM.")

    if mode == "ctp":
        ctp = config.get("ctp", {})
        simulate = ctp.get("simulate", False)
        if not simulate:
            required = ["broker_id", "user_id", "password", "md_front", "td_front"]
            for key in required:
                if not ctp.get(key):
                    push_error(f"ctp.{key} is required for CTP mode.")
            sdk_path = ctp.get("sdk_path", "")
            if not sdk_path:
                push_error("ctp.sdk_path is required when simulate=false.")
            elif not os.path.exists(sdk_path):
                push_warn(f"ctp.sdk_path does not exist: {sdk_path}")

    policy_errors, policy_warnings = validate_data_policy(config)
    errors.extend(policy_errors)
    warnings.extend(policy_warnings)

    cycle_cfg = config.get("research_cycle", {})
    if cycle_cfg:
        numeric_keys = [
            "max_days",
            "min_dataset_days",
            "holdout_bars",
            "max_candidates",
            "dd_penalty",
            "min_trades",
            "min_holdout_trades",
            "min_score_improve",
        ]
        for key in numeric_keys:
            value = cycle_cfg.get(key)
            if value is None:
                continue
            if not _is_number(value):
                push_error(f"research_cycle.{key} must be a number.")

    scheduler = config.get("scheduler", {})
    if scheduler:
        fetch_times = scheduler.get("fetch_times", [])
        if fetch_times is not None and not isinstance(fetch_times, list):
            push_error("scheduler.fetch_times must be a list.")
        if isinstance(fetch_times, list):
            for item in fetch_times:
                if not _is_time_string(item):
                    push_error(f"scheduler.fetch_times invalid HH:MM: {item}")
        research_time = scheduler.get("research_time")
        if research_time is not None and not _is_time_string(research_time):
            push_error("scheduler.research_time must be HH:MM.")

    cost_model = config.get("cost_model", {})
    if cost_model:
        profiles = cost_model.get("profiles", [])
        ranges = []
        if profiles is not None and not isinstance(profiles, list):
            push_error("cost_model.profiles must be a list.")
        if isinstance(profiles, list):
            for idx, profile in enumerate(profiles):
                if not isinstance(profile, dict):
                    push_error(f"cost_model.profiles[{idx}] must be an object.")
                    continue
                if not _is_time_string(profile.get("start", "")):
                    push_error(f"cost_model.profiles[{idx}].start must be HH:MM.")
                if not _is_time_string(profile.get("end", "")):
                    push_error(f"cost_model.profiles[{idx}].end must be HH:MM.")
                for key in ("slippage", "commission_multiplier", "fill_ratio_min", "fill_ratio_max", "reject_prob"):
                    value = profile.get(key)
                    if value is None:
                        continue
                    if not _is_number(value):
                        push_error(f"cost_model.profiles[{idx}].{key} must be a number.")
                fr_min = profile.get("fill_ratio_min")
                fr_max = profile.get("fill_ratio_max")
                if fr_min is not None and (fr_min < 0 or fr_min > 1):
                    push_error(f"cost_model.profiles[{idx}].fill_ratio_min must be between 0 and 1.")
                if fr_max is not None and (fr_max < 0 or fr_max > 1):
                    push_error(f"cost_model.profiles[{idx}].fill_ratio_max must be between 0 and 1.")
                reject_prob = profile.get("reject_prob")
                if reject_prob is not None and (reject_prob < 0 or reject_prob > 1):
                    push_error(f"cost_model.profiles[{idx}].reject_prob must be between 0 and 1.")

                start_min = _time_to_minutes(profile.get("start", ""))
                end_min = _time_to_minutes(profile.get("end", ""))
                if start_min is not None and end_min is not None and start_min < end_min:
                    ranges.append((idx, start_min, end_min))

        ranges.sort(key=lambda x: x[1])
        for i in range(1, len(ranges)):
            prev_idx, _, prev_end = ranges[i - 1]
            cur_idx, cur_start, _ = ranges[i]
            if cur_start < prev_end:
                push_warn(
                    f"cost_model.profiles[{cur_idx}] overlaps with cost_model.profiles[{prev_idx}] "
                    "(later profile may be ignored)."
                )

    monitor = config.get("monitor", {})
    if monitor and monitor.get("drawdown_alert_threshold") is not None:
        threshold = monitor.get("drawdown_alert_threshold")
        if not _is_number(threshold) or threshold < 0:
            push_error("monitor.drawdown_alert_threshold must be >= 0.")
    if monitor and monitor.get("no_new_data_error_threshold") is not None:
        threshold = monitor.get("no_new_data_error_threshold")
        if not isinstance(threshold, int) or threshold < 1:
            push_error("monitor.no_new_data_error_threshold must be an integer >= 1.")

    data_quality = config.get("data_quality", {})
    if data_quality:
        enabled = data_quality.get("enabled")
        if enabled is not None and not isinstance(enabled, bool):
            push_error("data_quality.enabled must be true or false.")

        min_rows = data_quality.get("min_rows")
        if min_rows is not None and (not isinstance(min_rows, int) or min_rows < 1):
            push_error("data_quality.min_rows must be an integer >= 1.")

        max_missing_bars = data_quality.get("max_missing_bars")
        if max_missing_bars is not None and (not isinstance(max_missing_bars, int) or max_missing_bars < 0):
            push_error("data_quality.max_missing_bars must be an integer >= 0.")

        max_duplicates = data_quality.get("max_duplicates")
        if max_duplicates is not None and (not isinstance(max_duplicates, int) or max_duplicates < 0):
            push_error("data_quality.max_duplicates must be an integer >= 0.")

        max_missing_ratio = data_quality.get("max_missing_ratio")
        if max_missing_ratio is not None and (not _is_number(max_missing_ratio) or max_missing_ratio < 0 or max_missing_ratio > 1):
            push_error("data_quality.max_missing_ratio must be between 0 and 1.")

        max_jump_ratio = data_quality.get("max_jump_ratio")
        if max_jump_ratio is not None and (not _is_number(max_jump_ratio) or max_jump_ratio < 0 or max_jump_ratio > 1):
            push_error("data_quality.max_jump_ratio must be between 0 and 1.")

        warn_missing_ratio = data_quality.get("warn_missing_ratio")
        if warn_missing_ratio is not None and (
            not _is_number(warn_missing_ratio) or warn_missing_ratio < 0 or warn_missing_ratio > 1
        ):
            push_error("data_quality.warn_missing_ratio must be between 0 and 1.")

        min_coverage_ratio = data_quality.get("min_coverage_ratio")
        if min_coverage_ratio is not None and (
            not _is_number(min_coverage_ratio) or min_coverage_ratio < 0 or min_coverage_ratio > 1
        ):
            push_error("data_quality.min_coverage_ratio must be between 0 and 1.")

        warn_coverage_ratio = data_quality.get("warn_coverage_ratio")
        if warn_coverage_ratio is not None and (
            not _is_number(warn_coverage_ratio) or warn_coverage_ratio < 0 or warn_coverage_ratio > 1
        ):
            push_error("data_quality.warn_coverage_ratio must be between 0 and 1.")

        if _is_number(warn_missing_ratio) and _is_number(max_missing_ratio) and warn_missing_ratio > max_missing_ratio:
            push_error("data_quality.warn_missing_ratio must be <= data_quality.max_missing_ratio.")
        if (
            _is_number(warn_coverage_ratio)
            and _is_number(min_coverage_ratio)
            and warn_coverage_ratio < min_coverage_ratio
        ):
            push_error("data_quality.warn_coverage_ratio must be >= data_quality.min_coverage_ratio.")

    paper_check = config.get("paper_check", {})
    if paper_check:
        enabled = paper_check.get("enabled")
        strict = paper_check.get("strict")
        if enabled is not None and not isinstance(enabled, bool):
            push_error("paper_check.enabled must be true or false.")
        if strict is not None and not isinstance(strict, bool):
            push_error("paper_check.strict must be true or false.")

    portfolio = config.get("portfolio", {})
    if portfolio:
        max_corr = portfolio.get("max_corr")
        if max_corr is not None and (not _is_number(max_corr) or max_corr < -1 or max_corr > 1):
            push_error("portfolio.max_corr must be between -1 and 1.")
        weight_method = portfolio.get("weight_method")
        if weight_method is not None and str(weight_method) not in ("equal", "risk_budget"):
            push_error("portfolio.weight_method must be 'equal' or 'risk_budget'.")
        rebalance = portfolio.get("rebalance")
        if rebalance is not None and str(rebalance) not in ("none", "weekly", "monthly"):
            push_error("portfolio.rebalance must be 'none', 'weekly', or 'monthly'.")
        min_rebalance_bars = portfolio.get("min_rebalance_bars")
        if min_rebalance_bars is not None and (not isinstance(min_rebalance_bars, int) or min_rebalance_bars < 1):
            push_error("portfolio.min_rebalance_bars must be an integer >= 1.")

    return errors, warnings


def report_validation(errors, warnings):
    for item in warnings:
        print(f"[WARN] {item}")
    if errors:
        for item in errors:
            print(f"[ERROR] {item}")
        raise SystemExit("Config validation failed.")
