import json
import os
import uuid
from datetime import datetime

from engine.strategy_state import StrategyState


class ParamVersionStore:
    def __init__(self, path="state/param_versions.json"):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)

    def _load_all(self):
        if not os.path.exists(self.path):
            return {"versions": []}
        with open(self.path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"versions": []}
        versions = data.get("versions")
        if not isinstance(versions, list):
            versions = []
        return {"versions": versions}

    def _save_all(self, payload):
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def append(self, symbol, params, source, metrics=None, note=""):
        payload = self._load_all()
        version = {
            "version_id": uuid.uuid4().hex[:12],
            "symbol": symbol,
            "params": params,
            "source": source,
            "metrics": metrics or {},
            "note": note,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        payload["versions"].append(version)
        self._save_all(payload)
        return version

    def list_versions(self, symbol=None, limit=20):
        payload = self._load_all()
        versions = payload["versions"]
        if symbol:
            versions = [v for v in versions if v.get("symbol") == symbol]
        versions = sorted(versions, key=lambda x: x.get("created_at", ""), reverse=True)
        return versions[:limit]

    def get(self, version_id):
        payload = self._load_all()
        for item in payload["versions"]:
            if item.get("version_id") == version_id:
                return item
        return None

    def rollback_to(self, config_path, version_id, strategy_state_path="state/strategy_state.json"):
        target = self.get(version_id)
        if not target:
            raise ValueError(f"version not found: {version_id}")

        with open(config_path, "r", encoding="utf-8-sig") as f:
            cfg = json.load(f)

        cfg.setdefault("strategy", {})
        cfg["strategy"].update(target["params"])
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)

        StrategyState(strategy_state_path).save_params(
            {
                "fast": cfg["strategy"].get("fast"),
                "slow": cfg["strategy"].get("slow"),
                "mode": cfg["strategy"].get("mode"),
                "min_diff": cfg["strategy"].get("min_diff"),
                "trend_filter": cfg["strategy"].get("trend_filter"),
                "trend_window": cfg["strategy"].get("trend_window"),
                "rsi_period": cfg["strategy"].get("rsi_period"),
                "rsi_overbought": cfg["strategy"].get("rsi_overbought"),
                "rsi_oversold": cfg["strategy"].get("rsi_oversold"),
            }
        )
        return target
