from unittest.mock import MagicMock

from src.schemas.report import ReportDraft
from src.schemas.research import ResearchItem, ResearchNotes
from src.services.report_service import ReportService


def test_draft_report_research_enabled():
    mock_gemini = MagicMock()

    # Mock structured response
    expected_draft = ReportDraft(
        title="AI Revolution",
        executive_summary="Summary text",
        introduction="Intro text",
        key_findings="Findings text",
        detailed_analysis="Analysis text",
        challenges_risks="Risks text",
        recommendations="Recommendations text",
        conclusion="Conclusion text",
        references=[],
    )
    mock_gemini.generate_structured.return_value = expected_draft

    service = ReportService(gemini_service=mock_gemini)

    notes = ResearchNotes(
        topic="AI Revolution",
        summary="Some summary",
        items=[ResearchItem(fact="Fact 1", source_url="https://mit.edu/1", score=5)],
    )

    result = service.draft_report(
        topic="AI Revolution",
        research_notes=notes,
        tone="Professional",
        length="Medium",
        user_context="Context",
        audience="General",
        requirements="None",
    )

    assert result.title == "AI Revolution"
    # Verify references are populated from notes
    assert result.references == ["https://mit.edu/1"]
    assert mock_gemini.generate_structured.call_count == 1


def test_draft_report_research_disabled():
    mock_gemini = MagicMock()

    expected_draft = ReportDraft(
        title="AI Revolution",
        executive_summary="Draft based on context",
        introduction="Intro text",
        key_findings="Findings text",
        detailed_analysis="Analysis text",
        challenges_risks="Risks text",
        recommendations="Recommendations text",
        conclusion="Conclusion text",
        references=[],
    )
    mock_gemini.generate_structured.return_value = expected_draft

    service = ReportService(gemini_service=mock_gemini)

    result = service.draft_report(
        topic="AI Revolution",
        research_notes=None,  # DISABLED
        tone="Professional",
        length="Medium",
        user_context="Only this info",
        audience="General",
        requirements="None",
    )

    assert result.title == "AI Revolution"
    # Verify notice is injected into executive summary
    assert "[Notice: Based solely on user-supplied context]" in result.executive_summary
    # Verify default reference when research disabled
    assert result.references == ["Report drafted based on user-supplied context only."]
