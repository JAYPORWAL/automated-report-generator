import os

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


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
        allowed = ["gemini-2.5-flash", "gemini-2.5-pro"]
        if v not in allowed:
            return "gemini-2.5-flash"
        return v


# Ensure the temp directory exists
settings = Settings()
os.makedirs(settings.temp_dir, exist_ok=True)
