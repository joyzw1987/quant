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

    risk = config.get("risk", {})
    if risk:
        stop_loss = risk.get("stop_loss_percentage")
        if not _is_number(stop_loss) or stop_loss < 0 or stop_loss > 1:
            push_error("risk.stop_loss_percentage must be between 0 and 1.")

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

    return errors, warnings


def report_validation(errors, warnings):
    for item in warnings:
        print(f"[WARN] {item}")
    if errors:
        for item in errors:
            print(f"[ERROR] {item}")
        raise SystemExit("Config validation failed.")
