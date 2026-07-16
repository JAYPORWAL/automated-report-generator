import html
import re
import urllib.parse
from typing import Any

import httpx

from src.config import settings
from src.constants import OFFICIAL_DOMAINS, RECOGNIZED_DOMAINS
from src.schemas.research import ResearchItem, ResearchNotes
from src.utils.logger import logger
from src.utils.text_utils import extract_domain
from src.utils.validators import validate_url


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


def sanitize_snippet(text: str) -> str:
    """Sanitizes text snippets by removing HTML tags and resolving HTML entities."""
    if not text:
        return ""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]+>", "", text)
    # Decode HTML entity references (e.g. &amp;, &quot;)
    cleaned = html.unescape(cleaned)
    # Standardize whitespace
    cleaned = " ".join(cleaned.split())
    return cleaned


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

        try:
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
        except httpx.HTTPStatusError as e:
            logger.error(f"Tavily HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"Tavily search timed out: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Tavily connection error: {e}")
            raise

    def _search_duckduckgo(self, query: str, limit: int) -> list[dict[str, Any]]:
        """
        Queries DuckDuckGo using the official ddgs library with timeouts and error handling.
        """
        try:
            from ddgs import DDGS

            with DDGS(timeout=8.0) as ddgs:
                logger.info(f"Querying ddgs for '{query}' with limit {limit}")
                ddg_results = ddgs.text(query, max_results=limit)

                if not ddg_results:
                    logger.info("ddgs returned empty result list.")
                    return []

                results = []
                for r in ddg_results:
                    raw_url = r.get("href", "")

                    # Clean and decode DuckDuckGo redirect wraps if present
                    url = raw_url
                    if "/l/?kh=" in raw_url:
                        parsed_url = urllib.parse.urlparse(raw_url)
                        query_params = urllib.parse.parse_qs(parsed_url.query)
                        if "uddg" in query_params:
                            url = query_params["uddg"][0]

                    results.append(
                        {
                            "title": r.get("title", ""),
                            "url": url,
                            "content": r.get("body", ""),
                            "published_date": "Unknown",
                        }
                    )
                return results

        except httpx.HTTPStatusError as e:
            logger.error(f"DuckDuckGo search HTTP error: {e.response.status_code}")
            raise
        except httpx.TimeoutException as e:
            logger.error(f"DuckDuckGo search timed out: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"DuckDuckGo connection request error: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in DuckDuckGo search execution: {e}")
            raise

    def collect_and_deduplicate(
        self, query: str, raw_results: list[dict[str, Any]]
    ) -> ResearchNotes:
        """
        Deduplicates sources, validates URLs, sanitizes snippets,
        scores credibility, and structures raw results into ResearchNotes.
        """
        seen_urls = set()
        deduped_items = []

        for r in raw_results:
            url = r.get("url", "").strip()
            if not url:
                continue

            # Validate that the URL is a correct HTTP/HTTPS link
            if not validate_url(url):
                logger.warning(f"Discarding invalid URL structure: {url}")
                continue

            if url in seen_urls:
                continue
            seen_urls.add(url)

            # Sanitize title and content to prevent malformed HTML/injections
            title_sanitized = sanitize_snippet(r.get("title", "Source"))
            content_sanitized = sanitize_snippet(r.get("content", ""))

            # Calculate deterministic credibility score
            score = compute_deterministic_score(url)

            fact_summary = f"[{title_sanitized}] - {content_sanitized}"
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

        # Cap search items to settings limit
        deduped_items = deduped_items[: settings.max_research_results]

        summary = f"Gathered {len(deduped_items)} unique and scored sources for: '{query}'."
        logger.info(summary)

        return ResearchNotes(topic=query, summary=summary, items=deduped_items)
