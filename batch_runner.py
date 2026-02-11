import json
import os

from main import main


def load_config(path="config.json"):
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def main_batch():
    cfg = load_config()
    symbols = cfg.get("symbols") or [cfg.get("symbol")]
    summary = []
    for sym in symbols:
        out_dir = os.path.join("output", sym)
        os.makedirs(out_dir, exist_ok=True)
        main(symbol_override=sym, output_dir=out_dir)
        perf_path = os.path.join(out_dir, "performance.json")
        if os.path.exists(perf_path):
            with open(perf_path, "r", encoding="utf-8") as f:
                perf = json.load(f)
            perf["symbol"] = sym
            if perf.get("initial_capital"):
                perf["return_pct"] = (perf.get("total_pnl", 0) / perf["initial_capital"]) * 100
            summary.append(perf)

    summary_path = os.path.join("output", "batch_summary.json")
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"[BATCH] saved {summary_path}")


if __name__ == "__main__":
    main_batch()
