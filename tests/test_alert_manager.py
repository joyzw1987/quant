import json
import tempfile
import unittest
from pathlib import Path

from engine.alert_manager import AlertManager


class AlertManagerTest(unittest.TestCase):
    def test_send_event_writes_json_line(self):
        with tempfile.TemporaryDirectory() as td:
            path = str(Path(td) / "alerts.log")
            alert = AlertManager(alert_file=path, webhook_url="")
            alert.send_event("unit_test", "hello", level="WARN", data={"x": 1})
            with open(path, "r", encoding="utf-8") as f:
                line = f.readline().strip()
            payload = json.loads(line)
            self.assertEqual("unit_test", payload["event"])
            self.assertEqual("WARN", payload["level"])
            self.assertEqual(1, payload["data"]["x"])


if __name__ == "__main__":
    unittest.main()
