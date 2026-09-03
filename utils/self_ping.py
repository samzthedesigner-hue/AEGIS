import threading
import time
import logging
import requests

logger = logging.getLogger(__name__)

class SelfPinger:
    def __init__(self, config):
        self.config = config
        self.ping_interval = config.PING_INTERVAL
        self.render_url = config.RENDER_URL
        self.is_running = False        self.thread = None
        self.last_ping_time = None
        self.ping_count = 0

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._ping_loop, daemon=True)
        self.thread.start()
        logger.info(f"Self-pinger started (interval: {self.ping_interval}s)")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("Self-pinger stopped")

    def ping_now(self) -> bool:
        try:
            response = requests.get(f"{self.render_url}/api/health", timeout=10)
            if response.status_code == 200:
                self.last_ping_time = time.time()
                self.ping_count += 1
                return True
        except Exception as e:
            logger.warning(f"Self-ping failed: {e}")
        return False

    def _ping_loop(self):
        while self.is_running:
            self.ping_now()
            time.sleep(self.ping_interval)

    def get_status(self) -> dict:
        return {
            'is_running': self.is_running,
            'last_ping_time': self.last_ping_time,
            'ping_count': self.ping_count,
            'interval': self.ping_interval
        }
