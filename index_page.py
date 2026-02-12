import os


def main():
    links = []
    for name in (
        "batch_report.html",
        "dashboard.html",
        "report.html",
        "param_heatmap_M2609.html",
    ):
        path = os.path.join("output", name)
        if os.path.exists(path):
            links.append(f"<li><a href='{name}'>{name}</a></li>")

    portfolio_summary = os.path.join("output", "portfolio", "portfolio_summary.json")
    portfolio_curve = os.path.join("output", "portfolio", "portfolio_equity.csv")
    if os.path.exists(portfolio_summary):
        links.append("<li><a href='portfolio/portfolio_summary.json'>portfolio_summary.json</a></li>")
    if os.path.exists(portfolio_curve):
        links.append("<li><a href='portfolio/portfolio_equity.csv'>portfolio_equity.csv</a></li>")

    html = (
        "<html><head><meta charset='utf-8'><title>Index</title></head>"
        "<body><h1>Reports</h1><ul>"
        + "".join(links)
        + "</ul></body></html>"
    )
    out_path = os.path.join("output", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INDEX] saved {out_path}")


if __name__ == "__main__":
    main()
