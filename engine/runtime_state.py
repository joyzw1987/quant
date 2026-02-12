import json
import os
from datetime import datetime


class RuntimeState:
    def __init__(self, path="state/runtime_state.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def update(self, data: dict, replace=False):
        payload = {}
        if not replace and os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    old = json.load(f)
                    if isinstance(old, dict):
                        payload.update(old)
            except Exception:
                pass
        payload.update(dict(data))
        payload["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def load(self):
        if not os.path.exists(self.path):
            return {}
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
