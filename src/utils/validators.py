import json
import re
from urllib.parse import urlparse

from src.config import settings
from src.constants import SUPPORTED_GEMINI_MODELS, SUPPORTED_REPORT_TONES


class ValidationError(Exception):
    """Custom validation exception."""

    pass


def validate_topic(topic: str) -> str:
    """Validates the research topic string."""
    if not topic or not topic.strip():
        raise ValidationError("Topic cannot be empty.")

    cleaned = topic.strip()
    if len(cleaned) > settings.max_topic_length:
        raise ValidationError(
            f"Topic exceeds maximum length of {settings.max_topic_length} characters. "
            f"Current length: {len(cleaned)}"
        )
    return cleaned


def validate_api_keys(gemini_key: str | None) -> None:
    """Validates that at least the Gemini API key is present."""
    if not gemini_key or not gemini_key.strip():
        raise ValidationError(
            "Gemini API Key is missing. Please configure it in your .env file "
            "or enter it in the sidebar."
        )


def validate_json_string(json_str: str) -> dict:
    """Safely validates and parses a JSON string, raising ValidationError on failure."""
    if not json_str:
        raise ValidationError("JSON content is empty.")
    try:
        # Strip potential markdown code blocks surrounding JSON
        cleaned = json_str.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise ValidationError(f"Invalid JSON response: {e}") from e


def validate_url(url: str) -> bool:
    """Validates if a string is a correctly formatted HTTP/HTTPS URL."""
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except ValueError:
        return False


def sanitize_filename(filename: str) -> str:
    """Sanitizes file names to prevent directory traversal or invalid character issues."""
    # Keep only alphanumeric, underscores, hyphens, and dots
    sanitized = re.sub(r"[^\w\-\.]", "_", filename)
    return sanitized


def validate_audience(audience: str) -> str:
    """Validates target audience description length."""
    cleaned = audience.strip()
    if len(cleaned) > 500:
        raise ValidationError(
            f"Target audience exceeds maximum length of 500 characters. "
            f"Current length: {len(cleaned)}"
        )
    return cleaned


def validate_requirements(requirements: str) -> str:
    """Validates special report requirements description length."""
    cleaned = requirements.strip()
    if len(cleaned) > 2000:
        raise ValidationError(
            f"Report requirements exceed maximum length of 2000 characters. "
            f"Current length: {len(cleaned)}"
        )
    return cleaned


def validate_slide_count(slide_count: int) -> int:
    """Validates the requested slide count range."""
    if not (5 <= slide_count <= 15):
        raise ValidationError(f"Slide count must be between 5 and 15. Received: {slide_count}")
    return slide_count


def validate_tone(tone: str) -> str:
    """Validates that the selected tone is supported."""
    if tone not in SUPPORTED_REPORT_TONES:
        raise ValidationError(
            f"Invalid tone '{tone}'. Supported tones are: {SUPPORTED_REPORT_TONES}"
        )
    return tone


def validate_model(model: str) -> str:
    """Validates that the selected Gemini model is supported."""
    if model not in SUPPORTED_GEMINI_MODELS:
        raise ValidationError(
            f"Invalid model '{model}'. Supported models are: {SUPPORTED_GEMINI_MODELS}"
        )
    return model
