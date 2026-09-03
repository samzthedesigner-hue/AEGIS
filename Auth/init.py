"""Authentication module for AEGIS Knowledge Engine"""

try:
    from auth.google_auth import GoogleAuthManager
    __all__ = ['GoogleAuthManager']
except ImportError:
    # Google Auth not available - provide a stub
    class GoogleAuthManager:
        def __init__(self, config=None):
            self.config = config
            self.client_id = ''
            self.client_secret = ''
            self.redirect_uri = ''
        
        def get_auth_url(self):
            return ''
        
        def exchange_code(self, code):
            return None
        
        def get_user_info(self, token):
            return {}
    
    __all__ = ['GoogleAuthManager']
