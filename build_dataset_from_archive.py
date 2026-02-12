import argparse
import glob
import json
from datetime import datetime
from pathlib import Path

import pandas as pd


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def parse_date(value):
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


def main():
    parser = argparse.ArgumentParser(description="Build long training dataset from raw archive.")
    parser.add_argument("--symbol", default=None)
    parser.add_argument("--raw-root", default=None)
    parser.add_argument("--out", default=None)
    parser.add_argument("--start-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--end-date", default=None, help="YYYY-MM-DD")
    parser.add_argument("--max-days", type=int, default=0, help="0 means no limit")
    parser.add_argument("--report-out", default="output/dataset_build_report.json")
    args = parser.parse_args()

    cfg = load_config()
    symbol = args.symbol or cfg.get("symbol", "M2609")
    storage_cfg = cfg.get("data_storage") or {}
    raw_root = args.raw_root or storage_cfg.get("raw_root", "E:/quantData")
    out_path = args.out or f"data/{symbol}.csv"

    start_date = parse_date(args.start_date)
    end_date = parse_date(args.end_date)

    pattern = str(Path(raw_root) / "*" / "*" / "*" / f"{symbol}_*.csv")
    files = sorted(glob.glob(pattern))
    if not files:
        raise SystemExit(f"No archive files found: {pattern}")

    frames = []
    for file_path in files:
        try:
            df = pd.read_csv(file_path)
        except Exception:
            continue
        if df.empty or "datetime" not in df.columns:
            continue
        df = df[["datetime", "open", "high", "low", "close"]].copy()
        df["datetime"] = pd.to_datetime(df["datetime"])
        frames.append(df)

    if not frames:
        raise SystemExit("No valid csv content found in archive files.")

    merged = pd.concat(frames, ignore_index=True)
    merged = merged.dropna(subset=["datetime"]).drop_duplicates(subset=["datetime"]).sort_values("datetime")
    merged["trade_date"] = merged["datetime"].dt.date

    if start_date:
        merged = merged[merged["trade_date"] >= start_date]
    if end_date:
        merged = merged[merged["trade_date"] <= end_date]

    if args.max_days and args.max_days > 0:
        dates = sorted(merged["trade_date"].unique())
        keep_dates = set(dates[-args.max_days :])
        merged = merged[merged["trade_date"].isin(keep_dates)]

    if merged.empty:
        raise SystemExit("No rows left after date filtering.")

    out = merged[["datetime", "open", "high", "low", "close"]].copy()
    out["datetime"] = out["datetime"].dt.strftime("%Y-%m-%d %H:%M")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(out_path, index=False, encoding="utf-8")

    dates = sorted(merged["trade_date"].unique())
    report = {
        "symbol": symbol,
        "rows": len(out),
        "days": len(dates),
        "range_start": str(dates[0]),
        "range_end": str(dates[-1]),
        "out": out_path,
        "raw_root": raw_root,
    }
    report_out = args.report_out
    if report_out:
        report_path = Path(report_out)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

    print("Dataset build completed")
    print(f"symbol={symbol}")
    print(f"rows={len(out)}")
    print(f"days={len(dates)}")
    print(f"range={dates[0]} -> {dates[-1]}")
    print(f"out={out_path}")
    if report_out:
        print(f"report={report_out}")


if __name__ == "__main__":
    main()
