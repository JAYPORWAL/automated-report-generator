from unittest.mock import MagicMock, patch

from src.schemas.report import ReportDraft
from src.services.gemini_service import GeminiService, check_service_health


@patch("src.services.gemini_service.genai.Client")
def test_gemini_service_client_instantiation(mock_client):
    service = GeminiService(api_key="test-key")
    assert service.client is not None
    mock_client.assert_called_once_with(api_key="test-key")


@patch("src.services.gemini_service.genai.Client")
def test_gemini_generate_text_success(mock_client_class):
    # Mock text response
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Hello world"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = GeminiService(api_key="test-key")
    result = service.generate_text("Say hello")

    assert result == "Hello world"
    mock_client.models.generate_content.assert_called_once()


@patch("src.services.gemini_service.genai.Client")
def test_gemini_generate_structured_success(mock_client_class):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"title": "T", "executive_summary": "E", "introduction": "I", '
        '"key_findings": "F", "detailed_analysis": "D", "challenges_risks": "C", '
        '"recommendations": "R", "conclusion": "N", "references": []}'
    )
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = GeminiService(api_key="test-key")
    result = service.generate_structured("Prompt", ReportDraft)

    assert result.title == "T"
    assert result.executive_summary == "E"


@patch("src.services.gemini_service.genai.Client")
def test_gemini_service_retries_on_failure(mock_client_class):
    mock_client = MagicMock()
    mock_client.models.generate_content.side_effect = [
        RuntimeError("Temporary error"),
        RuntimeError("Temporary error"),
        MagicMock(text="Hello world"),
    ]
    mock_client_class.return_value = mock_client

    service = GeminiService(api_key="test-key")
    result = service.generate_text("Prompt", max_retries=3, initial_delay=0.01)

    assert result == "Hello world"
    assert mock_client.models.generate_content.call_count == 3


def test_check_service_health():
    # Run the healthcheck (will run on actual environment variables configured)
    health = check_service_health()
    assert "status" in health
    assert "details" in health
    assert health["details"]["duckduckgo_search_available"] is True
