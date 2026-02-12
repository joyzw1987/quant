import argparse
import json
import os


def _read_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _kv_rows(data):
    if not isinstance(data, dict):
        return "<tr><td colspan='2'>-</td></tr>"
    return "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in data.items())


def _blocked_rows(items):
    if not items:
        return "<tr><td colspan='3'>无</td></tr>"
    rows = []
    for item in items:
        rows.append(
            "<tr>"
            f"<td>{item.get('symbol', '-')}</td>"
            f"<td>{item.get('blocked_by', '-')}</td>"
            f"<td>{item.get('corr', '-')}</td>"
            "</tr>"
        )
    return "".join(rows)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build dashboard html")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args(argv)

    perf_path = os.path.join(args.output_dir, "performance.json")
    portfolio_path = os.path.join(args.output_dir, "portfolio", "portfolio_summary.json")
    perf = _read_json(perf_path)
    portfolio = _read_json(portfolio_path)
    if not perf and not portfolio:
        raise SystemExit("performance.json and portfolio_summary.json not found.")

    perf_rows = _kv_rows(perf)
    portfolio_rows = _kv_rows(portfolio)
    blocked_rows = _blocked_rows(portfolio.get("blocked_by_corr", []) if isinstance(portfolio, dict) else [])

    html = f"""
<!doctype html>
<html><head><meta charset='utf-8'><title>Dashboard</title></head>
<body>
<h1>Dashboard</h1>
<h2>单策略表现</h2>
<table border='1' cellpadding='6' cellspacing='0'>
{perf_rows}
</table>
<h2>组合表现</h2>
<table border='1' cellpadding='6' cellspacing='0'>
{portfolio_rows}
</table>
<h2>相关性剔除明细</h2>
<table border='1' cellpadding='6' cellspacing='0'>
<tr><th>symbol</th><th>blocked_by</th><th>corr</th></tr>
{blocked_rows}
</table>
</body></html>
"""

    out_path = os.path.join(args.output_dir, "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DASH] saved {out_path}")


if __name__ == "__main__":
    main()
