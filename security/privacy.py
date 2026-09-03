import logging
import threading
from typing import Dict, Set

logger = logging.getLogger(__name__)

class PrivacyManager:
    def __init__(self, config):
        self.config = config
        self.incognito_clients: Set[str] = set()
        self.lock = threading.Lock()
        self.client_data: Dict[str, Dict] = {}

    def set_incognito(self, client_id: str, enabled: bool):
        with self.lock:
            if enabled:
                self.incognito_clients.add(client_id)
            else:
                self.incognito_clients.discard(client_id)

    def is_incognito(self, client_id: str) -> bool:
        with self.lock:
            return client_id in self.incognito_clients

    def clear_data(self, client_id: str):
        with self.lock:
            self.client_data.pop(client_id, None)
            self.incognito_clients.discard(client_id)
