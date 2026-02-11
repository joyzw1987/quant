import time


class ReconnectPolicy:
    def __init__(self, max_retries=10, base_delay=1.0, max_delay=30.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay

    def backoff(self, attempt):
        delay = min(self.base_delay * (attempt + 1), self.max_delay)
        time.sleep(delay)
