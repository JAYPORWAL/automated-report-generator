import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from src.constants import SUPPORTED_GEMINI_MODELS


class Settings(BaseSettings):
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    tavily_api_key: str | None = Field(default=None, validation_alias="TAVILY_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", validation_alias="GEMINI_MODEL")
    log_level: str = Field(default="INFO", validation_alias="LOG_LEVEL")
    temp_dir: str = Field(default="temp_exports", validation_alias="TEMP_DIR")
    max_topic_length: int = Field(default=500, validation_alias="MAX_TOPIC_LENGTH")
    max_research_results: int = Field(default=15, validation_alias="MAX_RESEARCH_RESULTS")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("gemini_model")
    @classmethod
    def validate_gemini_model(cls, v: str) -> str:
        if not v or not v.strip():
            return "gemini-2.5-flash"

        cleaned_v = v.strip()
        if cleaned_v not in SUPPORTED_GEMINI_MODELS:
            raise ValueError(
                f"Invalid model name '{cleaned_v}' configured for environment variable GEMINI_MODEL. "
                f"Supported model values are: {SUPPORTED_GEMINI_MODELS}."
            )
        return cleaned_v


# Ensure the temp directory exists, handle configuration validation errors gracefully
settings = None
config_error = None

try:
    settings = Settings()
    os.makedirs(settings.temp_dir, exist_ok=True)
except Exception as e:
    config_error = e

    # Create a fallback settings object with defaults so other imports don't crash
    class FallbackSettings:
        gemini_api_key = None
        tavily_api_key = None
        gemini_model = "gemini-2.5-flash"
        log_level = "INFO"
        temp_dir = "temp_exports"
        max_topic_length = 500
        max_research_results = 15

    settings = FallbackSettings()
