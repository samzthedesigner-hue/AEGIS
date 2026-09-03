import os

class Config:
    PORT = int(os.environ.get('PORT', 10000))
    HOST = '0.0.0.0'
    DEBUG = False
    SECRET_KEY = os.environ.get('SECRET_KEY', 'aegis-knowledge-engine-secret-key-2024')
    
    RENDER_URL = os.environ.get('RENDER_EXTERNAL_URL', 'http://localhost:10000')
    
    PING_INTERVAL = 600
    SLEEP_TIMEOUT = 1800
    HEARTBEAT_INTERVAL = 30
    
    ANDROID_AUTHORITY = "com.aegis.knowledgeengine.provider"
    ANDROID_CATCHES_URI = f"content://{ANDROID_AUTHORITY}/catches"
    ANDROID_TOPICS_URI = f"content://{ANDROID_AUTHORITY}/topics"
    
    CRAWLER_USER_AGENT = 'AEGISKnowledgeBot/1.0 (compatible; +https://aegis-knowledge.onrender.com)'
    CRAWLER_DELAY = 2
    MAX_CRAWL_DEPTH = 3
    MAX_PAGES_PER_DOMAIN = 50
    RESPECT_ROBOTS_TXT = True
    MAX_CRAWL_TIMEOUT = 15
    
    CACHE_TTL = 3600
    CACHE_MAX_SIZE = 1000
    
    MAX_DOWNLOAD_SIZE = 500 * 1024 * 1024
    DOWNLOAD_CHUNK_SIZE = 8192
    ALLOWED_DOWNLOAD_TYPES = [
        'image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/svg+xml',
        'video/mp4', 'video/webm', 'video/avi', 'video/mkv', 'video/quicktime',
        'application/pdf', 'application/zip', 'application/x-tar', 'application/gzip',
        'text/plain', 'text/html', 'application/json', 'application/xml',
        'audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/flac',
        'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'application/vnd.ms-excel', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-powerpoint', 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'application/epub+zip', 'application/x-mobipocket-ebook'
    ]
    
    NEWS_REFRESH_INTERVAL = 900
    NEWS_SOURCES = {
        'general': [
            'https://feeds.bbci.co.uk/news/rss.xml',
            'https://feeds.reuters.com/reuters/topNews',
            'https://apnews.com/rss',
            'https://www.aljazeera.com/xml/rss/all.xml',
            'https://feeds.npr.org/1001/rss.xml',
            'https://www.theguardian.com/world/rss'
        ],
        'technology': [
            'https://feeds.arstechnica.com/arstechnica/index',
            'https://www.theverge.com/rss/index.xml',
            'https://techcrunch.com/feed/',
            'https://www.wired.com/feed/rss',
            'https://hnrss.org/frontpage',
            'https://lobste.rs/rss'
        ],
        'science': [
            'https://www.sciencedaily.com/rss/all.xml',
            'https://www.nature.com/nature.rss',
            'https://www.sciencemag.org/rss/news_current.xml',
            'https://feeds.newscientist.com/science'
        ],
        'programming': [
            'https://dev.to/feed',
            'https://www.freecodecamp.org/news/rss',
            'https://github.blog/feed/',
            'https://stackoverflow.blog/feed/'
        ],
        'academic': [
            'https://export.arxiv.org/rss/cs',
            'https://export.arxiv.org/rss/physics',
            'https://export.arxiv.org/rss/math',
            'https://export.arxiv.org/rss/q-bio'
        ]
    }
    
    SEARCH_SOURCES = {
        'general': ['duckduckgo_html', 'searxng', 'mojeek', 'wikipedia', 'wikidata', 'internet_archive'],
        'programming': ['stackoverflow', 'github', 'hackernews', 'devto', 'npm', 'pypi', 'maven', 'dockerhub'],
        'academic': ['arxiv', 'pubmed', 'semantic_scholar', 'crossref', 'openalex', 'doaj', 'core', 'paperity', 'base'],
        'books': ['openlibrary', 'gutenberg', 'google_books'],
        'social': ['reddit', 'lobsters', 'mastodon'],
        'news': ['gdelft', 'rss_feeds'],
        'education': ['khanacademy', 'coursera_public', 'edx_public']
    }
    
    GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
    GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
    GOOGLE_REDIRECT_URI = os.environ.get('GOOGLE_REDIRECT_URI', '')
    
    ADDON_STORAGE_DIR = '/tmp/addons'
    ADDON_MAX_SIZE = 10 * 1024 * 1024
    
    SAFE_BROWSING_ENABLED = True
    MAX_REQUESTS_PER_MINUTE = 120
    RATE_LIMIT_ENABLED = True
    
    MAX_RESULTS = 50
    SEARCH_TIMEOUT = 15
    AUTOCOMPLETE_LIMIT = 10
    MAX_CONCURRENT_SEARCHES = 15
