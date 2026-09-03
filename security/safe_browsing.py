import logging
import hashlib
from typing import List
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class SafeBrowsingChecker:
    def __init__(self, config):
        self.config = config
        self.malicious_domains = self._load_malicious_domains()

    def _load_malicious_domains(self) -> set:
        domains = {
            'malware.com', 'phishing-site.net', 'spam.org',
            'suspicious-domain.xyz', 'fake-login.com'
        }
        return domains

    def is_malicious(self, url: str) -> bool:
        try:
            domain = urlparse(url).netloc.lower()
            if domain in self.malicious_domains:
                return True
            domain_hash = hashlib.md5(domain.encode()).hexdigest()
            return domain_hash in self.malicious_domains
        except Exception:
            return False
