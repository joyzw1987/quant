import json
import time
from datetime import datetime

from engine.adapter_loader import load_adapter
from engine.alert_manager import AlertManager
from engine.config_validator import report_validation, validate_config
from engine.ctp_adapter import CtpAdapter
from engine.ctp_loader import prepare_ctp_sdk
from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway
from engine.position_reconciler import diff_account, diff_positions, summarize_positions
from engine.reconnect import ReconnectPolicy
from engine.state_store import StateStore


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _connect_with_retry(name, gateway, kwargs, policy, alert):
    for attempt in range(policy.max_retries):
        ok = gateway.connect(**kwargs)
        if ok:
            return True
        alert.send_event(
            event="ctp_connect_retry",
            level="WARN",
            message=f"{name} connect failed attempt={attempt + 1}",
            data={"error": getattr(gateway, "last_error", "")},
        )
        policy.backoff(attempt)
    return False


def main():
    cfg = load_config()
    errors, warnings = validate_config(cfg, mode="ctp")
    report_validation(errors, warnings)

    ctp = cfg["ctp"]
    monitor = cfg.get("monitor", {})
    symbol = cfg.get("symbol", "")
    alert = AlertManager(monitor.get("alert_file", "logs/alerts.log"), monitor.get("webhook_url", ""))

    sdk_path = ctp.get("sdk_path", "")
    simulate = ctp.get("simulate", True)
    if not simulate and sdk_path:
        prepare_ctp_sdk(sdk_path)

    adapter = load_adapter(cfg) or CtpAdapter(ctp)
    md = CtpMarketDataGateway(adapter.create_md_api())
    td = CtpTradeGateway(adapter.create_td_api())

    reconnect_cfg = ctp.get("reconnect", {})
    policy = ReconnectPolicy(
        max_retries=reconnect_cfg.get("max_retries", 10),
        base_delay=reconnect_cfg.get("base_delay", 1.0),
        max_delay=reconnect_cfg.get("max_delay", 30.0),
    )
    store = StateStore(ctp.get("state_path", "state/ctp_state.json"))

    md_args = {
        "broker_id": ctp.get("broker_id"),
        "user_id": ctp.get("user_id"),
        "password": ctp.get("password"),
        "front": ctp.get("md_front"),
        "app_id": ctp.get("app_id"),
        "auth_code": ctp.get("auth_code"),
        "product_info": ctp.get("product_info"),
    }
    td_args = {
        "broker_id": ctp.get("broker_id"),
        "user_id": ctp.get("user_id"),
        "password": ctp.get("password"),
        "front": ctp.get("td_front"),
        "app_id": ctp.get("app_id"),
        "auth_code": ctp.get("auth_code"),
        "product_info": ctp.get("product_info"),
    }

    print("[CTP] connecting...")
    md_ok = _connect_with_retry("md", md, md_args, policy, alert)
    td_ok = _connect_with_retry("td", td, td_args, policy, alert)
    if not (md_ok and td_ok):
        raise SystemExit("[CTP] connect failed after retries")

    subscribed = False
    if symbol:
        subscribed = md.subscribe([symbol])
        if not subscribed:
            alert.send_event(
                event="ctp_subscribe_failed",
                level="ERROR",
                message=f"subscribe failed symbol={symbol}",
                data={"error": md.last_error},
            )

    store.update(
        {
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "simulate": simulate,
            "md_connected": md.connected,
            "td_connected": td.connected,
            "subscribed": bool(subscribed),
            "symbol": symbol,
        }
    )
    print(f"[CTP] connected (simulate={simulate})")

    watchdog = ctp.get("watchdog", {}) or {}
    interval_sec = int(watchdog.get("interval_sec", 30))
    if interval_sec <= 0:
        interval_sec = 30
    query_positions_enabled = bool(watchdog.get("query_positions", True))
    query_orders_enabled = bool(watchdog.get("query_orders", True))
    position_tolerance = float(watchdog.get("position_tolerance", 0.0))
    account_tolerance = float(watchdog.get("account_tolerance", 1e-6))
    protection_mode = False

    smoke_order = bool(ctp.get("smoke_order", False))
    if smoke_order and symbol:
        order = td.place_order(symbol=symbol, direction="BUY", price=1.0, size=1, order_type="LIMIT")
        alert.send_event(
            event="ctp_smoke_order",
            level="INFO" if order.get("ok") else "ERROR",
            message=f"smoke_order ok={order.get('ok')}",
            data=order,
        )

    try:
        while True:
            if not md.connected:
                md_ok = _connect_with_retry("md", md, md_args, policy, alert)
                if symbol and md_ok:
                    md.subscribe([symbol])
            if not td.connected:
                _connect_with_retry("td", td, td_args, policy, alert)

            positions = td.query_positions() if query_positions_enabled else []
            orders = td.query_orders() if query_orders_enabled else []
            account = td.query_account() or {}

            state_now = store.load()
            local_positions = state_now.get("local_positions", {}) if isinstance(state_now, dict) else {}
            local_account = state_now.get("local_account", {}) if isinstance(state_now, dict) else {}
            broker_summary = summarize_positions(positions)
            position_diffs = diff_positions(local_positions, broker_summary)
            # Remove tiny floating noise.
            if position_tolerance > 0:
                filtered = {}
                for k, row in position_diffs.items():
                    try:
                        if abs(float(row.get("local", 0)) - float(row.get("broker", 0))) <= position_tolerance:
                            continue
                    except Exception:
                        pass
                    filtered[k] = row
                position_diffs = filtered
            account_diffs = diff_account(local_account, account, tolerance=account_tolerance)

            mismatch = bool(position_diffs or account_diffs)
            if mismatch and not protection_mode:
                protection_mode = True
                alert.send_event(
                    event="ctp_reconcile_mismatch",
                    level="ERROR",
                    message="broker/local state mismatch, enter protection mode",
                    data={"position_diffs": position_diffs, "account_diffs": account_diffs},
                )
            if not mismatch and protection_mode:
                protection_mode = False
                alert.send_event(
                    event="ctp_reconcile_recovered",
                    level="INFO",
                    message="reconcile recovered, leave protection mode",
                    data={},
                )

            payload = {
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "simulate": simulate,
                "md_connected": md.connected,
                "td_connected": td.connected,
                "symbol": symbol,
                "positions_count": len(positions or []),
                "orders_count": len(orders or []),
                "account": account,
                "broker_positions_summary": broker_summary,
                "position_diffs": position_diffs,
                "account_diffs": account_diffs,
                "protection_mode": protection_mode,
                "last_error_md": md.last_error,
                "last_error_td": td.last_error,
            }
            store.update(payload)
            time.sleep(interval_sec)
    except KeyboardInterrupt:
        md.disconnect()
        td.disconnect()
        print("[CTP] exit")


if __name__ == "__main__":
    main()
