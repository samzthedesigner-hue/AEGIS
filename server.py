import threading
import time
import json
import logging
import os
from datetime import datetime
from flask import Flask, request, jsonify, send_from_directory, Response, stream_with_context
from flask_cors import CORS

from config import Config
from storage.relay import RelayManager
from storage.cache import CacheManager
from search.meta_search import MetaSearchEngine
from search.crawler import WebCrawler
from search.ranker import ResultRanker
from downloads.manager import DownloadManager
from news.feed import NewsFeedManager
from auth.google_auth import GoogleAuthManager
from addons.manager import AddonManager
from security.safe_browsing import SafeBrowsingChecker
from security.privacy import PrivacyManager
from utils.self_ping import SelfPinger
from utils.sleep_manager import SleepManager
from utils.helpers import generate_id, validate_url, extract_domain, get_client_ip

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)
CORS(app, resources={r"/*": {"origins": "*"}})

config = Config()
cache_manager = CacheManager(config)
relay_manager = RelayManager(config)
meta_search = MetaSearchEngine(config)
crawler = WebCrawler(config)
ranker = ResultRanker()
download_manager = DownloadManager(config, relay_manager)
news_manager = NewsFeedManager(config, cache_manager)
auth_manager = GoogleAuthManager(config)
addon_manager = AddonManager(config)
safe_browsing = SafeBrowsingChecker(config)
privacy_manager = PrivacyManager(config)
self_pinger = SelfPinger(config)
sleep_manager = SleepManager(config, self_pinger)

active_clients = {}
clients_lock = threading.Lock()
request_timestamps = {}
rate_limit_lock = threading.Lock()

def rate_limit_check(client_ip):
    if not config.RATE_LIMIT_ENABLED:
        return True
    with rate_limit_lock:
        now = time.time()
        if client_ip not in request_timestamps:
            request_timestamps[client_ip] = []
        request_timestamps[client_ip] = [ts for ts in request_timestamps[client_ip] if now - ts < 60]
        if len(request_timestamps[client_ip]) >= config.MAX_REQUESTS_PER_MINUTE:
            return False
        request_timestamps[client_ip].append(now)
        return True

@app.before_request
def before_request():
    client_ip = get_client_ip(request)
    if not rate_limit_check(client_ip):
        return jsonify({'error': 'Rate limit exceeded'}), 429
    sleep_manager.wake()
    client_id = request.headers.get('X-Client-ID')
    if client_id:
        with clients_lock:
            active_clients[client_id] = time.time()

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'isAwake': sleep_manager.is_awake,
        'activeClients': len(active_clients),
        'uptime': time.time() - getattr(app, 'start_time', time.time()),
        'timestamp': datetime.now().isoformat(),
        'cacheSize': cache_manager.size(),
        'pendingRelayOps': len(relay_manager.get_pending_operations())
    })

@app.route('/api/register', methods=['POST'])
def register_client():
    data = request.json or {}
    client_id = data.get('clientId', generate_id())
    with clients_lock:
        active_clients[client_id] = time.time()
    sleep_manager.wake()
    return jsonify({'status': 'registered', 'clientId': client_id, 'activeClients': len(active_clients), 'serverTime': datetime.now().isoformat()})

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    data = request.json or {}
    client_id = data.get('clientId')
    if client_id:
        with clients_lock:
            active_clients[client_id] = time.time()
    sleep_manager.update_activity()
    return jsonify({'status': 'alive', 'activeClients': len(active_clients), 'serverTime': datetime.now().isoformat(), 'isAwake': sleep_manager.is_awake})

@app.route('/api/disconnect', methods=['POST'])
def disconnect_client():
    data = request.json or {}
    client_id = data.get('clientId')
    if client_id:
        with clients_lock:
            active_clients.pop(client_id, None)
    return jsonify({'status': 'disconnected', 'activeClients': len(active_clients)})

@app.route('/api/search', methods=['GET'])
def search():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'error': 'Missing query parameter'}), 400
    page = int(request.args.get('page', 1))
    limit = min(int(request.args.get('limit', 20)), config.MAX_RESULTS)
    search_type = request.args.get('type', 'all')
    cache_key = f"search:{query}:{page}:{limit}:{search_type}"
    cached = cache_manager.get(cache_key)
    if cached:
        relay_manager.log_search(query, cached, 'cache')
        return jsonify(cached)
    raw_results = meta_search.search(query, limit, search_type)
    ranked_results = ranker.rank(raw_results, query)
    response = {
        'query': query,
        'page': page,
        'limit': limit,
        'total': len(ranked_results),
        'results': ranked_results,
        'timestamp': datetime.now().isoformat(),
        'searchType': search_type
    }
    cache_manager.set(cache_key, response)
    relay_manager.log_search(query, response, 'live')
    return jsonify(response)

@app.route('/api/autocomplete', methods=['GET'])
def autocomplete():
    query = request.args.get('q', '').strip()
    if not query:
        return jsonify({'suggestions': []})
    suggestions = meta_search.get_suggestions(query, config.AUTOCOMPLETE_LIMIT)
    return jsonify({'query': query, 'suggestions': suggestions})

@app.route('/api/search/images', methods=['GET'])
def search_images():
    query = request.args.get('q', '')
    results = meta_search.search_images(query, 20)
    relay_manager.log_search(query, {'images': results}, 'images')
    return jsonify({'query': query, 'images': results})

@app.route('/api/search/videos', methods=['GET'])
def search_videos():
    query = request.args.get('q', '')
    results = meta_search.search_videos(query, 20)
    relay_manager.log_search(query, {'videos': results}, 'videos')
    return jsonify({'query': query, 'videos': results})

@app.route('/api/search/news', methods=['GET'])
def search_news():
    query = request.args.get('q', '')
    results = meta_search.search_news(query, 20)
    relay_manager.log_search(query, {'news': results}, 'news')
    return jsonify({'query': query, 'news': results})

@app.route('/api/search/academic', methods=['GET'])
def search_academic():
    query = request.args.get('q', '')
    results = meta_search.search_academic(query, 20)
    relay_manager.log_search(query, {'academic': results}, 'academic')
    return jsonify({'query': query, 'academic': results})

@app.route('/api/crawl', methods=['POST'])
def crawl_url():
    data = request.json or {}
    url = data.get('url')
    if not url or not validate_url(url):
        return jsonify({'error': 'Invalid URL'}), 400
    if config.RESPECT_ROBOTS_TXT and not crawler.is_allowed_by_robots(url):
        return jsonify({'error': 'Blocked by robots.txt'}), 403
    result = crawler.crawl_single(url)
    if result:
        relay_manager.store_crawl(url, result)
        return jsonify({'status': 'success', 'crawled': result})
    return jsonify({'error': 'Crawl failed'}), 500

@app.route('/api/crawl/topic', methods=['POST'])
def crawl_topic():
    data = request.json or {}
    topic = data.get('topic')
    max_pages = data.get('maxPages', 10)
    if not topic:
        return jsonify({'error': 'Missing topic'}), 400
    results = crawler.crawl_topic(topic, max_pages)
    for result in results:
        relay_manager.store_crawl(result['url'], result)
    return jsonify({'topic': topic, 'pagesCrawled': len(results), 'results': results})

@app.route('/api/download', methods=['POST'])
def download_file():
    data = request.json or {}
    url = data.get('url')
    filename = data.get('filename', '')
    file_type = data.get('fileType', 'auto')
    if not url or not validate_url(url):
        return jsonify({'error': 'Invalid URL'}), 400
    if config.SAFE_BROWSING_ENABLED and safe_browsing.is_malicious(url):
        return jsonify({'error': 'Blocked by safe browsing'}), 403
    download_id = download_manager.start_download(url, filename, file_type)
    relay_manager.log_download(url, download_id, 'started')
    return jsonify({'downloadId': download_id, 'status': 'started', 'url': url})

@app.route('/api/download/<download_id>', methods=['GET'])
def download_status(download_id):
    status = download_manager.get_status(download_id)
    if not status:
        return jsonify({'error': 'Download not found'}), 404
    return jsonify(status)

@app.route('/api/download/<download_id>/pause', methods=['POST'])
def pause_download(download_id):
    download_manager.pause(download_id)
    return jsonify({'status': 'paused'})

@app.route('/api/download/<download_id>/resume', methods=['POST'])
def resume_download(download_id):
    download_manager.resume(download_id)
    return jsonify({'status': 'resumed'})

@app.route('/api/download/<download_id>/cancel', methods=['POST'])
def cancel_download(download_id):
    download_manager.cancel(download_id)
    relay_manager.log_download(download_id, '', 'cancelled')
    return jsonify({'status': 'cancelled'})

@app.route('/api/download/<download_id>/file', methods=['GET'])
def download_file_content(download_id):
    file_path = download_manager.get_file_path(download_id)
    if not file_path or not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    relay_manager.log_download(download_id, '', 'served')
    return send_from_directory(os.path.dirname(file_path), os.path.basename(file_path), as_attachment=True)

@app.route('/api/news', methods=['GET'])
def get_news():
    category = request.args.get('category', 'all')
    limit = int(request.args.get('limit', 20))
    news_items = news_manager.get_news(category, limit)
    return jsonify({'category': category, 'news': news_items, 'timestamp': datetime.now().isoformat()})

@app.route('/api/news/trending', methods=['GET'])
def trending_topics():
    trends = news_manager.get_trending()
    return jsonify({'trending': trends})

@app.route('/api/auth/google/login', methods=['GET'])
def google_login():
    auth_url = auth_manager.get_auth_url()
    return jsonify({'authUrl': auth_url})

@app.route('/api/auth/google/callback', methods=['GET'])
def google_callback():
    code = request.args.get('code')
    if not code:
        return jsonify({'error': 'Missing code'}), 400
    token = auth_manager.exchange_code(code)
    user_info = auth_manager.get_user_info(token)
    relay_manager.log_auth(user_info.get('email', 'unknown'), 'login')
    return jsonify({'token': token, 'user': user_info})

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    relay_manager.log_auth('', 'logout')
    return jsonify({'status': 'logged_out'})

@app.route('/api/addons/list', methods=['GET'])
def list_addons():
    installed = addon_manager.get_installed_addons()
    return jsonify({'addons': installed})

@app.route('/api/addons/repository', methods=['GET'])
def addon_repository():
    available = addon_manager.get_repository_addons()
    return jsonify({'available': available})

@app.route('/api/addons/install', methods=['POST'])
def install_addon():
    data = request.json or {}
    addon_id = data.get('addonId')
    result = addon_manager.install(addon_id)
    relay_manager.log_addon(addon_id, 'install')
    return jsonify(result)

@app.route('/api/addons/uninstall', methods=['POST'])
def uninstall_addon():
    data = request.json or {}
    addon_id = data.get('addonId')
    result = addon_manager.uninstall(addon_id)
    relay_manager.log_addon(addon_id, 'uninstall')
    return jsonify(result)

@app.route('/api/addons/toggle', methods=['POST'])
def toggle_addon():
    data = request.json or {}
    addon_id = data.get('addonId')
    enabled = data.get('enabled', True)
    result = addon_manager.toggle(addon_id, enabled)
    return jsonify(result)

@app.route('/api/addons/execute', methods=['POST'])
def execute_addon():
    data = request.json or {}
    addon_id = data.get('addonId')
    script = data.get('script')
    page_url = data.get('pageUrl')
    result = addon_manager.execute_script(addon_id, script, page_url)
    return jsonify(result)

@app.route('/api/relay/sync', methods=['POST'])
def relay_sync():
    data = request.json or {}
    result = relay_manager.sync_to_android(data)
    return jsonify(result)

@app.route('/api/relay/status', methods=['GET'])
def relay_status():
    return jsonify(relay_manager.get_status())

@app.route('/api/relay/pending', methods=['GET'])
def relay_pending():
    pending = relay_manager.get_pending_operations()
    return jsonify({'pending': pending, 'count': len(pending)})

@app.route('/api/relay/clear', methods=['POST'])
def relay_clear():
    relay_manager.clear_pending_operations()
    return jsonify({'status': 'cleared'})

@app.route('/api/cache/clear', methods=['POST'])
def clear_cache():
    cache_manager.clear()
    return jsonify({'status': 'cleared'})

@app.route('/api/cache/stats', methods=['GET'])
def cache_stats():
    return jsonify(cache_manager.get_stats())

@app.route('/api/privacy/incognito', methods=['POST'])
def toggle_incognito():
    data = request.json or {}
    client_id = data.get('clientId')
    enabled = data.get('enabled', True)
    privacy_manager.set_incognito(client_id, enabled)
    return jsonify({'status': 'set', 'incognito': enabled})

@app.route('/api/privacy/clear-data', methods=['POST'])
def clear_privacy_data():
    data = request.json or {}
    client_id = data.get('clientId')
    privacy_manager.clear_data(client_id)
    return jsonify({'status': 'cleared'})

@app.route('/api/security/check-url', methods=['POST'])
def check_url_safety():
    data = request.json or {}
    url = data.get('url')
    if not url:
        return jsonify({'error': 'Missing URL'}), 400
    is_safe = not safe_browsing.is_malicious(url)
    return jsonify({'url': url, 'safe': is_safe})

@app.route('/', methods=['GET'])
def web_ui():
    return send_from_directory('data/web_ui', 'index.html')

@app.route('/<path:path>', methods=['GET'])
def serve_static(path):
    if os.path.exists(os.path.join('data/web_ui', path)):
        return send_from_directory('data/web_ui', path)
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(404)
def not_found(e):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"Internal error: {e}")
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.start_time = time.time()
    os.makedirs('data/web_ui', exist_ok=True)
    os.makedirs('data/downloads', exist_ok=True)
    os.makedirs('data/cache', exist_ok=True)
    os.makedirs(config.ADDON_STORAGE_DIR, exist_ok=True)
    self_pinger.start()
    sleep_manager.start()
    news_manager.start_updater()
    logger.info(f"AEGIS Knowledge Engine starting on port {config.PORT}")
    app.run(host=config.HOST, port=config.PORT, debug=config.DEBUG, threaded=True)
