import json
import os
from datetime import datetime


class StateStore:
    def __init__(self, path):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def update(self, fields: dict):
        state = self.load()
        state.update(fields)
        state["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
