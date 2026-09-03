import logging
import json
import re
import requests
from typing import Dict, List, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import quote
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

class MetaSearchEngine:
    def __init__(self, config):
        self.config = config
        self.timeout = config.SEARCH_TIMEOUT
        self.user_agent = config.CRAWLER_USER_AGENT
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'application/json, text/html, application/xhtml+xml',
            'Accept-Language': 'en-US,en;q=0.9'
        })

    def search(self, query: str, limit: int = 20, search_type: str = 'all') -> List[Dict]:
        all_results = []
        sources = self._get_sources_for_type(search_type)
        with ThreadPoolExecutor(max_workers=self.config.MAX_CONCURRENT_SEARCHES) as executor:
            futures = {}
            for source_name in sources:
                method = getattr(self, f'_search_{source_name}', None)
                if method:
                    future = executor.submit(method, query, limit)
                    futures[future] = source_name
            for future in as_completed(futures, timeout=self.timeout):
                source_name = futures[future]
                try:
                    results = future.result()
                    if results:
                        all_results.extend(results)
                except Exception as e:
                    logger.warning(f"Source '{source_name}' failed: {e}")
        seen_urls: Set[str] = set()
        deduplicated = []
        for result in all_results:
            url = result.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                deduplicated.append(result)
        return deduplicated[:limit]

    def _get_sources_for_type(self, search_type: str) -> List[str]:
        if search_type == 'all':
            sources = []
            for source_list in self.config.SEARCH_SOURCES.values():
                sources.extend(source_list)
            return sources[:20]
        return self.config.SEARCH_SOURCES.get(search_type, self.config.SEARCH_SOURCES['general'])

    def _search_duckduckgo_html(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for result in soup.select('.result')[:limit]:
                title_elem = result.select_one('.result__title')
                link_elem = result.select_one('.result__url')
                snippet_elem = result.select_one('.result__snippet')
                if title_elem and link_elem:
                    title = title_elem.get_text(strip=True)
                    link = link_elem.get('href', '')
                    if link.startswith('//'):
                        link = 'https:' + link
                    if 'uddg=' in link:
                        link = re.search(r'uddg=([^&]+)', link).group(1)
                        link = requests.utils.unquote(link)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ''
                    results.append({'title': title, 'url': link, 'snippet': snippet[:300], 'source': 'duckduckgo', 'type': 'web'})
        except Exception as e:
            logger.debug(f"DuckDuckGo failed: {e}")
        return results

    def _search_searxng(self, query: str, limit: int) -> List[Dict]:
        results = []
        instances = ['https://searx.be', 'https://searx.tiekoetter.com', 'https://searx.fmac.xyz']
        for instance in instances:
            try:
                url = f"{instance}/search?q={quote(query)}&format=json"
                response = self.session.get(url, timeout=self.timeout)
                data = response.json()
                for item in data.get('results', [])[:limit]:
                    results.append({'title': item.get('title', ''), 'url': item.get('url', ''), 'snippet': item.get('content', '')[:300], 'source': 'searxng', 'type': 'web'})
                if results:
                    break
            except Exception as e:
                logger.debug(f"SearXNG {instance} failed: {e}")
        return results

    def _search_mojeek(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.mojeek.com/search?q={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for result in soup.select('.results-standard li')[:limit]:
                title_elem = result.select_one('h2 a')
                snippet_elem = result.select_one('.s')
                if title_elem:
                    results.append({'title': title_elem.get_text(strip=True), 'url': title_elem.get('href', ''), 'snippet': snippet_elem.get_text(strip=True)[:300] if snippet_elem else '', 'source': 'mojeek', 'type': 'web'})
        except Exception as e:
            logger.debug(f"Mojeek failed: {e}")
        return results

    def _search_wikipedia(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {'action': 'query', 'list': 'search', 'srsearch': query, 'format': 'json', 'srlimit': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            data = response.json()
            for item in data.get('query', {}).get('search', []):
                page_url = f"https://en.wikipedia.org/wiki/{quote(item['title'].replace(' ', '_'))}"
                results.append({'title': item['title'], 'url': page_url, 'snippet': item.get('snippet', '').replace('<span class="searchmatch">', '').replace('</span>', '')[:300], 'source': 'wikipedia', 'type': 'encyclopedia'})
        except Exception as e:
            logger.debug(f"Wikipedia failed: {e}")
        return results

    def _search_wikidata(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://www.wikidata.org/w/api.php"
            params = {'action': 'wbsearchentities', 'search': query, 'language': 'en', 'format': 'json', 'limit': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            data = response.json()
            for item in data.get('search', []):
                results.append({'title': item.get('label', ''), 'url': f"https://www.wikidata.org/wiki/{item.get('id', '')}", 'snippet': item.get('description', ''), 'source': 'wikidata', 'type': 'knowledge_graph'})
        except Exception as e:
            logger.debug(f"Wikidata failed: {e}")
        return results

    def _search_internet_archive(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://archive.org/advancedsearch.php?q={quote(query)}&fl[]=identifier&fl[]=title&fl[]=description&rows={limit}&output=json"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for doc in data.get('response', {}).get('docs', []):
                identifier = doc.get('identifier', '')
                results.append({'title': doc.get('title', identifier), 'url': f"https://archive.org/details/{identifier}", 'snippet': doc.get('description', '')[:300], 'source': 'internet_archive', 'type': 'archive'})
        except Exception as e:
            logger.debug(f"Internet Archive failed: {e}")
        return results

    def _search_stackoverflow(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://api.stackexchange.com/2.3/search/advanced"
            params = {'order': 'desc', 'sort': 'relevance', 'q': query, 'site': 'stackoverflow', 'pagesize': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            data = response.json()
            for item in data.get('items', []):
                results.append({'title': item.get('title', ''), 'url': item.get('link', ''), 'snippet': re.sub(r'<[^>]+>', '', item.get('excerpt', ''))[:300], 'source': 'stackoverflow', 'type': 'programming', 'metadata': {'score': item.get('score', 0), 'answered': item.get('is_answered', False), 'tags': item.get('tags', [])}})
        except Exception as e:
            logger.debug(f"StackOverflow failed: {e}")
        return results

    def _search_github(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://api.github.com/search/repositories"
            params = {'q': query, 'per_page': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            data = response.json()
            for item in data.get('items', []):
                results.append({'title': item.get('full_name', ''), 'url': item.get('html_url', ''), 'snippet': item.get('description', '') or '', 'source': 'github', 'type': 'code_repository', 'metadata': {'stars': item.get('stargazers_count', 0), 'language': item.get('language', ''), 'forks': item.get('forks_count', 0)}})
        except Exception as e:
            logger.debug(f"GitHub failed: {e}")
        return results

    def _search_hackernews(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://hn.algolia.com/api/v1/search?query={quote(query)}&hitsPerPage={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for hit in data.get('hits', []):
                hn_url = f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"
                results.append({'title': hit.get('title', '') or hit.get('story_title', ''), 'url': hit.get('url', hn_url), 'snippet': (hit.get('story_text', '') or hit.get('comment_text', ''))[:300], 'source': 'hackernews', 'type': 'tech_news', 'metadata': {'points': hit.get('points', 0), 'author': hit.get('author', ''), 'comments': hit.get('num_comments', 0)}})
        except Exception as e:
            logger.debug(f"HackerNews failed: {e}")
        return results

    def _search_devto(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://dev.to/api/articles"
            params = {'tag': query, 'per_page': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            articles = response.json()
            for article in articles:
                results.append({'title': article.get('title', ''), 'url': article.get('url', ''), 'snippet': article.get('description', '')[:300], 'source': 'devto', 'type': 'blog', 'metadata': {'author': article.get('user', {}).get('name', ''), 'tags': article.get('tags', ''), 'reactions': article.get('positive_reactions_count', 0)}})
        except Exception as e:
            logger.debug(f"Dev.to failed: {e}")
        return results

    def _search_npm(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://registry.npmjs.org/-/v1/search?text={quote(query)}&size={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for obj in data.get('objects', []):
                package = obj.get('package', {})
                results.append({'title': package.get('name', ''), 'url': f"https://www.npmjs.com/package/{package.get('name', '')}", 'snippet': package.get('description', '')[:300], 'source': 'npm', 'type': 'package', 'metadata': {'version': package.get('version', ''), 'weekly_downloads': obj.get('downloads', {}).get('weekly', 0)}})
        except Exception as e:
            logger.debug(f"NPM failed: {e}")
        return results

    def _search_pypi(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://pypi.org/pypi/{quote(query)}/json"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            info = data.get('info', {})
            results.append({'title': info.get('name', query), 'url': info.get('package_url', f"https://pypi.org/project/{quote(query)}/"), 'snippet': info.get('summary', '')[:300], 'source': 'pypi', 'type': 'package', 'metadata': {'version': info.get('version', ''), 'author': info.get('author', ''), 'license': info.get('license', '')}})
        except Exception as e:
            logger.debug(f"PyPI failed: {e}")
        return results

    def _search_maven(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://search.maven.org/solrsearch/select?q={quote(query)}&rows={limit}&wt=json"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for doc in data.get('response', {}).get('docs', []):
                results.append({'title': f"{doc.get('g', '')}:{doc.get('a', '')}", 'url': f"https://search.maven.org/artifact/{doc.get('g', '')}/{doc.get('a', '')}", 'snippet': f"Maven artifact version {doc.get('latestVersion', '')}", 'source': 'maven', 'type': 'package', 'metadata': {'group': doc.get('g', ''), 'artifact': doc.get('a', ''), 'version': doc.get('latestVersion', '')}})
        except Exception as e:
            logger.debug(f"Maven failed: {e}")
        return results

    def _search_dockerhub(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://hub.docker.com/v2/search/repositories/?query={quote(query)}&page_size={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for repo in data.get('results', []):
                results.append({'title': repo.get('repo_name', ''), 'url': f"https://hub.docker.com/r/{repo.get('repo_name', '')}", 'snippet': repo.get('short_description', '')[:300], 'source': 'dockerhub', 'type': 'container', 'metadata': {'stars': repo.get('star_count', 0), 'pulls': repo.get('pull_count', 0)}})
        except Exception as e:
            logger.debug(f"DockerHub failed: {e}")
        return results

    def _search_arxiv(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://export.arxiv.org/api/query?search_query=all:{quote(query)}&max_results={limit}"
            response = self.session.get(url, timeout=self.timeout)
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title = entry.find('atom:title', ns).text.strip().replace('\n', ' ')
                summary = entry.find('atom:summary', ns).text.strip()[:300]
                link = entry.find('atom:id', ns).text
                authors = [a.find('atom:name', ns).text for a in entry.findall('atom:author', ns)]
                results.append({'title': title, 'url': link, 'snippet': summary, 'source': 'arxiv', 'type': 'academic_paper', 'metadata': {'authors': authors[:5], 'published': entry.find('atom:published', ns).text}})
        except Exception as e:
            logger.debug(f"Arxiv failed: {e}")
        return results

    def _search_pubmed(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            search_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term={quote(query)}&retmax={limit}&retmode=json"
            response = self.session.get(search_url, timeout=self.timeout)
            data = response.json()
            ids = data.get('esearchresult', {}).get('idlist', [])
            if ids:
                fetch_url = f"https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id={','.join(ids)}&retmode=json"
                fetch_response = self.session.get(fetch_url, timeout=self.timeout)
                fetch_data = fetch_response.json()
                for pmid in ids:
                    article = fetch_data.get('result', {}).get(pmid, {})
                    results.append({'title': article.get('title', f'PubMed {pmid}'), 'url': f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/", 'snippet': article.get('pubdate', ''), 'source': 'pubmed', 'type': 'academic_paper', 'metadata': {'pmid': pmid, 'authors': [a.get('name', '') for a in article.get('authors', [])][:5]}})
        except Exception as e:
            logger.debug(f"PubMed failed: {e}")
        return results

    def _search_semantic_scholar(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={quote(query)}&limit={limit}&fields=title,abstract,url,authors,year,citationCount"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for paper in data.get('data', []):
                results.append({'title': paper.get('title', ''), 'url': paper.get('url', ''), 'snippet': (paper.get('abstract') or '')[:300], 'source': 'semantic_scholar', 'type': 'academic_paper', 'metadata': {'authors': [a.get('name', '') for a in paper.get('authors', [])][:5], 'year': paper.get('year', ''), 'citations': paper.get('citationCount', 0)}})
        except Exception as e:
            logger.debug(f"Semantic Scholar failed: {e}")
        return results

    def _search_crossref(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://api.crossref.org/works?query={quote(query)}&rows={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for item in data.get('message', {}).get('items', []):
                title = item.get('title', [''])[0] if item.get('title') else ''
                doi = item.get('DOI', '')
                results.append({'title': title, 'url': f"https://doi.org/{doi}" if doi else '', 'snippet': (item.get('abstract', '') or '')[:300], 'source': 'crossref', 'type': 'academic_paper', 'metadata': {'doi': doi, 'publisher': item.get('publisher', ''), 'year': item.get('published', {}).get('date-parts', [['']])[0][0]}})
        except Exception as e:
            logger.debug(f"Crossref failed: {e}")
        return results

    def _search_openalex(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://api.openalex.org/works?search={quote(query)}&per-page={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for work in data.get('results', []):
                results.append({'title': work.get('title', ''), 'url': work.get('doi') or work.get('id', ''), 'snippet': '', 'source': 'openalex', 'type': 'academic_paper', 'metadata': {'authors': [a.get('author', {}).get('display_name', '') for a in work.get('authorships', [])][:5], 'year': work.get('publication_year', ''), 'citations': work.get('cited_by_count', 0)}})
        except Exception as e:
            logger.debug(f"OpenAlex failed: {e}")
        return results

    def _search_doaj(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://doaj.org/api/search/articles/{quote(query)}?pageSize={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for article in data.get('results', []):
                bibjson = article.get('bibjson', {})
                title = bibjson.get('title', '')
                results.append({'title': title, 'url': bibjson.get('link', [{}])[0].get('url', '') if bibjson.get('link') else '', 'snippet': (bibjson.get('abstract', '') or '')[:300], 'source': 'doaj', 'type': 'academic_paper', 'metadata': {'journal': bibjson.get('journal', {}).get('title', ''), 'authors': [a.get('name', '') for a in bibjson.get('author', [])][:5]}})
        except Exception as e:
            logger.debug(f"DOAJ failed: {e}")
        return results

    def _search_core(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://api.core.ac.uk/v3/search/works?q={quote(query)}&limit={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for work in data.get('results', []):
                results.append({'title': work.get('title', ''), 'url': work.get('downloadUrl', work.get('sourceUrl', '')), 'snippet': (work.get('abstract', '') or '')[:300], 'source': 'core', 'type': 'academic_paper', 'metadata': {'authors': [a.get('name', '') for a in work.get('authors', [])][:5], 'year': work.get('yearPublished', '')}})
        except Exception as e:
            logger.debug(f"CORE failed: {e}")
        return results

    def _search_paperity(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://paperity.org/search/?q={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for article in soup.select('.paper-item')[:limit]:
                title_elem = article.select_one('h2 a, h3 a')
                link_elem = article.select_one('a[href*="/p/"]')
                if title_elem:
                    results.append({'title': title_elem.get_text(strip=True), 'url': f"https://paperity.org{link_elem.get('href', '')}" if link_elem else '', 'snippet': article.select_one('.paper-abstract').get_text(strip=True)[:300] if article.select_one('.paper-abstract') else '', 'source': 'paperity', 'type': 'academic_paper'})
        except Exception as e:
            logger.debug(f"Paperity failed: {e}")
        return results

    def _search_base(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.base-search.net/Search/Results?lookfor={quote(query)}&type=all"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for result in soup.select('.result-item')[:limit]:
                title_elem = result.select_one('h3 a, .title a')
                if title_elem:
                    results.append({'title': title_elem.get_text(strip=True), 'url': title_elem.get('href', ''), 'snippet': result.select_one('.result-description, .abstract').get_text(strip=True)[:300] if result.select_one('.result-description, .abstract') else '', 'source': 'base', 'type': 'academic_paper'})
        except Exception as e:
            logger.debug(f"BASE failed: {e}")
        return results

    def _search_openlibrary(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://openlibrary.org/search.json?q={quote(query)}&limit={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for doc in data.get('docs', []):
                title = doc.get('title', '')
                author = doc.get('author_name', [''])[0] if doc.get('author_name') else ''
                results.append({'title': f"{title} - {author}" if author else title, 'url': f"https://openlibrary.org{doc.get('key', '')}", 'snippet': f"Published {doc.get('first_publish_year', 'unknown')}", 'source': 'openlibrary', 'type': 'book', 'metadata': {'author': author, 'year': doc.get('first_publish_year', ''), 'pages': doc.get('number_of_pages_median', '')}})
        except Exception as e:
            logger.debug(f"OpenLibrary failed: {e}")
        return results

    def _search_gutenberg(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://gutendex.com/books?search={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for book in data.get('results', [])[:limit]:
                title = book.get('title', '')
                results.append({'title': title, 'url': f"https://www.gutenberg.org/ebooks/{book.get('id', '')}", 'snippet': f"Author: {', '.join(a.get('name', '') for a in book.get('authors', []))}", 'source': 'gutenberg', 'type': 'book', 'metadata': {'id': book.get('id', ''), 'authors': [a.get('name', '') for a in book.get('authors', [])], 'downloads': book.get('download_count', 0)}})
        except Exception as e:
            logger.debug(f"Gutenberg failed: {e}")
        return results

    def _search_google_books(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.googleapis.com/books/v1/volumes?q={quote(query)}&maxResults={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for item in data.get('items', []):
                info = item.get('volumeInfo', {})
                title = info.get('title', '')
                results.append({'title': title, 'url': info.get('infoLink', ''), 'snippet': (info.get('description', '') or '')[:300], 'source': 'google_books', 'type': 'book', 'metadata': {'authors': info.get('authors', []), 'publisher': info.get('publisher', ''), 'year': info.get('publishedDate', '')}})
        except Exception as e:
            logger.debug(f"Google Books failed: {e}")
        return results

    def _search_reddit(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.reddit.com/search.json?q={quote(query)}&limit={limit}"
            headers = {'User-Agent': self.user_agent}
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            data = response.json()
            for child in data.get('data', {}).get('children', []):
                post = child.get('data', {})
                results.append({'title': post.get('title', ''), 'url': f"https://www.reddit.com{post.get('permalink', '')}", 'snippet': post.get('selftext', '')[:300], 'source': 'reddit', 'type': 'social', 'metadata': {'subreddit': post.get('subreddit', ''), 'score': post.get('score', 0), 'comments': post.get('num_comments', 0)}})
        except Exception as e:
            logger.debug(f"Reddit failed: {e}")
        return results

    def _search_lobsters(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://lobste.rs/search.json?q={quote(query)}&what=stories&order=relevance"
            response = self.session.get(url, timeout=self.timeout)
            stories = response.json()
            for story in stories[:limit]:
                results.append({'title': story.get('title', ''), 'url': story.get('url', f"https://lobste.rs/s/{story.get('short_id', '')}"), 'snippet': story.get('description', '')[:300], 'source': 'lobsters', 'type': 'tech_news', 'metadata': {'score': story.get('score', 0), 'comments': story.get('comment_count', 0), 'tags': story.get('tags', [])}})
        except Exception as e:
            logger.debug(f"Lobste.rs failed: {e}")
        return results

    def _search_mastodon(self, query: str, limit: int) -> List[Dict]:
        results = []
        instances = ['mastodon.social', 'mstdn.social', 'fosstodon.org']
        for instance in instances:
            try:
                url = f"https://{instance}/api/v2/search?q={quote(query)}&type=statuses&limit={limit}"
                response = self.session.get(url, timeout=self.timeout)
                data = response.json()
                for status in data.get('statuses', []):
                    account = status.get('account', {})
                    results.append({'title': account.get('display_name', ''), 'url': status.get('url', ''), 'snippet': re.sub(r'<[^>]+>', '', status.get('content', ''))[:300], 'source': 'mastodon', 'type': 'social', 'metadata': {'username': account.get('username', ''), 'followers': account.get('followers_count', 0)}})
                if results:
                    break
            except Exception as e:
                logger.debug(f"Mastodon {instance} failed: {e}")
        return results

    def _search_gdelft(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://api.gdeltproject.org/api/v2/doc/doc?query={quote(query)}&mode=artlist&maxrecords={limit}&format=json"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for article in data.get('articles', []):
                results.append({'title': article.get('title', ''), 'url': article.get('url', ''), 'snippet': article.get('seendate', ''), 'source': 'gdelft', 'type': 'news', 'metadata': {'domain': article.get('domain', ''), 'language': article.get('language', ''), 'socialimage': article.get('socialimage', '')}})
        except Exception as e:
            logger.debug(f"GDELFT failed: {e}")
        return results

    def _search_rss_feeds(self, query: str, limit: int) -> List[Dict]:
        results = []
        import feedparser
        for category, feeds in self.config.NEWS_SOURCES.items():
            for feed_url in feeds[:5]:
                try:
                    feed = feedparser.parse(feed_url)
                    for entry in feed.entries[:5]:
                        if query.lower() in entry.get('title', '').lower() or query.lower() in entry.get('summary', '').lower():
                            results.append({'title': entry.get('title', ''), 'url': entry.get('link', ''), 'snippet': entry.get('summary', '')[:300], 'source': 'rss', 'type': 'news', 'metadata': {'published': entry.get('published', ''), 'feed': feed_url}})
                except Exception as e:
                    logger.debug(f"RSS {feed_url} failed: {e}")
        return results[:limit]

    def _search_khanacademy(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.khanacademy.org/api/internal/search/scratchpads?query={quote(query)}&limit={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for item in data.get('scratchpads', []):
                results.append({'title': item.get('title', ''), 'url': f"https://www.khanacademy.org/{item.get('url', '')}", 'snippet': item.get('description', '')[:300], 'source': 'khanacademy', 'type': 'education'})
        except Exception as e:
            logger.debug(f"Khan Academy failed: {e}")
        return results

    def _search_coursera_public(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.coursera.org/search?query={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for course in soup.select('.card-container')[:limit]:
                title_elem = course.select_one('h2, h3')
                link_elem = course.select_one('a[href*="/learn/"]')
                if title_elem and link_elem:
                    results.append({'title': title_elem.get_text(strip=True), 'url': f"https://www.coursera.org{link_elem.get('href', '')}", 'snippet': course.select_one('.description').get_text(strip=True)[:300] if course.select_one('.description') else '', 'source': 'coursera', 'type': 'education'})
        except Exception as e:
            logger.debug(f"Coursera failed: {e}")
        return results

    def _search_edx_public(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://www.edx.org/search?q={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            soup = BeautifulSoup(response.text, 'lxml')
            for course in soup.select('.course-card')[:limit]:
                title_elem = course.select_one('h2, h3, .course-title')
                link_elem = course.select_one('a[href*="/course/"]')
                if title_elem and link_elem:
                    results.append({'title': title_elem.get_text(strip=True), 'url': f"https://www.edx.org{link_elem.get('href', '')}", 'snippet': course.select_one('.course-description').get_text(strip=True)[:300] if course.select_one('.course-description') else '', 'source': 'edx', 'type': 'education'})
        except Exception as e:
            logger.debug(f"edX failed: {e}")
        return results

    def search_images(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = "https://commons.wikimedia.org/w/api.php"
            params = {'action': 'query', 'list': 'search', 'srsearch': query, 'srnamespace': '6', 'format': 'json', 'srlimit': limit}
            response = self.session.get(url, params=params, timeout=self.timeout)
            data = response.json()
            for item in data.get('query', {}).get('search', []):
                image_url = f"https://commons.wikimedia.org/wiki/Special:FilePath/{quote(item['title'].replace('File:', ''))}"
                results.append({'title': item['title'].replace('File:', ''), 'url': image_url, 'thumbnail': image_url, 'source': 'wikimedia_commons', 'type': 'image'})
        except Exception as e:
            logger.debug(f"Wikimedia images failed: {e}")
        try:
            url = f"https://openlibrary.org/search.json?q={quote(query)}&limit={limit}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for doc in data.get('docs', []):
                if doc.get('cover_i'):
                    cover_url = f"https://covers.openlibrary.org/b/id/{doc['cover_i']}-L.jpg"
                    results.append({'title': doc.get('title', ''), 'url': cover_url, 'thumbnail': cover_url, 'source': 'openlibrary_cover', 'type': 'image'})
        except Exception as e:
            logger.debug(f"OpenLibrary covers failed: {e}")
        try:
            url = f"https://gutendex.com/books?search={quote(query)}"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for book in data.get('results', [])[:limit]:
                if book.get('formats', {}).get('image/jpeg'):
                    results.append({'title': book.get('title', ''), 'url': book['formats']['image/jpeg'], 'thumbnail': book['formats']['image/jpeg'], 'source': 'gutenberg_cover', 'type': 'image'})
        except Exception as e:
            logger.debug(f"Gutenberg covers failed: {e}")
        return results[:limit]

    def search_videos(self, query: str, limit: int) -> List[Dict]:
        results = []
        try:
            url = f"https://archive.org/advancedsearch.php?q={quote(query)}+AND+mediatype:(movies)&fl[]=identifier&fl[]=title&fl[]=description&rows={limit}&output=json"
            response = self.session.get(url, timeout=self.timeout)
            data = response.json()
            for doc in data.get('response', {}).get('docs', []):
                identifier = doc.get('identifier', '')
                results.append({'title': doc.get('title', identifier), 'url': f"https://archive.org/download/{identifier}", 'thumbnail': f"https://archive.org/services/img/{identifier}", 'snippet': doc.get('description', '')[:300], 'source': 'internet_archive_video', 'type': 'video'})
        except Exception as e:
            logger.debug(f"Internet Archive videos failed: {e}")
        return results[:limit]

    def search_news(self, query: str, limit: int) -> List[Dict]:
        return self.search(query, limit, 'news')

    def search_academic(self, query: str, limit: int) -> List[Dict]:
        return self.search(query, limit, 'academic')

    def get_suggestions(self, query: str, limit: int) -> List[str]:
        suggestions = []
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {'action': 'opensearch', 'search': query, 'limit': limit, 'format': 'json'}
            response = self.session.get(url, params=params, timeout=5)
            data = response.json()
            suggestions.extend(data[1] if len(data) > 1 else [])
        except:
            pass
        try:
            url = f"https://duckduckgo.com/ac/?q={quote(query)}&type=list"
            response = self.session.get(url, timeout=5)
            data = response.json()
            suggestions.extend([item.get('phrase', '') for item in data if item.get('phrase')])
        except:
            pass
        seen = set()
        unique_suggestions = []
        for s in suggestions:
            if s.lower() not in seen:
                seen.add(s.lower())
                unique_suggestions.append(s)
        return unique_suggestions[:limit]
