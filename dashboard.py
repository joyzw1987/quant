import json
import os


def main():
    perf_path = os.path.join("output", "performance.json")
    if not os.path.exists(perf_path):
        raise SystemExit("performance.json not found.")
    with open(perf_path, "r", encoding="utf-8") as f:
        perf = json.load(f)

    rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in perf.items())
    html = f"""
<!doctype html>
<html><head><meta charset='utf-8'><title>Dashboard</title></head>
<body>
<h1>Dashboard</h1>
<table border='1' cellpadding='6' cellspacing='0'>
{rows}
</table>
</body></html>
"""

    out_path = os.path.join("output", "dashboard.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[DASH] saved {out_path}")


if __name__ == "__main__":
    main()
