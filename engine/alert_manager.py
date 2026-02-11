import os
import json
from datetime import datetime


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
