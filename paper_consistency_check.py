import argparse
import csv
import math
import os


REQUIRED_FIELDS = [
    "direction",
    "entry_price",
    "exit_price",
    "size",
    "gross_pnl",
    "commission",
    "pnl",
]


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def check_trades(path, eps=1e-6):
    if not os.path.exists(path):
        return [f"missing file: {path}"]
    with open(path, "r", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    errors = []
    if not rows:
        return errors
    for field in REQUIRED_FIELDS:
        if field not in rows[0]:
            errors.append(f"missing field: {field}")
    for i, row in enumerate(rows, start=1):
        size = _to_float(row.get("size"))
        if size is None or size <= 0:
            errors.append(f"row {i}: invalid size={row.get('size')}")
        fill_ratio = _to_float(row.get("fill_ratio"))
        if fill_ratio is not None and (fill_ratio < 0 or fill_ratio > 1):
            errors.append(f"row {i}: invalid fill_ratio={fill_ratio}")
        gross = _to_float(row.get("gross_pnl"))
        fee = _to_float(row.get("commission"))
        pnl = _to_float(row.get("pnl"))
        if gross is None or fee is None or pnl is None:
            errors.append(f"row {i}: invalid pnl fields")
            continue
        if math.fabs((gross - fee) - pnl) > eps:
            errors.append(
                f"row {i}: pnl mismatch gross={gross} fee={fee} pnl={pnl}"
            )
    return errors


def main():
    parser = argparse.ArgumentParser(description="Paper trade consistency check")
    parser.add_argument("--trades", default="output/trades.csv")
    args = parser.parse_args()
    errors = check_trades(args.trades)
    if errors:
        print("[PAPER_CHECK] FAILED")
        for e in errors:
            print(e)
        raise SystemExit(1)
    print("[PAPER_CHECK] PASSED")
    print(f"trades={args.trades}")


if __name__ == "__main__":
    main()

