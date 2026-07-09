import re
import urllib.parse
from typing import Any

import httpx

from src.config import settings
from src.constants import OFFICIAL_DOMAINS, RECOGNIZED_DOMAINS
from src.schemas.research import ResearchItem, ResearchNotes
from src.utils.logger import logger
from src.utils.text_utils import extract_domain


def compute_deterministic_score(url: str) -> int:
    """
    Determines reliability score (1 to 5) based on the URL domain.
    - 5: Official / Government / Academic domains
    - 4: Renowned news publications / journals
    - 2: Standard commercial/blog domains
    - 1: Unknown or unclassified
    """
    domain = extract_domain(url)
    if not domain:
        return 1

    # Check official
    if any(o_dom in domain for o_dom in OFFICIAL_DOMAINS):
        return 5

    # Check recognized news / journals
    if any(domain == r_dom or domain.endswith("." + r_dom) for r_dom in RECOGNIZED_DOMAINS):
        return 4

    return 2


class ResearchService:
    """Service to handle background research using Tavily or DuckDuckGo fallback."""

    def __init__(self, tavily_api_key: str | None = None):
        self.tavily_api_key = tavily_api_key or settings.tavily_api_key

    def search(self, query: str, max_results: int | None = None) -> list[dict[str, Any]]:
        """
        Executes search query. First attempts Tavily API, and falls back to
        pure-Python DuckDuckGo HTML scraping if keys are missing or requests fail.
        """
        limit = max_results or settings.max_research_results

        # 1. Try Tavily
        if self.tavily_api_key:
            try:
                logger.info("Attempting web search via Tavily API...")
                results = self._search_tavily(query, limit)
                if results:
                    return results
            except Exception as e:
                logger.warning(f"Tavily search failed: {e}. Falling back to DuckDuckGo.")

        # 2. Try DuckDuckGo
        try:
            logger.info("Attempting web search via DuckDuckGo fallback...")
            return self._search_duckduckgo(query, limit)
        except Exception as e:
            logger.error(f"DuckDuckGo search fallback also failed: {e}")

        return []

    def _search_tavily(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Hits Tavily search API directly using httpx with short timeouts."""
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": self.tavily_api_key,
            "query": query,
            "search_depth": "basic",
            "max_results": limit,
        }

        # httpx post with 8 second timeout
        response = httpx.post(url, json=payload, timeout=8.0)
        response.raise_for_status()
        data = response.json()

        results = []
        for r in data.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("url", ""),
                    "content": r.get("content", ""),
                    "published_date": r.get("published_date") or "Unknown",
                }
            )
        return results

    def _search_duckduckgo(self, query: str, limit: int) -> list[dict[str, Any]]:
        """
        Queries DuckDuckGo's HTML-only version and parses it using regular expressions.
        Pure Python, zero-dependency fallback.
        """
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        }
        data = {"q": query}

        # Make request with timeout
        response = httpx.post(url, data=data, headers=headers, timeout=8.0)
        response.raise_for_status()

        html_content = response.text
        results = []

        # Regex matching
        # Result titles and links: <a class="result__a" href="[URL]">Title</a>
        matches = list(
            re.finditer(
                r'<a\s+class="result__a"\s+href="(?P<url>[^"]+)"[^>]*>(?P<title>.*?)</a>',
                html_content,
                re.DOTALL,
            )
        )

        # Snippets: <a class="result__snippet" ...>Snippet</a> or <span class="result__snippet">Snippet</span>
        snippets = re.findall(
            r'<a\s+class="result__snippet"[^>]*>(.*?)</a>', html_content, re.DOTALL
        )
        if not snippets:
            snippets = re.findall(
                r'<span\s+class="result__snippet"[^>]*>(.*?)</span>', html_content, re.DOTALL
            )

        for idx, match in enumerate(matches):
            if len(results) >= limit:
                break

            raw_url = match.group("url")

            # DuckDuckGo wraps links as /l/?kh=-1&uddg=https%3A%2F%2Fexample.com
            url = raw_url
            if "/l/?kh=" in raw_url:
                parsed_url = urllib.parse.urlparse(raw_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)
                if "uddg" in query_params:
                    url = query_params["uddg"][0]

            title = re.sub(r"<[^>]+>", "", match.group("title")).strip()

            content = ""
            if idx < len(snippets):
                content = re.sub(r"<[^>]+>", "", snippets[idx]).strip()

            results.append(
                {"title": title, "url": url, "content": content, "published_date": "Unknown"}
            )

        return results

    def collect_and_deduplicate(
        self, query: str, raw_results: list[dict[str, Any]]
    ) -> ResearchNotes:
        """
        Deduplicates sources, scores credibility, structures raw results into ResearchNotes.
        """
        seen_urls = set()
        deduped_items = []

        for r in raw_results:
            url = r.get("url", "").strip()
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)

            # Simple scoring
            score = compute_deterministic_score(url)

            fact_summary = f"[{r.get('title', 'Source')}] - {r.get('content', '')}"
            deduped_items.append(
                ResearchItem(
                    fact=fact_summary,
                    source_url=url,
                    publication_date=r.get("published_date") or "Unknown",
                    score=score,
                )
            )

        # Sort items by credibility score (descending)
        deduped_items.sort(key=lambda x: x.score, reverse=True)

        # Cap search items
        deduped_items = deduped_items[: settings.max_research_results]

        summary = f"Gathered {len(deduped_items)} unique and scored sources for: '{query}'."
        logger.info(summary)

        return ResearchNotes(topic=query, summary=summary, items=deduped_items)
