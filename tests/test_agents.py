from unittest.mock import MagicMock

from src.agents.research_agent import ResearchAgent
from src.agents.reviewer_agent import ReviewerAgent
from src.agents.slide_agent import SlideAgent
from src.agents.writer_agent import WriterAgent
from src.schemas.report import ReportDraft
from src.schemas.research import ResearchNotes
from src.schemas.review import ReviewResult
from src.services.slide_service import PresentationContent


def test_research_agent_run():
    mock_service = MagicMock()
    notes = ResearchNotes(topic="topic", summary="summary", items=[])
    mock_service.search.return_value = [
        {"title": "A", "url": "https://gov.com/1", "content": "body"}
    ]
    mock_service.collect_and_deduplicate.return_value = notes

    agent = ResearchAgent(research_service=mock_service)
    result = agent.run("topic")

    assert result == notes
    mock_service.search.assert_called_once_with("topic")
    mock_service.collect_and_deduplicate.assert_called_once()


def test_research_agent_fallback_on_error():
    mock_service = MagicMock()
    mock_service.search.side_effect = RuntimeError("Search error")

    agent = ResearchAgent(research_service=mock_service)
    result = agent.run("topic")

    assert result.topic == "topic"
    assert len(result.items) == 0


def test_writer_agent_run():
    mock_service = MagicMock()
    draft = ReportDraft(
        title="T",
        executive_summary="E",
        introduction="I",
        key_findings="F",
        detailed_analysis="D",
        challenges_risks="C",
        recommendations="R",
        conclusion="N",
        references=[],
    )
    mock_service.draft_report.return_value = draft

    agent = WriterAgent(report_service=mock_service)
    result = agent.run("topic", None)

    assert result == draft
    mock_service.draft_report.assert_called_once()


def test_reviewer_agent_run():
    mock_service = MagicMock()
    review = ReviewResult(
        quality_score=90,
        issues_found=[],
        improvements_made=[],
        suggestions=[],
        improved_report="report",
    )
    mock_service.review_report.return_value = review

    agent = ReviewerAgent(review_service=mock_service)
    result = agent.run(MagicMock(), None)

    assert result == review
    mock_service.review_report.assert_called_once()


def test_slide_agent_run():
    mock_service = MagicMock()
    content = PresentationContent(title="T", subtitle="S", agenda=[], slides=[])
    mock_service.generate_presentation.return_value = content

    agent = SlideAgent(slide_service=mock_service)
    result = agent.run("report", 5)

    assert result == content
    mock_service.generate_presentation.assert_called_once_with(
        report_markdown="report", slide_count=5, model=None
    )
