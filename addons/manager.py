import os
import json
import logging
import threading
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class AddonManager:
    def __init__(self, config):
        self.config = config
        self.storage_dir = config.ADDON_STORAGE_DIR
        self.addons: Dict[str, Dict] = {}
        self.lock = threading.Lock()
        os.makedirs(self.storage_dir, exist_ok=True)
        self._load_builtin_addons()

    def _load_builtin_addons(self):
        builtin = [
            {
                'id': 'ad-blocker',
                'name': 'Ad Blocker',
                'version': '1.0.0',
                'description': 'Blocks ads on web pages',
                'enabled': False,
                'builtin': True,
                'permissions': ['blockContent', 'pageModification']
            },
            {
                'id': 'dark-mode',
                'name': 'Dark Mode',
                'version': '1.0.0',
                'description': 'Forces dark theme on all pages',
                'enabled': False,
                'builtin': True,
                'permissions': ['pageModification']
            },
            {
                'id': 'video-downloader',
                'name': 'Video Downloader',
                'version': '1.0.0',
                'description': 'Detects and downloads videos',
                'enabled': False,
                'builtin': True,
                'permissions': ['downloads', 'pageAccess']
            },
            {
                'id': 'reader-mode',
                'name': 'Reader Mode',
                'version': '1.0.0',
                'description': 'Strips clutter and shows clean text',
                'enabled': False,
                'builtin': True,
                'permissions': ['pageModification', 'pageAccess']
            },
            {
                'id': 'screenshot',
                'name': 'Screenshot',
                'version': '1.0.0',
                'description': 'Takes full-page screenshots',
                'enabled': False,
                'builtin': True,
                'permissions': ['pageAccess']
            }
        ]
        for addon in builtin:
            self.addons[addon['id']] = addon

    def get_installed_addons(self) -> List[Dict]:
        with self.lock:
            return list(self.addons.values())

    def get_repository_addons(self) -> List[Dict]:
        return [
            {
                'id': 'translator',
                'name': 'Translator',
                'version': '1.0.0',
                'description': 'Translates page content',
                'permissions': ['pageAccess', 'network']
            },
            {
                'id': 'password-manager',
                'name': 'Password Manager',
                'version': '1.0.0',
                'description': 'Saves and autofills passwords',
                'permissions': ['storage']
            },
            {
                'id': 'speed-dial',
                'name': 'Speed Dial',
                'version': '1.0.0',
                'description': 'Quick access to favorite sites',
                'permissions': ['storage']
            }
        ]

    def install(self, addon_id: str) -> Dict:
        repo_addons = {a['id']: a for a in self.get_repository_addons()}
        if addon_id in repo_addons:
            addon = repo_addons[addon_id]
            addon['enabled'] = False
            addon['builtin'] = False
            with self.lock:
                self.addons[addon_id] = addon
            return {'status': 'installed', 'addon': addon}
        return {'status': 'error', 'error': 'Add-on not found'}

    def uninstall(self, addon_id: str) -> Dict:
        with self.lock:
            if addon_id in self.addons and not self.addons[addon_id].get('builtin'):
                del self.addons[addon_id]
                return {'status': 'uninstalled'}
        return {'status': 'error', 'error': 'Cannot uninstall built-in add-on'}

    def toggle(self, addon_id: str, enabled: bool) -> Dict:
        with self.lock:
            if addon_id in self.addons:
                self.addons[addon_id]['enabled'] = enabled
                return {'status': 'toggled', 'enabled': enabled}
        return {'status': 'error', 'error': 'Add-on not found'}

    def execute_script(self, addon_id: str, script: str, page_url: str) -> Dict:
        with self.lock:
            addon = self.addons.get(addon_id)
        if not addon or not addon.get('enabled'):
            return {'status': 'error', 'error': 'Add-on not enabled'}
        return {'status': 'executed', 'result': f'Script executed on {page_url}'}
