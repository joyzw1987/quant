import json

from engine.gateway_ctp import CtpMarketDataGateway, CtpTradeGateway
from engine.gateway_paper import PaperMarketDataGateway, PaperTradeGateway
from engine.execution_sim import SimExecution
from engine.data_engine import DataEngine
from engine.config_validator import validate_config, report_validation


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def run_paper(config):
    symbol = config["symbol"]
    data = DataEngine()
    execution = SimExecution()
    market = PaperMarketDataGateway(data)
    trade = PaperTradeGateway(execution)
    market.stream_bars(symbol)
    return market, trade


def run_ctp(config):
    ctp = config["ctp"]
    md = CtpMarketDataGateway()
    td = CtpTradeGateway()
    md.connect(
        broker_id=ctp["broker_id"],
        user_id=ctp["user_id"],
        password=ctp["password"],
        front=ctp["md_front"],
        app_id=ctp["app_id"],
        auth_code=ctp["auth_code"],
        product_info=ctp["product_info"],
    )
    td.connect(
        broker_id=ctp["broker_id"],
        user_id=ctp["user_id"],
        password=ctp["password"],
        front=ctp["td_front"],
        app_id=ctp["app_id"],
        auth_code=ctp["auth_code"],
        product_info=ctp["product_info"],
    )
    md.subscribe([config["symbol"]])
    return md, td


def main():
    config = load_config()
    mode = config.get("run_mode", "paper")
    errors, warnings = validate_config(config, mode=mode)
    report_validation(errors, warnings)
    symbol = config.get("symbol", "")
    if mode == "ctp":
        ctp_cfg = config.get("ctp", {})
        print(f"[RUN] mode=ctp symbol={symbol} simulate={ctp_cfg.get('simulate', False)} sdk_path={ctp_cfg.get('sdk_path', '')}")
        run_ctp(config)
    else:
        print(f"[RUN] mode=paper symbol={symbol}")
        run_paper(config)


if __name__ == "__main__":
    main()
