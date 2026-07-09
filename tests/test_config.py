from src.config import Settings


def test_settings_load_defaults():
    settings = Settings(_env_file=None)
    assert settings.gemini_model == "gemini-2.5-flash"
    assert settings.log_level == "INFO"
    assert settings.temp_dir == "temp_exports"
    assert settings.max_topic_length == 500
    assert settings.max_research_results == 15


def test_settings_custom_env(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-pro")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("MAX_TOPIC_LENGTH", "100")

    settings = Settings()
    assert settings.gemini_model == "gemini-2.5-pro"
    assert settings.log_level == "DEBUG"
    assert settings.max_topic_length == 100


def test_settings_invalid_model_fallback(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "invalid-model")
    settings = Settings()
    # It should fallback to gemini-2.5-flash
    assert settings.gemini_model == "gemini-2.5-flash"
