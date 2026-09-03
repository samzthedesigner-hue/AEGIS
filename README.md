# AEGIS Knowledge Engine

A full-featured search engine backend that combines web crawling, meta-search aggregation, and Android database integration. Built to run on Render's free tier with self-pinging to stay alive.

## Features

### Search
- **30+ Sources** - Aggregates results from Wikipedia, Stack Overflow, GitHub, Arxiv, PubMed, and more
- **No API Keys Required** - All sources are free and open
- **Meta-Search** - Combines results from multiple search engines
- **Ranking** - Custom relevance scoring algorithm
- **Autocomplete** - Search suggestions from multiple sources
- **Type Filtering** - General, programming, academic, books, news, social, education

### Web Crawling
- **Robots.txt Compliance** - Respects crawl rules
- **Rate Limiting** - Built-in delay between requests
- **Content Extraction** - Parses HTML, JSON, and text
- **Link Discovery** - Finds and follows links
- **Metadata Extraction** - Title, description, images, etc.

### Downloads
- **File Types** - Images, videos, audio, documents, archives
- **Resumable** - Pause, resume, and cancel
- **Progress Tracking** - Real-time download status
- **Safe Browsing** - Blocks malicious URLs

### News Feed
- **Multiple Sources** - BBC, Reuters, AP, NPR, The Guardian
- **Categories** - General, technology, science, programming, academic
- **Auto-Refresh** - Updates every 15 minutes
- **Trending Topics** - Aggregated from all sources

### Authentication
- **Google OAuth** - Sign in with Google
- **No Google Branding** - Clean, neutral UI
- **Session Management** - Token-based auth

### Add-on System
- **Built-in Add-ons** - Ad blocker, dark mode, video downloader, reader mode, screenshot
- **Repository** - Install additional add-ons
- **Permissions** - Granular access control
- **Toggle** - Enable/disable per add-on

### Privacy & Security
- **Incognito Mode** - No history, cookies, or cache
- **Rate Limiting** - Prevents abuse
- **Safe Browsing** - Blocks known malicious domains
- **Caching** - TTL-based cache for faster results

### Android Integration
- **ContentProvider Relay** - Sends all data to Android database
- **Search Logging** - Records queries and results
- **Crawl Storage** - Stores crawled content
- **Download Logging** - Tracks download activity
- **Auth Events** - Logs login/logout

### Self-Management
- **Self-Pinging** - Keeps Render alive every 10 minutes
- **Sleep Mode** - Enters sleep after 30 minutes of inactivity
- **Wake on Request** - Automatically wakes when client connects
- **Heartbeat** - Clients send heartbeat every 30 seconds

## API Endpoints

### Health & Client Management
- `GET /api/health` - Server health status
- `POST /api/register` - Register a client
- `POST /api/heartbeat` - Client heartbeat
- `POST /api/disconnect` - Client disconnect

### Search
- `GET /api/search?q=query&type=all&page=1&limit=20` - Main search
- `GET /api/autocomplete?q=query` - Search suggestions
- `GET /api/search/images?q=query` - Image search
- `GET /api/search/videos?q=query` - Video search
- `GET /api/search/news?q=query` - News search
- `GET /api/search/academic?q=query` - Academic search

### Crawling
- `POST /api/crawl` - Crawl a single URL
- `POST /api/crawl/topic` - Crawl a topic

### Downloads
- `POST /api/download` - Start a download
- `GET /api/download/{id}` - Download status
- `POST /api/download/{id}/pause` - Pause download
- `POST /api/download/{id}/resume` - Resume download
- `POST /api/download/{id}/cancel` - Cancel download
- `GET /api/download/{id}/file` - Get downloaded file

### News
- `GET /api/news?category=all&limit=20` - News feed
- `GET /api/news/trending` - Trending topics

### Auth
- `GET /api/auth/google/login` - Google OAuth login
- `GET /api/auth/google/callback` - OAuth callback
- `POST /api/auth/logout` - Logout

### Add-ons
- `GET /api/addons/list` - Installed add-ons
- `GET /api/addons/repository` - Available add-ons
- `POST /api/addons/install` - Install add-on
- `POST /api/addons/uninstall` - Uninstall add-on
- `POST /api/addons/toggle` - Enable/disable add-on
- `POST /api/addons/execute` - Execute add-on script

### Relay
- `POST /api/relay/sync` - Sync data to Android
- `GET /api/relay/status` - Relay status
- `GET /api/relay/pending` - Pending operations
- `POST /api/relay/clear` - Clear synced operations

### Cache
- `POST /api/cache/clear` - Clear cache
- `GET /api/cache/stats` - Cache statistics

### Privacy
- `POST /api/privacy/incognito` - Toggle incognito
- `POST /api/privacy/clear-data` - Clear privacy data

### Security
- `POST /api/security/check-url` - Check URL safety

## Deployment to Render

1. Push this repository to GitHub
2. Go to [Render](https://render.com)
3. Click "New Web Service"
4. Connect your GitHub repository
5. Configure:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn server:app --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120`
6. Set environment variables:
   - `RENDER_EXTERNAL_URL` - Your Render URL (e.g., https://your-app.onrender.com)
   - `SECRET_KEY` - A random secret key
   - `GOOGLE_CLIENT_ID` - Google OAuth client ID (optional)
   - `GOOGLE_CLIENT_SECRET` - Google OAuth client secret (optional)
7. Deploy!

## Architecture
Web Browser → Render Backend → Meta-Search (30+ APIs)
↓
Relay Manager → Android ContentProvider → SQLite
↓
Cache Manager (TTL-based)
↓
Sleep Manager (Self-pinging)

```

## Configuration

All configuration is in `config.py`. Key settings:

- `PING_INTERVAL` - Self-ping interval (default: 600 seconds)
- `SLEEP_TIMEOUT` - Sleep after inactivity (default: 1800 seconds)
- `CRAWLER_DELAY` - Delay between crawl requests (default: 2 seconds)
- `CACHE_TTL` - Cache time-to-live (default: 3600 seconds)
- `MAX_RESULTS` - Maximum search results (default: 50)
- `SEARCH_TIMEOUT` - Search timeout (default: 15 seconds)

## Search Sources (30+)

### General
- DuckDuckGo HTML
- SearXNG (public instances)
- Mojeek
- Wikipedia
- Wikidata
- Internet Archive

### Programming
- Stack Overflow
- GitHub
- Hacker News
- Dev.to
- NPM
- PyPI
- Maven Central
- Docker Hub

### Academic
- Arxiv
- PubMed
- Semantic Scholar
- Crossref
- OpenAlex
- DOAJ
- CORE
- Paperity
- BASE

### Books
- OpenLibrary
- Project Gutenberg
- Google Books

### Social
- Reddit
- Lobste.rs
- Mastodon

### News
- GDELT Project
- RSS Feeds (BBC, Reuters, AP, NPR, etc.)

### Education
- Khan Academy
- Coursera
- edX

## License

MIT License - Free to use, modify, and distribute.
```
