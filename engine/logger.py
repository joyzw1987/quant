import os
from datetime import datetime


class Logger:
    def __init__(self, path="logs/runtime.log"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def log(self, msg):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {msg}"
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)
