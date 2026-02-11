import os


def main():
    links = []
    for name in ("batch_report.html", "dashboard.html", "report.html"):
        path = os.path.join("output", name)
        if os.path.exists(path):
            links.append(f"<li><a href='{name}'>{name}</a></li>")
    html = "<html><head><meta charset='utf-8'><title>Index</title></head><body><h1>Reports</h1><ul>" + "".join(links) + "</ul></body></html>"
    out_path = os.path.join("output", "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INDEX] saved {out_path}")


if __name__ == "__main__":
    main()
