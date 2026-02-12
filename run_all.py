import subprocess
import sys


def run(cmd):
    print("[RUN] " + " ".join(cmd))
    subprocess.run(cmd, check=False)


def main():
    run([sys.executable, "batch_runner.py"])
    run([sys.executable, "batch_plot.py"])
    run([sys.executable, "single_report.py"])
    run([sys.executable, "batch_html.py"])
    run([sys.executable, "portfolio_runner.py"])
    run([sys.executable, "dashboard.py"])
    run([sys.executable, "index_page.py"])


if __name__ == "__main__":
    main()
