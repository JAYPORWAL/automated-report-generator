import pytest

from src.utils.validators import (
    ValidationError,
    sanitize_filename,
    validate_api_keys,
    validate_audience,
    validate_json_string,
    validate_model,
    validate_requirements,
    validate_slide_count,
    validate_tone,
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


def test_validate_audience_success():
    assert validate_audience("  Engineering Team ") == "Engineering Team"


def test_validate_audience_too_long():
    long_aud = "A" * 501
    with pytest.raises(ValidationError, match="Target audience exceeds maximum length"):
        validate_audience(long_aud)


def test_validate_requirements_success():
    assert validate_requirements("  Focus on costs ") == "Focus on costs"


def test_validate_requirements_too_long():
    long_req = "R" * 2001
    with pytest.raises(ValidationError, match="Report requirements exceed maximum length"):
        validate_requirements(long_req)


def test_validate_slide_count_success():
    assert validate_slide_count(5) == 5
    assert validate_slide_count(10) == 10
    assert validate_slide_count(15) == 15


def test_validate_slide_count_out_of_bounds():
    with pytest.raises(ValidationError, match="Slide count must be between 5 and 15"):
        validate_slide_count(4)
    with pytest.raises(ValidationError, match="Slide count must be between 5 and 15"):
        validate_slide_count(16)


def test_validate_tone_success():
    assert validate_tone("Professional") == "Professional"
    assert validate_tone("Strategic") == "Strategic"


def test_validate_tone_invalid():
    with pytest.raises(ValidationError, match="Invalid tone"):
        validate_tone("SillyTone")


def test_validate_model_success():
    assert validate_model("gemini-2.5-flash") == "gemini-2.5-flash"
    assert validate_model("gemini-2.5-pro") == "gemini-2.5-pro"


def test_validate_model_invalid():
    with pytest.raises(ValidationError, match="Invalid model"):
        validate_model("invalid-model")
