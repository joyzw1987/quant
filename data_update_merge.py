import argparse
from datetime import datetime
from pathlib import Path

import akshare as ak
import pandas as pd


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
    args = parser.parse_args()

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

    start = combined["datetime"].iloc[0]
    end = combined["datetime"].iloc[-1]
    print(
        f"[DATA] merged {out_path} rows={len(combined)} symbol={args.symbol} "
        f"range={start} -> {end} at {datetime.now():%Y-%m-%d %H:%M:%S}"
    )


if __name__ == "__main__":
    main()
