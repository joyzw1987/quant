import json
import tempfile
import unittest
from pathlib import Path

from engine.param_version_store import ParamVersionStore


class ParamVersionStoreTest(unittest.TestCase):
    def test_append_and_list(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "state" / "param_versions.json")
            store = ParamVersionStore(path=path)
            store.append(
                symbol="M2609",
                params={"fast": 4, "slow": 20},
                source="unit_test",
                metrics={"score": 1.0},
            )
            items = store.list_versions(symbol="M2609", limit=5)
            self.assertEqual(1, len(items))
            self.assertEqual("M2609", items[0]["symbol"])

    def test_rollback_to(self):
        with tempfile.TemporaryDirectory() as td:
            state_path = str(Path(td) / "state" / "param_versions.json")
            config_path = str(Path(td) / "config.json")
            Path(td, "state").mkdir(parents=True, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"strategy": {"fast": 1, "slow": 2, "mode": "trend"}}, f)

            store = ParamVersionStore(path=state_path)
            item = store.append(
                symbol="M2609",
                params={"fast": 5, "slow": 30, "mode": "trend", "min_diff": 0.6},
                source="unit_test",
            )
            strategy_state_path = str(Path(td) / "state" / "strategy_state.json")
            target = store.rollback_to(
                config_path=config_path,
                version_id=item["version_id"],
                strategy_state_path=strategy_state_path,
            )
            self.assertEqual(item["version_id"], target["version_id"])

            with open(config_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.assertEqual(5, cfg["strategy"]["fast"])
            self.assertEqual(30, cfg["strategy"]["slow"])


if __name__ == "__main__":
    unittest.main()
