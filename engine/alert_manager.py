import json
import os
from datetime import datetime
from urllib import error, request


class AlertManager:
    def __init__(self, alert_file="logs/alerts.log", webhook_url=""):
        self.alert_file = alert_file
        self.webhook_url = webhook_url
        os.makedirs(os.path.dirname(alert_file), exist_ok=True)

    def send(self, message):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {message}"
        with open(self.alert_file, "a", encoding="utf-8") as f:
            f.write(line + "\n")
        print(line)

    def send_event(self, event, message, level="INFO", data=None):
        payload = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "level": str(level).upper(),
            "event": str(event),
            "message": str(message),
            "data": data or {},
        }
        with open(self.alert_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")
        print(f"[{payload['time']}][{payload['level']}][{payload['event']}] {payload['message']}")
        self._send_webhook(payload)

    def _send_webhook(self, payload):
        if not self.webhook_url:
            return
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            self.webhook_url,
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=5):
                return
        except (error.URLError, TimeoutError):
            # Alert channel is best effort. Fail quietly to avoid breaking the strategy loop.
            return
