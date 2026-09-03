import logging
import time
import re
import hashlib
import threading
from typing import Dict, List, Optional, Set
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WebCrawler:
    def __init__(self, config):
        self.config = config
        self.user_agent = config.CRAWLER_USER_AGENT
        self.delay = config.CRAWLER_DELAY
        self.max_depth = config.MAX_CRAWL_DEPTH
        self.max_pages_per_domain = config.MAX_PAGES_PER_DOMAIN
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': self.user_agent})
        self.domain_lock = threading.Lock()
        self.domain_page_counts: Dict[str, int] = {}
        self.domain_last_access: Dict[str, float] = {}
        self.robots_cache: Dict[str, Optional[RobotFileParser]] = {}
        self.visited_urls: Set[str] = set()
        self.visited_lock = threading.Lock()

    def is_allowed_by_robots(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            domain = parsed.netloc
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            if robots_url in self.robots_cache:
                rp = self.robots_cache[robots_url]
                if rp is None:
                    return True
                return rp.can_fetch(self.user_agent, url)
            rp = RobotFileParser()
            rp.set_url(robots_url)
            try:
                rp.read()
                self.robots_cache[robots_url] = rp
                return rp.can_fetch(self.user_agent, url)
            except:
                self.robots_cache[robots_url] = None
                return True
        except Exception as e:
            logger.debug(f"robots.txt check failed for {url}: {e}")
            return True

    def _respect_delay(self, domain: str):
        with self.domain_lock:
            last_access = self.domain_last_access.get(domain, 0)
            elapsed = time.time() - last_access
            if elapsed < self.delay:
                time.sleep(self.delay - elapsed)
            self.domain_last_access[domain] = time.time()

    def _increment_page_count(self, domain: str) -> bool:
        with self.domain_lock:
            count = self.domain_page_counts.get(domain, 0)
            if count >= self.max_pages_per_domain:
                return False
            self.domain_page_counts[domain] = count + 1
            return True

    def crawl_single(self, url: str) -> Optional[Dict]:
        if url in self.visited_urls:
            return None
        if not self.is_allowed_by_robots(url):
            logger.info(f"Blocked by robots.txt: {url}")
            return None
        domain = urlparse(url).netloc
        if not self._increment_page_count(domain):
            return None
        self._respect_delay(domain)
        try:
            with self.visited_lock:
                self.visited_urls.add(url)
            response = self.session.get(url, timeout=self.config.MAX_CRAWL_TIMEOUT)
            response.raise_for_status()
            content_type = response.headers.get('Content-Type', '')
            if 'text/html' in content_type:
                return self._parse_html(url, response.text, response.headers)
            elif 'application/json' in content_type:
                return self._parse_json(url, response.json(), response.headers)
            else:
                return {
                    'url': url, 'title': url, 'text': '',
                    'content_type': content_type,
                    'headers': dict(response.headers),
                    'etag': response.headers.get('ETag'),
                    'last_modified': response.headers.get('Last-Modified')
                }
        except Exception as e:
            logger.warning(f"Crawl failed for {url}: {e}")
            return None

    def crawl_topic(self, topic: str, max_pages: int = 10) -> List[Dict]:
        results = []
        from search.meta_search import MetaSearchEngine
        meta_search = MetaSearchEngine(self.config)
        search_results = meta_search.search(topic, max_pages * 2)
        seed_urls = [r['url'] for r in search_results if r.get('url')][:max_pages]
        for url in seed_urls:
            result = self.crawl_single(url)
            if result:
                result['topic'] = topic
                results.append(result)
            if len(results) >= max_pages:
                break
        return results

    def _parse_html(self, url: str, html: str, headers: Dict) -> Dict:
        soup = BeautifulSoup(html, 'lxml')
        title = soup.title.string if soup.title else url
        for script in soup(['script', 'style', 'nav', 'footer', 'header']):
            script.decompose()
        text = soup.get_text(separator='\n', strip=True)
        links = []
        for a in soup.find_all('a', href=True):
            href = urljoin(url, a['href'])
            if href.startswith(('http://', 'https://')):
                links.append(href)
        meta_tags = {}
        for meta in soup.find_all('meta'):
            name = meta.get('name', meta.get('property', ''))
            content = meta.get('content', '')
            if name:
                meta_tags[name] = content
        images = []
        for img in soup.find_all('img', src=True):
            img_url = urljoin(url, img['src'])
            images.append(img_url)
        content_hash = hashlib.md5(text.encode()).hexdigest()
        return {
            'url': url,
            'title': title.strip() if title else url,
            'text': text[:50000],
            'links': links[:100],
            'images': images[:50],
            'meta': meta_tags,
            'content_hash': content_hash,
            'content_type': headers.get('Content-Type', 'text/html'),
            'etag': headers.get('ETag'),
            'last_modified': headers.get('Last-Modified'),
            'domain': urlparse(url).netloc
        }

    def _parse_json(self, url: str, data: Dict, headers: Dict) -> Dict:
        text = str(data)[:50000]
        return {
            'url': url, 'title': url, 'text': text,
            'content_type': 'application/json',
            'etag': headers.get('ETag'),
            'last_modified': headers.get('Last-Modified'),
            'domain': urlparse(url).netloc
              }
