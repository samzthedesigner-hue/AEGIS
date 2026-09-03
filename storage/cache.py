import time
import threading
import logging
from typing import Dict, Optional
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheManager:
    def __init__(self, config):
        self.config = config
        self.ttl = config.CACHE_TTL
        self.max_size = config.CACHE_MAX_SIZE
        self.cache: OrderedDict[str, tuple] = OrderedDict()
        self.lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self.evictions = 0
        logger.info(f"CacheManager initialized (TTL: {self.ttl}s, Max: {self.max_size})")

    def get(self, key: str) -> Optional[Dict]:
        with self.lock:
            if key in self.cache:
                value, expiry = self.cache[key]
                if time.time() < expiry:
                    self.hits += 1
                    self.cache.move_to_end(key)
                    return value
                else:
                    del self.cache[key]
                    self.misses += 1
                    return None
            else:
                self.misses += 1
                return None

    def set(self, key: str, value: Dict):
        with self.lock:
            expiry = time.time() + self.ttl
            self.cache[key] = (value, expiry)
            self.cache.move_to_end(key)
            while len(self.cache) > self.max_size:
                self.cache.popitem(last=False)
                self.evictions += 1

    def clear(self):
        with self.lock:
            self.cache.clear()

    def size(self) -> int:
        with self.lock:
            return len(self.cache)

    def get_stats(self) -> Dict:
        total = self.hits + self.misses
        return {
            'size': self.size(),
            'max_size': self.max_size,
            'hits': self.hits,
            'misses': self.misses,
            'evictions': self.evictions,
            'hit_rate': self.hits / total if total > 0 else 0,
            'ttl': self.ttl
      }
