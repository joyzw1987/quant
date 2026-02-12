import json
import time

from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway
from engine.ctp_loader import prepare_ctp_sdk
from engine.ctp_adapter import CtpAdapter
from engine.alert_manager import AlertManager
from engine.adapter_loader import load_adapter
from engine.config_validator import validate_config, report_validation
from engine.state_store import StateStore
from engine.reconnect import ReconnectPolicy


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main():
    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="ctp")
    report_validation(errors, warnings)

    ctp = cfg["ctp"]
    monitor = cfg.get("monitor", {})
    alert = AlertManager(monitor.get("alert_file", "logs/alerts.log"), monitor.get("webhook_url", ""))

    sdk_path = ctp.get("sdk_path", "")
    simulate = ctp.get("simulate", True)
    if not simulate and sdk_path:
        prepare_ctp_sdk(sdk_path)

    adapter = load_adapter(cfg) or CtpAdapter(ctp)
    md = CtpMarketDataGateway(adapter.create_md_api() if adapter else None)
    td = CtpTradeGateway(adapter.create_td_api() if adapter else None)

    store = StateStore(ctp.get("state_path", "state/ctp_state.json"))
    reconnect_cfg = ctp.get("reconnect", {})
    policy = ReconnectPolicy(
        max_retries=reconnect_cfg.get("max_retries", 10),
        base_delay=reconnect_cfg.get("base_delay", 1.0),
        max_delay=reconnect_cfg.get("max_delay", 30.0),
    )

    print("[CTP] connecting...")
    md.connect(
        broker_id=ctp.get("broker_id"),
        user_id=ctp.get("user_id"),
        password=ctp.get("password"),
        front=ctp.get("md_front"),
        app_id=ctp.get("app_id"),
        auth_code=ctp.get("auth_code"),
        product_info=ctp.get("product_info"),
    )
    td.connect(
        broker_id=ctp.get("broker_id"),
        user_id=ctp.get("user_id"),
        password=ctp.get("password"),
        front=ctp.get("td_front"),
        app_id=ctp.get("app_id"),
        auth_code=ctp.get("auth_code"),
        product_info=ctp.get("product_info"),
    )

    if cfg.get("symbol"):
        md.subscribe([cfg["symbol"]])

    store.update({"md_connected": True, "td_connected": True})
    print("[CTP] connected (simulate=%s)" % simulate)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("[CTP] exit")


if __name__ == "__main__":
    main()
