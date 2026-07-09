import os
from unittest.mock import MagicMock, patch

from src.schemas.report import ReportDraft
from src.schemas.review import ReviewResult
from src.services.slide_service import PresentationContent, SlideContent
from src.workflow.report_workflow import ReportWorkflow


@patch("src.services.gemini_service.genai.Client")
@patch("src.services.research_service.ResearchService._search_duckduckgo")
@patch("src.services.research_service.httpx.post")
def test_workflow_end_to_end_mocked(mock_post, mock_ddg, mock_genai_client):
    # Setup mocks
    # 1. Tavily mock
    mock_post.return_value.json.return_value = {
        "results": [
            {
                "title": "Fact A",
                "url": "https://gov.com/1",
                "content": "Information content 1",
                "published_date": "2026-01-01",
            }
        ]
    }
    mock_post.return_value.raise_for_status.return_value = None

    # 2. Gemini structured responses mock
    # The workflow makes three structured generation calls:
    # Attempt 1: ReportDraft (Writing step)
    # Attempt 2: ReviewResult (Review step)
    # Attempt 3: PresentationContent (Presentation step)

    mock_gemini_service = MagicMock()

    mock_draft = ReportDraft(
        title="Automated Test Report",
        executive_summary="Draft summary",
        introduction="Draft intro",
        key_findings="Draft findings",
        detailed_analysis="Draft analysis",
        challenges_risks="Draft risks",
        recommendations="Draft recommendations",
        conclusion="Draft conclusion",
        references=["https://gov.com/1"],
    )

    mock_review = ReviewResult(
        quality_score=95,
        issues_found=["No issues"],
        improvements_made=["Cleaned formatting"],
        suggestions=["Everything is good"],
        improved_report="# Automated Test Report\n\n## Executive Summary\nImproved draft summary.",
    )

    mock_pres = PresentationContent(
        title="Test PPTX Title",
        subtitle="Test Subtitle",
        agenda=["Intro", "Findings"],
        slides=[SlideContent(title="Slide 1", bullets=["Point A"], speaker_notes="Notes")],
    )

    mock_gemini_service.generate_structured.side_effect = [mock_draft, mock_review, mock_pres]

    # Instantiate workflow and override gemini_service
    workflow = ReportWorkflow(gemini_api_key="mock-key", tavily_api_key="mock-key")
    workflow.gemini_service = mock_gemini_service
    # Re-link child services and agents to the mocked gemini_service
    workflow.report_service.gemini_service = mock_gemini_service
    workflow.review_service.gemini_service = mock_gemini_service
    workflow.slide_service.gemini_service = mock_gemini_service

    # Execute workflow generator
    steps = list(
        workflow.execute(
            topic="Testing Workflow",
            tone="Professional",
            length="Medium",
            slide_count=5,
            enable_research=True,
            user_context="Extra test context",
            target_audience="Engineers",
            report_requirements="None",
            model_selection="gemini-2.5-flash",
        )
    )

    # Verify steps yielded
    step_names = [s["step"] for s in steps]
    assert "research" in step_names
    assert "writing" in step_names
    assert "reviewing" in step_names
    assert "presentation" in step_names
    assert "export" in step_names
    assert "complete" in step_names

    # Verify final results
    final_step = steps[-1]
    assert final_step["step"] == "complete"
    results = final_step["results"]
    assert "draft_report" in results
    assert "final_report" in results
    assert "export_paths" in results

    # Check that export paths are files and exist
    export_paths = results["export_paths"]
    assert "report_md" in export_paths
    assert "report_pdf" in export_paths
    assert "presentation_pptx" in export_paths

    for _name, path in export_paths.items():
        assert os.path.exists(path)
        # Clean up files immediately
        try:
            os.remove(path)
        except Exception:
            pass
