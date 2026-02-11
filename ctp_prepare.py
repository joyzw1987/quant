import json
import os
import sys
from importlib import util as importlib_util


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def check_required(ctp_cfg):
    missing = []
    for key in ("broker_id", "user_id", "password", "md_front", "td_front"):
        if not ctp_cfg.get(key):
            missing.append(key)
    return missing


def check_sdk_path(ctp_cfg):
    sdk_path = ctp_cfg.get("sdk_path", "")
    if not sdk_path:
        return False, "ctp.sdk_path is empty"
    if not os.path.exists(sdk_path):
        return False, f"ctp.sdk_path not found: {sdk_path}"
    return True, f"ctp.sdk_path ok: {sdk_path}"


def check_adapter(ctp_cfg):
    adapter_path = ctp_cfg.get("adapter_path", "")
    adapter_module = ctp_cfg.get("adapter_module", "")
    adapter_class = ctp_cfg.get("adapter_class", "CtpAdapter")
    if not adapter_path and not adapter_module:
        return True, "adapter not configured (optional)"
    if adapter_path:
        adapter_path = os.path.abspath(adapter_path)
        if not os.path.exists(adapter_path):
            return False, f"adapter_path not found: {adapter_path}"
        if adapter_path not in sys.path:
            sys.path.insert(0, adapter_path)
    if not adapter_module:
        return False, "adapter_module is required when adapter_path is set"
    spec = importlib_util.find_spec(adapter_module)
    if spec is None:
        return False, f"adapter_module not found: {adapter_module}"
    return True, f"adapter module ok: {adapter_module} (class={adapter_class})"


def main():
    cfg = load_config()
    ctp_cfg = cfg.get("ctp", {})
    simulate = ctp_cfg.get("simulate", True)
    print(f"[CTP] simulate={simulate}")
    if simulate:
        print("[CTP] simulate=true, skipping credential checks")
        return

    missing = check_required(ctp_cfg)
    if missing:
        print(f"[CTP][ERROR] missing required fields: {', '.join(missing)}")
    else:
        print("[CTP] required fields ok")

    ok, msg = check_sdk_path(ctp_cfg)
    print(f"[CTP] {msg}")

    ok_adapter, msg_adapter = check_adapter(ctp_cfg)
    status = "ok" if ok_adapter else "error"
    print(f"[CTP][{status.upper()}] {msg_adapter}")

    if missing or not ok or not ok_adapter:
        raise SystemExit("CTP prepare check failed")

    print("[CTP] ready to connect. Next: run `python ctp_runner.py`.")


if __name__ == "__main__":
    main()
