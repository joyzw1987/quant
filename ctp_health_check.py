import json

from ctp_prepare import check_adapter, check_required, check_sdk_path, load_config
from engine.adapter_loader import load_adapter
from engine.config_validator import report_validation, validate_config
from engine.ctp_adapter import CtpAdapter
from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway


def main():
    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="ctp")
    report_validation(errors, warnings)

    ctp = cfg.get("ctp", {})
    symbol = cfg.get("symbol", "")
    report = {
        "simulate": bool(ctp.get("simulate", True)),
        "required_fields_ok": True,
        "sdk_ok": True,
        "adapter_ok": True,
        "md_connected": False,
        "td_connected": False,
        "subscribed": False,
    }

    if not report["simulate"]:
        missing = check_required(ctp)
        report["required_fields_ok"] = len(missing) == 0
        if missing:
            raise SystemExit(f"[CTP][ERROR] missing required fields: {', '.join(missing)}")

        sdk_ok, sdk_msg = check_sdk_path(ctp)
        report["sdk_ok"] = sdk_ok
        if not sdk_ok:
            raise SystemExit(f"[CTP][ERROR] {sdk_msg}")

    adapter_ok, adapter_msg = check_adapter(ctp)
    report["adapter_ok"] = adapter_ok
    if not adapter_ok:
        raise SystemExit(f"[CTP][ERROR] {adapter_msg}")

    adapter = load_adapter(cfg) or CtpAdapter(ctp)
    md = CtpMarketDataGateway(adapter.create_md_api())
    td = CtpTradeGateway(adapter.create_td_api())

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
    report["md_connected"] = bool(md.connected)
    report["td_connected"] = bool(td.connected)

    if symbol:
        report["subscribed"] = bool(md.subscribe([symbol]))

    print(json.dumps(report, ensure_ascii=False, indent=2))

    if not (report["md_connected"] and report["td_connected"]):
        raise SystemExit("[CTP][ERROR] gateway connect failed")

    print("[CTP] health check passed")


if __name__ == "__main__":
    main()
