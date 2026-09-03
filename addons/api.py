"""Add-on API - Interface for add-ons to interact with the browser"""

import logging
from typing import Dict, List, Optional, Callable

logger = logging.getLogger(__name__)


class AddonAPI:
    """API that add-ons use to interact with the search engine"""
    
    def __init__(self, addon_id: str, config):
        self.addon_id = addon_id
        self.config = config
        self.storage: Dict[str, str] = {}
        self.event_listeners: Dict[str, List[Callable]] = {}
        logger.info(f"AddonAPI initialized for add-on: {addon_id}")
    
    # Page manipulation
    def inject_css(self, css: str) -> bool:
        """Inject CSS into current page"""
        logger.info(f"[{self.addon_id}] Injecting CSS: {css[:50]}...")
        return True
    
    def inject_javascript(self, js: str) -> bool:
        """Inject JavaScript into current page"""
        logger.info(f"[{self.addon_id}] Injecting JS: {js[:50]}...")
        return True
    
    def remove_element(self, selector: str) -> bool:
        """Remove element from page"""
        logger.info(f"[{self.addon_id}] Removing element: {selector}")
        return True
    
    def hide_element(self, selector: str) -> bool:
        """Hide element on page"""
        logger.info(f"[{self.addon_id}] Hiding element: {selector}")
        return True
    
    # Content access
    def get_page_content(self) -> str:
        """Get current page content"""
        return ""
    
    def get_page_url(self) -> str:
        """Get current page URL"""
        return ""
    
    def get_page_title(self) -> str:
        """Get current page title"""
        return ""
    
    # Storage (add-on's own isolated storage)
    def save_data(self, key: str, value: str) -> bool:
        """Save data to add-on storage"""
        self.storage[key] = value
        return True
    
    def get_data(self, key: str) -> Optional[str]:
        """Get data from add-on storage"""
        return self.storage.get(key)
    
    def remove_data(self, key: str) -> bool:
        """Remove data from add-on storage"""
        if key in self.storage:
            del self.storage[key]
            return True
        return False
    
    # Network
    def fetch_url(self, url: str, callback: Optional[Callable] = None) -> Optional[Dict]:
        """Fetch a URL (add-on can make network requests)"""
        try:
            import requests
            response = requests.get(url, timeout=10)
            result = {
                'status': response.status_code,
                'content': response.text[:5000],
                'headers': dict(response.headers)
            }
            if callback:
                callback(result)
            return result
        except Exception as e:
            logger.error(f"[{self.addon_id}] Fetch failed: {e}")
            return None
    
    def download_file(self, url: str, filename: str) -> bool:
        """Download a file"""
        logger.info(f"[{self.addon_id}] Downloading: {url}")
        return True
    
    # UI
    def show_notification(self, title: str, message: str) -> bool:
        """Show notification"""
        logger.info(f"[{self.addon_id}] Notification: {title} - {message}")
        return True
    
    def add_context_menu_item(self, label: str, callback: Callable) -> bool:
        """Add context menu item"""
        logger.info(f"[{self.addon_id}] Context menu: {label}")
        return True
    
    def add_toolbar_button(self, icon: str, callback: Callable) -> bool:
        """Add toolbar button"""
        logger.info(f"[{self.addon_id}] Toolbar button: {icon}")
        return True
    
    # Browser controls
    def open_new_tab(self, url: str) -> bool:
        """Open URL in new tab"""
        logger.info(f"[{self.addon_id}] Opening tab: {url}")
        return True
    
    def close_current_tab(self) -> bool:
        """Close current tab"""
        logger.info(f"[{self.addon_id}] Closing tab")
        return True
    
    def reload_page(self) -> bool:
        """Reload current page"""
        logger.info(f"[{self.addon_id}] Reloading page")
        return True
    
    # Events
    def on_page_loaded(self, callback: Callable) -> bool:
        """Register page loaded event"""
        return self._register_event('page_loaded', callback)
    
    def on_page_changed(self, callback: Callable) -> bool:
        """Register page changed event"""
        return self._register_event('page_changed', callback)
    
    def on_tab_activated(self, callback: Callable) -> bool:
        """Register tab activated event"""
        return self._register_event('tab_activated', callback)
    
    def _register_event(self, event_type: str, callback: Callable) -> bool:
        """Register event listener"""
        if event_type not in self.event_listeners:
            self.event_listeners[event_type] = []
        self.event_listeners[event_type].append(callback)
        return True
    
    def trigger_event(self, event_type: str, data: Dict = None) -> bool:
        """Trigger an event"""
        listeners = self.event_listeners.get(event_type, [])
        for callback in listeners:
            try:
                callback(data or {})
            except Exception as e:
                logger.error(f"[{self.addon_id}] Event callback failed: {e}")
        return True
    
    # Permissions
    def has_permission(self, permission: str) -> bool:
        """Check if add-on has permission"""
        return True
    
    def request_permission(self, permission: str) -> bool:
        """Request permission from user"""
        logger.info(f"[{self.addon_id}] Requesting permission: {permission}")
        return True
