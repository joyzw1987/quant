import argparse
import json
from datetime import datetime

import akshare as ak
import pandas as pd

from engine.data_policy import assert_source_allowed


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def fetch_minutes(symbol: str, days: int) -> pd.DataFrame:
    df = ak.futures_zh_minute_sina(symbol=symbol, period="1")
    if df is None or df.empty:
        return pd.DataFrame()
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    if days is not None and days > 0:
        unique_dates = sorted(df["datetime"].dt.date.unique())
        if len(unique_dates) > days:
            keep = set(unique_dates[-days:])
            df = df[df["datetime"].dt.date.isin(keep)]
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="M2609")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--out", default="data/M2609.csv")
    parser.add_argument("--source", default="akshare")
    args = parser.parse_args()

    cfg = load_config()
    assert_source_allowed(cfg, args.source)

    df = fetch_minutes(args.symbol, args.days)
    if df.empty:
        raise SystemExit("No data fetched. Check symbol or data source.")

    out = df[["datetime", "open", "high", "low", "close"]].copy()
    out["datetime"] = out["datetime"].dt.strftime("%Y-%m-%d %H:%M")
    out.to_csv(args.out, index=False)

    start = out["datetime"].iloc[0]
    end = out["datetime"].iloc[-1]
    print(
        f"[DATA] source={args.source} saved {args.out} rows={len(out)} symbol={args.symbol} "
        f"range={start} -> {end} at {datetime.now():%Y-%m-%d %H:%M:%S}"
    )


if __name__ == "__main__":
    main()
