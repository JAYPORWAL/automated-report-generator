import os
import runpy
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.constants import SUPPORTED_GEMINI_MODELS, SUPPORTED_REPORT_TONES
from src.schemas.report import ReportDraft, ReportRequest
from src.schemas.review import ReviewResult

# --- Gemini Model Tests ---


def test_settings_gemini_model_flash_accepted(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-flash"


def test_settings_gemini_model_pro_accepted(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-pro"


def test_settings_invalid_model_error(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", " invalid-model-name ")
    with pytest.raises(ValidationError) as exc_info:
        Settings()

    err_msg = str(exc_info.value)
    assert "GEMINI_MODEL" in err_msg or "gemini_model" in err_msg
    assert "invalid-model-name" in err_msg
    assert "gemini-2.5-flash" in err_msg


def test_settings_missing_model_default(monkeypatch):
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-flash"


def test_settings_blank_model_default(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "   ")
    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-flash"


def test_config_imports_supported_models_from_constants():
    import src.config as config

    assert hasattr(config, "SUPPORTED_GEMINI_MODELS")
    assert config.SUPPORTED_GEMINI_MODELS is SUPPORTED_GEMINI_MODELS


def test_no_hardcoded_duplicate_model_list_in_config():
    config_path = os.path.join("src", "config.py")
    with open(config_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "allowed =" not in content
    assert '["gemini-2.5-flash", "gemini-2.5-pro"]' not in content
    assert '["gemini-2.5-pro", "gemini-2.5-flash"]' not in content


# --- Tone Tests ---


def test_strategic_exists_in_supported_report_tones():
    assert "Strategic" in SUPPORTED_REPORT_TONES


def test_every_tone_accepted_by_schema():
    for tone in SUPPORTED_REPORT_TONES:
        req = ReportRequest(topic="Test Topic", tone=tone, length="Medium")
        assert req.tone == tone


def test_invalid_tone_raises_validation_error():
    with pytest.raises(ValidationError) as exc_info:
        ReportRequest(topic="Test Topic", tone="InvalidToneOption", length="Medium")
    assert "Invalid tone" in str(exc_info.value)


def test_streamlit_uses_supported_report_tones():
    app_path = "app.py"
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert "SUPPORTED_REPORT_TONES" in content
    assert "Report Tone" in content


def test_strategic_report_prompt_instructions():
    mock_gemini = MagicMock()
    # Mock structured output generate response
    expected_draft = ReportDraft(
        title="Strategic Analysis Report",
        executive_summary="Business direction analysis.",
        introduction="Intro",
        key_findings="Findings",
        detailed_analysis="Analysis",
        challenges_risks="Risks",
        recommendations="Actionable recommendations",
        conclusion="Conclusion",
        references=[],
    )
    mock_gemini.generate_structured.return_value = expected_draft

    from src.services.report_service import ReportService

    service = ReportService(gemini_service=mock_gemini)
    service.draft_report(topic="Market Penetration", research_notes=None, tone="Strategic")

    call_args = mock_gemini.generate_structured.call_args[1]
    system_instruction = call_args["system_instruction"]
    assert "business direction" in system_instruction.lower()
    assert "decisions" in system_instruction.lower()
    assert "trade-offs" in system_instruction.lower()
    assert "concise executive language" in system_instruction.lower()


def test_reviewer_prompt_preserves_strategic_tone():
    mock_gemini = MagicMock()
    expected_review = ReviewResult(
        quality_score=95,
        issues_found=[],
        improvements_made=["Polished text"],
        suggestions=[],
        improved_report="# Final Strategic Analysis",
    )
    mock_gemini.generate_structured.return_value = expected_review

    from src.services.review_service import ReviewService

    service = ReviewService(gemini_service=mock_gemini)
    draft = ReportDraft(
        title="Strategic Analysis Report",
        executive_summary="Executive summary info.",
        introduction="Intro",
        key_findings="Findings",
        detailed_analysis="Analysis",
        challenges_risks="Risks",
        recommendations="Recommendations",
        conclusion="Conclusion",
        references=[],
    )
    service.review_report(draft=draft, research_notes=None, tone="Strategic")

    call_args = mock_gemini.generate_structured.call_args[1]
    system_instruction = call_args["system_instruction"]
    assert "preserve" in system_instruction.lower()
    assert "strategic" in system_instruction.lower()


def test_no_duplicate_tone_list_outside_constants():
    files_to_check = [
        os.path.join("src", "config.py"),
        os.path.join("src", "services", "report_service.py"),
        os.path.join("src", "workflow", "report_workflow.py"),
    ]
    for path in files_to_check:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
        assert '["Professional",' not in content
        assert "('Professional'," not in content
        assert '["Strategic",' not in content
        assert "('Strategic'," not in content


# --- UI Safety Tests ---


@patch("streamlit.error")
@patch("streamlit.stop")
def test_streamlit_handles_config_error_safely(mock_stop, mock_error):
    from pydantic import BaseModel

    # Create a real ValidationError in Pydantic v2
    val_err = None
    try:

        class DummyModel(BaseModel):
            gemini_model: int

        DummyModel(gemini_model="invalid")
    except ValidationError as e:
        val_err = e

    with patch("src.config.config_error", val_err):
        try:
            runpy.run_path("app.py")
        except SystemExit:
            pass
        except Exception:
            pass

        mock_error.assert_called_once()
        mock_stop.assert_called_once()
        called_arg = mock_error.call_args[0][0]
        assert "Configuration Error" in called_arg


def test_settings_log_level_validator(monkeypatch):
    monkeypatch.setenv("LOG_LEVEL", "invalid-log-level")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Invalid log level" in str(exc_info.value)


def test_settings_temp_dir_validator(monkeypatch):
    monkeypatch.setenv("TEMP_DIR", "   ")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "Temporary export directory (TEMP_DIR) path cannot be empty" in str(exc_info.value)


def test_settings_max_topic_length_validator(monkeypatch):
    monkeypatch.setenv("MAX_TOPIC_LENGTH", "5")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "MAX_TOPIC_LENGTH must be between 10 and 2000" in str(exc_info.value)


def test_settings_max_research_results_validator(monkeypatch):
    monkeypatch.setenv("MAX_RESEARCH_RESULTS", "0")
    with pytest.raises(ValidationError) as exc_info:
        Settings()
    assert "MAX_RESEARCH_RESULTS must be between 1 and 50" in str(exc_info.value)
