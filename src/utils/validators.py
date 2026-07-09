import json
import re
from urllib.parse import urlparse

from src.config import settings


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
