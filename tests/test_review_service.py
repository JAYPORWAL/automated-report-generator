from unittest.mock import MagicMock

import pytest

from src.schemas.report import ReportDraft
from src.schemas.review import ReviewResult
from src.services.review_service import ReviewService


def test_review_report_success():
    mock_gemini = MagicMock()

    expected_review = ReviewResult(
        quality_score=92,
        issues_found=["Grammar fix needed"],
        improvements_made=["Fixed spelling"],
        suggestions=["Add charts next time"],
        improved_report="# Improved Title\nImproved content",
    )
    mock_gemini.generate_structured.return_value = expected_review

    service = ReviewService(gemini_service=mock_gemini)

    draft = ReportDraft(
        title="Draft Title",
        executive_summary="Summary",
        introduction="Intro",
        key_findings="Findings",
        detailed_analysis="Analysis",
        challenges_risks="Risks",
        recommendations="Recs",
        conclusion="Conclusion",
        references=["https://example.com"],
    )

    result = service.review_report(draft=draft, research_notes=None)

    assert result.quality_score == 92
    assert "Grammar fix needed" in result.issues_found
    assert result.improved_report == "# Improved Title\nImproved content"
    assert mock_gemini.generate_structured.call_count == 1


def test_review_result_score_validation():
    # Valid scores
    ReviewResult(
        quality_score=0,
        issues_found=[],
        improvements_made=[],
        suggestions=[],
        improved_report="Text",
    )
    ReviewResult(
        quality_score=100,
        issues_found=[],
        improvements_made=[],
        suggestions=[],
        improved_report="Text",
    )

    # Invalid score
    with pytest.raises(ValueError):
        ReviewResult(
            quality_score=101,
            issues_found=[],
            improvements_made=[],
            suggestions=[],
            improved_report="Text",
        )
    with pytest.raises(ValueError):
        ReviewResult(
            quality_score=-1,
            issues_found=[],
            improvements_made=[],
            suggestions=[],
            improved_report="Text",
        )


Block = """
"""
