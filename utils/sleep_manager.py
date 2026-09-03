import threading
import time
import logging

logger = logging.getLogger(__name__)

class SleepManager:
    def __init__(self, config, self_pinger):
        self.config = config
        self.self_pinger = self_pinger
        self.sleep_timeout = config.SLEEP_TIMEOUT
        self.is_awake = True
        self.last_activity = time.time()
        self.activity_lock = threading.Lock()
        self.thread = None
        self.is_running = False

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        logger.info("SleepManager started")

    def stop(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=5)

    def update_activity(self):
        with self.activity_lock:
            self.last_activity = time.time()
            self.is_awake = True

    def wake(self):
        self.update_activity()
        if not self.is_awake:
            logger.info("Server waking up")
            self.is_awake = True

    def sleep(self):
        self.is_awake = False
        logger.info("Server entering sleep mode")

    def _monitor_loop(self):
        while self.is_running:
            with self.activity_lock:
                inactive_time = time.time() - self.last_activity
            if self.is_awake and inactive_time > self.sleep_timeout:
                self.is_awake = False
                logger.info(f"Server sleeping after {inactive_time:.0f}s of inactivity")
                self.self_pinger.stop()
            elif not self.is_awake and inactive_time <= self.sleep_timeout:
                self.is_awake = True
                logger.info("Server waking up")
                self.self_pinger.start()
                self.self_pinger.ping_now()
            time.sleep(30)

    def get_status(self) -> dict:
        with self.activity_lock:
            inactive_time = time.time() - self.last_activity
        return {
            'is_awake': self.is_awake,
            'last_activity': self.last_activity,
            'inactive_seconds': inactive_time,
            'sleep_timeout': self.sleep_timeout
        }
