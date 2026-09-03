import uuid
import re
import hashlib
from urllib.parse import urlparse
from flask import request

def generate_id() -> str:
    return str(uuid.uuid4())[:16]

def validate_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except:
        return False

def extract_domain(url: str) -> str:
    try:
        return urlparse(url).netloc
    except:
        return 'unknown'

def get_client_ip(request) -> str:
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or 'unknown'

def hash_content(content: str) -> str:
    return hashlib.md5(content.encode()).hexdigest()

def sanitize_filename(filename: str) -> str:
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = filename.strip('. ')
    return filename or 'download'

def truncate_text(text: str, max_length: int = 300) -> str:
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'
