import argparse
import json
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd

from engine.data_policy import assert_source_allowed
from engine.raw_data_store import save_raw_minutes_by_date_session


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def fetch_minutes(symbol: str) -> pd.DataFrame:
    df = ak.futures_zh_minute_sina(symbol=symbol, period="1")
    if df is None or df.empty:
        return pd.DataFrame()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    return df


def load_existing(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    df = pd.read_csv(path)
    if df.empty:
        return df
    df["datetime"] = pd.to_datetime(df["datetime"])
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="M2609")
    parser.add_argument("--out", default="data/M2609.csv")
    parser.add_argument("--source", default="akshare")
    parser.add_argument("--raw-root", default=None, help="raw minute archive root, default from config")
    args = parser.parse_args()

    cfg = load_config()
    assert_source_allowed(cfg, args.source)
    storage_cfg = cfg.get("data_storage") or {}
    raw_root = args.raw_root or storage_cfg.get("raw_root", "E:/quantData")
    save_raw = bool(storage_cfg.get("save_raw", True))

    out_path = Path(args.out)
    new_df = fetch_minutes(args.symbol)
    if new_df.empty:
        raise SystemExit("No data fetched. Check symbol or data source.")

    existing = load_existing(out_path)
    combined = pd.concat(
        [
            existing[["datetime", "open", "high", "low", "close"]] if not existing.empty else existing,
            new_df[["datetime", "open", "high", "low", "close"]],
        ],
        ignore_index=True,
    )
    combined = combined.drop_duplicates(subset=["datetime"]).sort_values("datetime")
    combined["datetime"] = combined["datetime"].dt.strftime("%Y-%m-%d %H:%M")
    out_path.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(out_path, index=False)

    raw_saved = []
    if save_raw:
        raw_saved = save_raw_minutes_by_date_session(
            df=new_df[["datetime", "open", "high", "low", "close"]],
            symbol=args.symbol,
            raw_root=raw_root,
            config=cfg,
        )

    start = combined["datetime"].iloc[0]
    end = combined["datetime"].iloc[-1]
    print(
        f"[DATA] source={args.source} merged {out_path} rows={len(combined)} symbol={args.symbol} "
        f"range={start} -> {end} at {datetime.now():%Y-%m-%d %H:%M:%S}"
    )
    if raw_saved:
        print(f"[DATA] raw archived root={raw_root} files={len(raw_saved)}")


if __name__ == "__main__":
    main()
