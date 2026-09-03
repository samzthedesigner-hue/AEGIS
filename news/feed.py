import logging
import threading
import time
import feedparser
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

class NewsFeedManager:
    def __init__(self, config, cache_manager):
        self.config = config
        self.cache_manager = cache_manager
        self.news_cache: Dict[str, List[Dict]] = {}
        self.cache_lock = threading.Lock()
        self.last_refresh = 0
        self.refresh_interval = config.NEWS_REFRESH_INTERVAL
        self.updater_thread = None
        self.is_running = False

    def start_updater(self):
        if self.is_running:
            return
        self.is_running = True
        self.updater_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.updater_thread.start()
        logger.info("News feed updater started")

    def stop_updater(self):
        self.is_running = False
        if self.updater_thread:
            self.updater_thread.join(timeout=5)

    def _update_loop(self):
        while self.is_running:
            self.refresh_news()
            time.sleep(self.refresh_interval)

    def refresh_news(self):
        for category, feeds in self.config.NEWS_SOURCES.items():
            items = []
            for feed_url in feeds:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:10]:
                        items.append({
                            'title': entry.get('title', ''),
                            'url': entry.get('link', ''),
                            'snippet': entry.get('summary', '')[:300],
                            'published': entry.get('published', ''),
                            'source': feed_url,
                            'category': category
                        })
                except Exception as e:
                    logger.warning(f"Feed {feed_url} failed: {e}")
            with self.cache_lock:
                self.news_cache[category] = items
        self.last_refresh = time.time()
        logger.info(f"News refreshed at {datetime.now().isoformat()}")

    def get_news(self, category: str = 'all', limit: int = 20) -> List[Dict]:
        with self.cache_lock:
            if category == 'all':
                all_items = []
                for items in self.news_cache.values():
                    all_items.extend(items)
                return all_items[:limit]
            return self.news_cache.get(category, [])[:limit]

    def get_trending(self) -> List[str]:
        trending = []
        with self.cache_lock:
            for items in self.news_cache.values():
                for item in items[:5]:
                    title = item.get('title', '')
                    if title:
                        trending.append(title)
        return trending[:20]
