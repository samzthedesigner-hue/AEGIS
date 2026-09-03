import os
import time
import threading
import logging
import requests
import hashlib
from typing import Dict, Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DownloadManager:
    def __init__(self, config, relay_manager):
        self.config = config
        self.relay_manager = relay_manager
        self.downloads: Dict[str, Dict] = {}
        self.download_lock = threading.Lock()
        self.download_dir = 'data/downloads'
        os.makedirs(self.download_dir, exist_ok=True)

    def start_download(self, url: str, filename: str = '', file_type: str = 'auto') -> str:
        download_id = hashlib.md5(f"{url}:{time.time()}".encode()).hexdigest()[:16]
        if not filename:
            filename = self._generate_filename(url)
        download_info = {
            'id': download_id,
            'url': url,
            'filename': filename,
            'file_type': file_type,
            'status': 'downloading',
            'progress': 0,
            'total_size': 0,
            'downloaded_size': 0,
            'start_time': time.time(),
            'file_path': os.path.join(self.download_dir, f"{download_id}_{filename}"),
            'thread': None,
            'paused': False,
            'cancelled': False
        }
        with self.download_lock:
            self.downloads[download_id] = download_info
        thread = threading.Thread(target=self._download_worker, args=(download_id,))
        thread.daemon = True
        download_info['thread'] = thread
        thread.start()
        return download_id

    def _download_worker(self, download_id: str):
        with self.download_lock:
            info = self.downloads.get(download_id)
            if not info:
                return
        url = info['url']
        file_path = info['file_path']
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()
            total_size = int(response.headers.get('content-length', 0))
            with self.download_lock:
                info['total_size'] = total_size
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.config.DOWNLOAD_CHUNK_SIZE):
                    with self.download_lock:
                        if info['cancelled']:
                            break
                        while info['paused'] and not info['cancelled']:
                            time.sleep(0.5)
                    if info['cancelled']:
                        break
                    f.write(chunk)
                    with self.download_lock:
                        info['downloaded_size'] += len(chunk)
                        if total_size > 0:
                            info['progress'] = info['downloaded_size'] / total_size * 100
            with self.download_lock:
                if info['cancelled']:
                    info['status'] = 'cancelled'
                    if os.path.exists(file_path):
                        os.remove(file_path)
                elif info['downloaded_size'] >= total_size and total_size > 0:
                    info['status'] = 'completed'
                    info['progress'] = 100
                else:
                    info['status'] = 'completed'
                    info['progress'] = 100
        except Exception as e:
            logger.error(f"Download failed for {url}: {e}")
            with self.download_lock:
                info['status'] = 'failed'
                info['error'] = str(e)

    def get_status(self, download_id: str) -> Optional[Dict]:
        with self.download_lock:
            info = self.downloads.get(download_id)
            if not info:
                return None
            return {
                'id': info['id'],
                'url': info['url'],
                'filename': info['filename'],
                'status': info['status'],
                'progress': info['progress'],
                'totalSize': info['total_size'],
                'downloadedSize': info['downloaded_size'],
                'fileType': info['file_type']
            }

    def pause(self, download_id: str):
        with self.download_lock:
            info = self.downloads.get(download_id)
            if info:
                info['paused'] = True
                info['status'] = 'paused'

    def resume(self, download_id: str):
        with self.download_lock:
            info = self.downloads.get(download_id)
            if info:
                info['paused'] = False
                info['status'] = 'downloading'

    def cancel(self, download_id: str):
        with self.download_lock:
            info = self.downloads.get(download_id)
            if info:
                info['cancelled'] = True
                info['status'] = 'cancelled'

    def get_file_path(self, download_id: str) -> Optional[str]:
        with self.download_lock:
            info = self.downloads.get(download_id)
            if info and info['status'] == 'completed':
                return info['file_path']
            return None

    def _generate_filename(self, url: str) -> str:
        parsed = urlparse(url)
        path = parsed.path
        filename = os.path.basename(path)
        if not filename or '.' not in filename:
            filename = f"download_{int(time.time())}"
        return filename
