from unittest.mock import MagicMock, patch

import httpx

from src.schemas.research import ResearchNotes
from src.services.research_service import ResearchService, compute_deterministic_score


def test_compute_deterministic_score():
    assert compute_deterministic_score("https://sub.gov.au/page") == 5
    assert compute_deterministic_score("https://mit.edu/research") == 5
    assert compute_deterministic_score("https://en.wikipedia.org/wiki/Main_Page") == 5
    assert compute_deterministic_score("https://reuters.com/news") == 4
    assert compute_deterministic_score("https://bloomberg.com/business") == 4
    assert compute_deterministic_score("https://nature.com/articles") == 4
    assert compute_deterministic_score("https://myblog.com/post") == 2
    assert compute_deterministic_score("invalid-url") == 1


@patch("src.services.research_service.httpx.post")
def test_search_tavily_success(mock_post):
    # Mock Tavily response
    mock_resp = MagicMock()
    mock_resp.json.return_value = {
        "results": [
            {
                "title": "Result 1",
                "url": "https://example.gov/1",
                "content": "Gov content",
                "published_date": "2026-01-01",
            },
            {"title": "Result 2", "url": "https://reuters.com/2", "content": "News content"},
        ]
    }
    mock_resp.raise_for_status.return_value = None
    mock_post.return_value = mock_resp

    service = ResearchService(tavily_api_key="mock-key")
    results = service.search("test topic", max_results=5)

    assert len(results) == 2
    assert results[0]["title"] == "Result 1"
    assert results[0]["url"] == "https://example.gov/1"
    assert results[0]["published_date"] == "2026-01-01"
    assert results[1]["published_date"] == "Unknown"


@patch("src.services.research_service.ResearchService._search_duckduckgo")
@patch("src.services.research_service.httpx.post")
def test_search_tavily_failure_ddg_fallback(mock_post, mock_ddg):
    # Tavily post fails
    mock_post.side_effect = httpx.HTTPError("API offline")

    # DuckDuckGo mock
    mock_ddg.return_value = [
        {"title": "DDG Result", "url": "https://wikipedia.org/ddg", "content": "DDG content"}
    ]

    service = ResearchService(tavily_api_key="mock-key")
    results = service.search("test query")

    assert len(results) == 1
    assert results[0]["title"] == "DDG Result"
    assert results[0]["url"] == "https://wikipedia.org/ddg"


def test_collect_and_deduplicate():
    service = ResearchService()
    raw_results = [
        {
            "title": "A",
            "url": "https://example.gov/1",
            "content": "Fact A",
            "published_date": "2026-01-01",
        },
        {
            "title": "B",
            "url": "https://example.gov/1",
            "content": "Duplicate URL Fact",
            "published_date": "2026-01-01",
        },
        {"title": "C", "url": "https://reuters.com/c", "content": "Fact C"},
        {"title": "D", "url": "https://regular.com/d", "content": "Fact D"},
    ]

    notes = service.collect_and_deduplicate("My Topic", raw_results)

    assert isinstance(notes, ResearchNotes)
    assert notes.topic == "My Topic"
    # Deduplicated (3 items instead of 4)
    assert len(notes.items) == 3
    # Sorted by score descending (example.gov = 5, reuters = 4, regular = 2)
    assert notes.items[0].source_url == "https://example.gov/1"
    assert notes.items[0].score == 5
    assert notes.items[1].source_url == "https://reuters.com/c"
    assert notes.items[1].score == 4
    assert notes.items[2].source_url == "https://regular.com/d"
    assert notes.items[2].score == 2
