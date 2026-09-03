"""Add-on repository management"""

import logging
import json
import os
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class AddonRepository:
    """Manages the add-on repository"""
    
    def __init__(self, config):
        self.config = config
        self.repository: List[Dict] = []
        self._load_builtin_repository()
        logger.info("AddonRepository initialized")
    
    def _load_builtin_repository(self):
        """Load built-in add-ons available in repository"""
        self.repository = [
            {
                'id': 'ad-blocker-pro',
                'name': 'Ad Blocker Pro',
                'version': '1.2.0',
                'description': 'Advanced ad blocking with custom filter lists',
                'author': 'AEGIS',
                'permissions': ['blockContent', 'pageModification', 'storage'],
                'size': 245760,
                'rating': 4.8,
                'downloads': 15234
            },
            {
                'id': 'translator',
                'name': 'Universal Translator',
                'version': '2.0.1',
                'description': 'Translate pages to any language',
                'author': 'AEGIS',
                'permissions': ['pageAccess', 'network'],
                'size': 512000,
                'rating': 4.5,
                'downloads': 8921
            },
            {
                'id': 'password-manager',
                'name': 'Secure Password Manager',
                'version': '3.1.0',
                'description': 'Save and autofill passwords securely',
                'author': 'AEGIS',
                'permissions': ['storage', 'pageAccess'],
                'size': 1024000,
                'rating': 4.7,
                'downloads': 12045
            },
            {
                'id': 'speed-dial',
                'name': 'Speed Dial',
                'version': '1.0.5',
                'description': 'Quick access to your favorite sites',
                'author': 'AEGIS',
                'permissions': ['storage'],
                'size': 102400,
                'rating': 4.2,
                'downloads': 5678
            },
            {
                'id': 'screenshot-pro',
                'name': 'Screenshot Pro',
                'version': '2.3.0',
                'description': 'Full-page screenshots with annotation',
                'author': 'AEGIS',
                'permissions': ['pageAccess', 'downloads'],
                'size': 307200,
                'rating': 4.6,
                'downloads': 7654
            },
            {
                'id': 'video-downloader-pro',
                'name': 'Video Downloader Pro',
                'version': '4.0.2',
                'description': 'Download videos from any site',
                'author': 'AEGIS',
                'permissions': ['downloads', 'pageAccess', 'network'],
                'size': 819200,
                'rating': 4.4,
                'downloads': 9876
            },
            {
                'id': 'reader-mode-pro',
                'name': 'Reader Mode Pro',
                'version': '2.1.3',
                'description': 'Clean reading experience with customization',
                'author': 'AEGIS',
                'permissions': ['pageModification', 'pageAccess'],
                'size': 204800,
                'rating': 4.3,
                'downloads': 6543
            },
            {
                'id': 'dark-mode-pro',
                'name': 'Dark Mode Pro',
                'version': '3.0.0',
                'description': 'Advanced dark mode with scheduling',
                'author': 'AEGIS',
                'permissions': ['pageModification'],
                'size': 153600,
                'rating': 4.9,
                'downloads': 18765
            }
        ]
    
    def get_all_addons(self) -> List[Dict]:
        """Get all available add-ons"""
        return self.repository
    
    def get_addon(self, addon_id: str) -> Optional[Dict]:
        """Get a specific add-on by ID"""
        for addon in self.repository:
            if addon['id'] == addon_id:
                return addon
        return None
    
    def search_addons(self, query: str) -> List[Dict]:
        """Search add-ons by name or description"""
        query_lower = query.lower()
        return [
            addon for addon in self.repository
            if query_lower in addon['name'].lower() or 
               query_lower in addon['description'].lower()
        ]
    
    def get_by_category(self, category: str) -> List[Dict]:
        """Get add-ons by category"""
        return [
            addon for addon in self.repository
            if category in addon.get('permissions', [])
        ]
    
    def get_popular(self, limit: int = 10) -> List[Dict]:
        """Get most popular add-ons"""
        sorted_addons = sorted(
            self.repository,
            key=lambda x: x.get('downloads', 0),
            reverse=True
        )
        return sorted_addons[:limit]
    
    def get_top_rated(self, limit: int = 10) -> List[Dict]:
        """Get top rated add-ons"""
        sorted_addons = sorted(
            self.repository,
            key=lambda x: x.get('rating', 0),
            reverse=True
        )
        return sorted_addons[:limit]
    
    def get_recently_added(self, limit: int = 10) -> List[Dict]:
        """Get recently added add-ons"""
        return self.repository[-limit:] if limit < len(self.repository) else self.repository
    
    def get_stats(self) -> Dict:
        """Get repository statistics"""
        return {
            'total_addons': len(self.repository),
            'total_downloads': sum(a.get('downloads', 0) for a in self.repository),
            'average_rating': sum(a.get('rating', 0) for a in self.repository) / len(self.repository) if self.repository else 0,
            'categories': {
                permission: len(self.get_by_category(permission))
                for permission in ['blockContent', 'pageModification', 'storage', 'network', 'downloads', 'pageAccess']
            }
  }
