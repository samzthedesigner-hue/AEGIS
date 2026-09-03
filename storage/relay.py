import logging
import json
import time
import threading
import hashlib
from datetime import datetime
from typing import Dict, List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class RelayManager:
    def __init__(self, config):
        self.config = config
        self.android_authority = config.ANDROID_AUTHORITY
        self.catches_uri = config.ANDROID_CATCHES_URI
        self.topics_uri = config.ANDROID_TOPICS_URI
        self.pending_operations = []
        self.operation_lock = threading.Lock()
        self.stats = {
            'total_searches_logged': 0,
            'total_crawls_stored': 0,
            'total_downloads_logged': 0,
            'total_auth_events': 0,
            'total_addon_events': 0,
            'total_syncs': 0,
            'last_sync': None,
            'pending_operations': 0
        }
        self.connected_devices = set()
        self.devices_lock = threading.Lock()
        logger.info("RelayManager initialized for Android ContentProvider")

    def log_search(self, query: str, results: Dict, search_type: str = 'all'):
        operation = {
            'type': 'search',
            'query': query,
            'results': results,
            'searchType': search_type,
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('search', query),
            'direction': 'incoming',
            'data': {
                'topic_name': query,
                'topic_status': 'searched',
                'content': json.dumps(results)[:5000],
                'tags': search_type,
                'url': f"search://{query}",
                'domain': 'search'
            }
        }
        self._queue_operation(operation)
        self.stats['total_searches_logged'] += 1
        result_operation = {
            'type': 'search_results',
            'query': query,
            'result_count': len(results.get('results', [])),
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('results', query),
            'direction': 'outgoing',
            'data': {
                'topic_name': query,
                'topic_status': 'results_returned',
                'content': json.dumps(results.get('results', []))[:5000],
                'tags': f"results_{search_type}",
                'url': f"results://{query}",
                'domain': 'results'
            }
        }
        self._queue_operation(result_operation)
        logger.info(f"Search logged: '{query}' (type: {search_type})")

    def store_crawl(self, url: str, content: Dict):
        operation = {
            'type': 'crawl',
            'url': url,
            'content': content,
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('crawl', url),
            'direction': 'incoming',
            'data': {
                'topic_name': content.get('topic', 'general'),
                'topic_status': 'crawled',
                'content': content.get('text', '')[:10000],
                'tags': content.get('tags', 'crawled'),
                'url': url,
                'domain': self._extract_domain(url),
                'etag': content.get('etag'),
                'last_modified': content.get('last_modified')
            }
        }
        self._queue_operation(operation)
        self.stats['total_crawls_stored'] += 1
        logger.info(f"Crawl stored: {url}")

    def log_download(self, url: str, download_id: str, status: str):
        operation = {
            'type': 'download',
            'url': url,
            'downloadId': download_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('download', url),
            'direction': 'outgoing' if status == 'served' else 'incoming',
            'data': {
                'topic_name': f"download_{status}",
                'topic_status': status,
                'content': f"Download {status}: {url}",
                'tags': f"download_{status}",
                'url': url,
                'domain': self._extract_domain(url)
            }
        }
        self._queue_operation(operation)
        self.stats['total_downloads_logged'] += 1
        logger.info(f"Download logged: {url} ({status})")

    def log_auth(self, email: str, action: str):
        operation = {
            'type': 'auth',
            'email': email if email else 'unknown',
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('auth', action),
            'direction': 'incoming',
            'data': {
                'topic_name': f"auth_{action}",
                'topic_status': 'auth',
                'content': f"Auth {action}: {email}",
                'tags': 'auth',
                'url': f"auth://{action}",
                'domain': 'auth'
            }
        }
        self._queue_operation(operation)
        self.stats['total_auth_events'] += 1
        logger.info(f"Auth event: {action}")

    def log_addon(self, addon_id: str, action: str):
        operation = {
            'type': 'addon',
            'addonId': addon_id,
            'action': action,
            'timestamp': datetime.now().isoformat(),
            'operation_id': self._generate_operation_id('addon', addon_id),
            'direction': 'incoming',
            'data': {
                'topic_name': f"addon_{action}",
                'topic_status': 'addon',
                'content': f"Addon {action}: {addon_id}",
                'tags': 'addon',
                'url': f"addon://{addon_id}",
                'domain': 'addon'
            }
        }
        self._queue_operation(operation)
        self.stats['total_addon_events'] += 1
        logger.info(f"Add-on event: {addon_id} {action}")

    def sync_to_android(self, data: Dict) -> Dict:
        try:
            operation = {
                'type': 'sync',
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'operation_id': self._generate_operation_id('sync', str(data)),
                'direction': 'incoming'
            }
            self._queue_operation(operation)
            self.stats['total_syncs'] += 1
            return {'status': 'queued', 'operationId': operation['operation_id']}
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {'status': 'error', 'error': str(e)}

    def _queue_operation(self, operation: Dict):
        with self.operation_lock:
            self.pending_operations.append(operation)
            self.stats['pending_operations'] = len(self.pending_operations)
        self.stats['last_sync'] = datetime.now().isoformat()

    def _generate_operation_id(self, prefix: str, data: str) -> str:
        hash_input = f"{prefix}:{data}:{time.time()}"
        return hashlib.md5(hash_input.encode()).hexdigest()[:16]

    def _extract_domain(self, url: str) -> str:
        try:
            return urlparse(url).netloc
        except:
            return 'unknown'

    def get_pending_operations(self) -> List[Dict]:
        with self.operation_lock:
            return list(self.pending_operations)

    def clear_pending_operations(self):
        with self.operation_lock:
            self.pending_operations.clear()
            self.stats['pending_operations'] = 0

    def get_status(self) -> Dict:
        return {
            **self.stats,
            'connectedDevices': len(self.connected_devices),
            'androidAuthority': self.android_authority,
            'catchesUri': self.catches_uri,
            'topicsUri': self.topics_uri
        }

    def register_device(self, device_id: str):
        with self.devices_lock:
            self.connected_devices.add(device_id)

    def unregister_device(self, device_id: str):
        with self.devices_lock:
            self.connected_devices.discard(device_id)
