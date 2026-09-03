import logging
import json
import requests
from typing import Dict, Optional
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class GoogleAuthManager:
    def __init__(self, config):
        self.config = config
        self.client_id = config.GOOGLE_CLIENT_ID
        self.client_secret = config.GOOGLE_CLIENT_SECRET
        self.redirect_uri = config.GOOGLE_REDIRECT_URI or f"{config.RENDER_URL}/api/auth/google/callback"
        self.token_endpoint = 'https://oauth2.googleapis.com/token'
        self.userinfo_endpoint = 'https://www.googleapis.com/oauth2/v2/userinfo'
        self.auth_endpoint = 'https://accounts.google.com/o/oauth2/v2/auth'

    def get_auth_url(self) -> str:
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'response_type': 'code',
            'scope': 'openid email profile',
            'access_type': 'offline',
            'prompt': 'consent'
        }
        return f"{self.auth_endpoint}?{urlencode(params)}"

    def exchange_code(self, code: str) -> Optional[str]:
        try:
            data = {
                'code': code,
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'redirect_uri': self.redirect_uri,
                'grant_type': 'authorization_code'
            }
            response = requests.post(self.token_endpoint, data=data, timeout=10)
            response.raise_for_status()
            token_data = response.json()
            return token_data.get('access_token')
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return None

    def get_user_info(self, token: str) -> Dict:
        try:
            headers = {'Authorization': f'Bearer {token}'}
            response = requests.get(self.userinfo_endpoint, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"User info fetch failed: {e}")
            return {}
