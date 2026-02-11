import json
import os
from datetime import datetime


class StrategyState:
    def __init__(self, path="state/strategy_state.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_params(self, params: dict):
        payload = {"params": params, "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
