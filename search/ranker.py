import re
import math
from typing import Dict, List

class ResultRanker:
    def __init__(self):
        self.source_weights = {
            'wikipedia': 0.9, 'arxiv': 0.85, 'pubmed': 0.85,
            'semantic_scholar': 0.85, 'crossref': 0.85, 'openalex': 0.85,
            'doaj': 0.85, 'core': 0.85, 'stackoverflow': 0.8,
            'github': 0.8, 'duckduckgo': 0.75, 'searxng': 0.75,
            'mojeek': 0.75, 'hackernews': 0.7, 'reddit': 0.65,
            'devto': 0.65, 'openlibrary': 0.7, 'gutenberg': 0.7,
            'internet_archive': 0.65, 'gdelft': 0.6, 'rss': 0.55,
            'npm': 0.6, 'pypi': 0.6, 'maven': 0.6, 'dockerhub': 0.6,
            'wikidata': 0.7, 'google_books': 0.7, 'lobsters': 0.65,
            'mastodon': 0.5, 'khanacademy': 0.7, 'coursera': 0.65,
            'edx': 0.65, 'paperity': 0.7, 'base': 0.7
        }

    def rank(self, results: List[Dict], query: str) -> List[Dict]:
        query_terms = self._tokenize(query)
        scored_results = []
        for result in results:
            score = self._calculate_score(result, query_terms)
            result['_score'] = score
            scored_results.append(result)
        scored_results.sort(key=lambda x: x['_score'], reverse=True)
        for result in scored_results:
            del result['_score']
        return scored_results

    def _calculate_score(self, result: Dict, query_terms: List[str]) -> float:
        score = 0.0
        title = result.get('title', '').lower()
        snippet = result.get('snippet', '').lower()
        url = result.get('url', '').lower()
        source = result.get('source', 'unknown')
        score += self.source_weights.get(source, 0.5)
        title_terms = self._tokenize(title)
        title_matches = set(query_terms) & set(title_terms)
        score += len(title_matches) / len(query_terms) * 2.0 if query_terms else 0
        if query_terms and all(term in title for term in query_terms):
            score += 3.0
        snippet_matches = sum(1 for term in query_terms if term in snippet)
        score += snippet_matches / len(query_terms) * 1.0 if query_terms else 0
        url_matches = sum(1 for term in query_terms if term in url)
        score += url_matches / len(query_terms) * 0.5 if query_terms else 0
        metadata = result.get('metadata', {})
        if metadata:
            if metadata.get('citations', 0) > 100:
                score += 1.0
            elif metadata.get('citations', 0) > 10:
                score += 0.5
            if metadata.get('stars', 0) > 1000:
                score += 1.0
            elif metadata.get('stars', 0) > 100:
                score += 0.5
            if metadata.get('score', 0) > 1000:
                score += 0.8
            elif metadata.get('score', 0) > 100:
                score += 0.4
        return score

    def _tokenize(self, text: str) -> List[str]:
        return set(re.findall(r'\w+', text.lower()))
