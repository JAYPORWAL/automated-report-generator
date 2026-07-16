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

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        allowed_levels = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")
        cleaned = v.strip().upper()
        if cleaned not in allowed_levels:
            raise ValueError(f"Invalid log level: '{v}'. Supported: {allowed_levels}")
        return cleaned

    @field_validator("temp_dir")
    @classmethod
    def validate_temp_dir(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Temporary export directory (TEMP_DIR) path cannot be empty.")
        return cleaned

    @field_validator("max_topic_length")
    @classmethod
    def validate_max_topic_length(cls, v: int) -> int:
        if v < 10 or v > 2000:
            raise ValueError(f"MAX_TOPIC_LENGTH must be between 10 and 2000. Received: {v}")
        return v

    @field_validator("max_research_results")
    @classmethod
    def validate_max_research_results(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError(f"MAX_RESEARCH_RESULTS must be between 1 and 50. Received: {v}")
        return v


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
