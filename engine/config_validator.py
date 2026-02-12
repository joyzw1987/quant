import os

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

    monitor = config.get("monitor", {})
    if monitor and monitor.get("drawdown_alert_threshold") is not None:
        threshold = monitor.get("drawdown_alert_threshold")
        if not _is_number(threshold) or threshold < 0:
            push_error("monitor.drawdown_alert_threshold must be >= 0.")

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


