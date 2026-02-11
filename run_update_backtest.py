import argparse
import subprocess
import sys


def run(cmd):
    print(f"[RUN] {' '.join(cmd)}")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="M2609")
    parser.add_argument("--days", type=int, default=20)
    parser.add_argument("--out", default="data/M2609.csv")
    args = parser.parse_args()

    run([sys.executable, "data_update.py", "--symbol", args.symbol, "--days", str(args.days), "--out", args.out])
    run([sys.executable, "main.py"])


if __name__ == "__main__":
    main()
