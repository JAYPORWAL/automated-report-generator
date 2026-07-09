import pytest

from src.utils.validators import (
    ValidationError,
    sanitize_filename,
    validate_api_keys,
    validate_json_string,
    validate_topic,
    validate_url,
)


def test_validate_topic_success():
    assert validate_topic("  Valid Topic  ") == "Valid Topic"


def test_validate_topic_empty():
    with pytest.raises(ValidationError, match="Topic cannot be empty"):
        validate_topic("   ")


def test_validate_topic_too_long():
    long_topic = "A" * 501
    with pytest.raises(ValidationError, match="Topic exceeds maximum length"):
        validate_topic(long_topic)


def test_validate_api_keys_missing():
    with pytest.raises(ValidationError, match="Gemini API Key is missing"):
        validate_api_keys(None)
    with pytest.raises(ValidationError, match="Gemini API Key is missing"):
        validate_api_keys("  ")


def test_validate_api_keys_present():
    # Should not raise any error
    validate_api_keys("some-valid-key")


def test_validate_json_string_success():
    raw_json = '{"key": "value"}'
    assert validate_json_string(raw_json) == {"key": "value"}


def test_validate_json_string_markdown_blocks():
    markdown_json = '```json\n{"key": "value"}\n```'
    assert validate_json_string(markdown_json) == {"key": "value"}

    markdown_only = '```\n{"key": "value"}\n```'
    assert validate_json_string(markdown_only) == {"key": "value"}


def test_validate_json_string_invalid():
    with pytest.raises(ValidationError, match="Invalid JSON response"):
        validate_json_string('{"key": "value"')


def test_validate_url():
    assert validate_url("https://google.com") is True
    assert validate_url("http://example.org/path") is True
    assert validate_url("not-a-url") is False
    assert validate_url("ftp://host.com") is False


def test_sanitize_filename():
    assert sanitize_filename("my/report\\name?.txt") == "my_report_name_.txt"
    assert sanitize_filename("valid-name_1.2") == "valid-name_1.2"
