import os
import runpy
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from src.config import Settings
from src.constants import SUPPORTED_GEMINI_MODELS


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
    # Check that error message includes GEMINI_MODEL, invalid-model-name, and gemini-2.5-flash
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

    # Assert that allowed allowed/models definition was removed
    assert "allowed =" not in content
    # Assert that the list literal itself isn't hardcoded in config
    assert '["gemini-2.5-flash", "gemini-2.5-pro"]' not in content
    assert '["gemini-2.5-pro", "gemini-2.5-flash"]' not in content


def test_streamlit_uses_supported_gemini_models():
    app_path = "app.py"
    with open(app_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "SUPPORTED_GEMINI_MODELS" in content
    assert "selectbox" in content
    assert "Gemini Model" in content


@patch("streamlit.error")
@patch("streamlit.stop")
def test_streamlit_handles_config_error_safely(mock_stop, mock_error):
    with patch("src.config.config_error", ValueError("Simulated validation error")):
        try:
            runpy.run_path("app.py")
        except SystemExit:
            pass
        except Exception:
            pass

        mock_error.assert_called_once()
        mock_stop.assert_called_once()

        # Verify message doesn't expose raw tracebacks and displays configuration error
        called_arg = mock_error.call_args[0][0]
        assert "Configuration Error" in called_arg
        assert "Simulated validation error" in called_arg
