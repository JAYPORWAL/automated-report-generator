import random
import time
from typing import Type, TypeVar

import httpx
from google import genai
from google.genai import types
from google.genai.errors import APIError
from pydantic import BaseModel

from src.config import settings
from src.utils.logger import logger
from src.utils.validators import validate_json_string

T = TypeVar("T", bound=BaseModel)


def is_transient_error(e: Exception) -> bool:
    """
    Identifies transient network or API errors suitable for retry.
    Non-transient failures (invalid API keys, missing models, schema conflicts)
    should fail immediately.
    """
    # 1. Connection/read timeouts and network errors
    if isinstance(e, (httpx.TimeoutException, httpx.NetworkError)):
        return True

    # 2. Check for Google API errors
    if isinstance(e, APIError) or "APIError" in type(e).__name__:
        code = getattr(e, "code", None)
        if code in (429, 500, 503, 504):
            return True
        # Check error message strings for transient triggers
        msg = str(e).lower()
        if "rate limit" in msg or "resource exhausted" in msg or "quota" in msg or "timeout" in msg:
            return True

    # 3. Standard connection exceptions
    if isinstance(e, (ConnectionResetError, ConnectionRefusedError, ConnectionError)):
        return True

    return False


class GeminiService:
    """Service to handle interactions with the Google Gemini API using the google-genai SDK."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    @property
    def client(self) -> genai.Client:
        """Lazily instantiates the Gemini API Client with custom httpx timeouts."""
        if not self._client:
            if not self.api_key:
                raise ValueError("Gemini API key is not configured. Please supply one.")

            # Create custom httpx Client with connection and read timeouts
            # Connection timeout: 5s, Read timeout: 20s
            limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
            timeout = httpx.Timeout(20.0, connect=5.0, read=20.0)
            custom_httpx = httpx.Client(limits=limits, timeout=timeout)

            # Set up the Client with overall timeout constraints
            self._client = genai.Client(
                api_key=self.api_key,
                http_options=types.HttpOptions(
                    httpx_client=custom_httpx,
                    timeout=20000,  # 20 seconds overall timeout in milliseconds
                ),
            )
        return self._client

    def generate_structured(
        self,
        prompt: str,
        response_schema: Type[T],
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.2,
        max_retries: int = 3,
        initial_delay: float = 2.0,
    ) -> T:
        """
        Generates content from Gemini, enforcing a structured Pydantic schema output.
        Implements exponential backoff with random jitter for transient errors.
        """
        model_name = model or settings.gemini_model
        logger.info(f"Generating structured content using model: {model_name}")

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema,
            system_instruction=system_instruction,
            temperature=temperature,
        )

        delay = initial_delay
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                # Log structured metadata for traceability
                logger.info(
                    "Executing structured Gemini API generation",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "model": model_name,
                        "prompt_length": len(prompt),
                    },
                )

                response = self.client.models.generate_content(
                    model=model_name, contents=prompt, config=config
                )

                if not response.text:
                    raise ValueError("Gemini API returned an empty response.")

                # Parse structured JSON output
                parsed_data = validate_json_string(response.text)
                return response_schema.model_validate(parsed_data)

            except Exception as e:
                last_exception = e

                # Halt immediately on non-transient failures
                if not is_transient_error(e):
                    logger.error(
                        "Non-transient error encountered during structured generation, raising immediately.",
                        extra={"error": str(e), "model": model_name},
                    )
                    raise e

                # Jitter calculations
                jitter = random.uniform(0.1, 1.0)
                backoff_delay = (delay * (2 ** (attempt - 1))) + jitter

                logger.warning(
                    f"Gemini API structured request failed on attempt {attempt}: {str(e)}. "
                    f"Retrying in {backoff_delay:.2f}s..."
                )
                if attempt < max_retries:
                    time.sleep(backoff_delay)
                else:
                    logger.error(
                        f"Gemini API structured call failed after {max_retries} attempts.",
                        extra={"error": str(e), "model": model_name},
                    )

        # Fallback unstructured generation and manual parsing if structured fails
        logger.warning("Attempting fallback unstructured generation and manual parsing...")
        try:
            fallback_config = types.GenerateContentConfig(
                system_instruction=system_instruction, temperature=temperature
            )
            prompt_with_instructions = (
                f"{prompt}\n\nIMPORTANT: Return ONLY a valid JSON object matching the schema. "
                "Do not include markdown code block wrappers or other text."
            )
            response = self.client.models.generate_content(
                model=model_name, contents=prompt_with_instructions, config=fallback_config
            )
            if response.text:
                parsed_data = validate_json_string(response.text)
                return response_schema.model_validate(parsed_data)
        except Exception as fallback_err:
            logger.error(f"Fallback unstructured generation also failed: {fallback_err}")
            # Raise the original structured generation exception to maintain stack trace integrity
            raise last_exception from fallback_err

        raise last_exception or RuntimeError(
            "Gemini Service failed to generate structured content."
        )

    def generate_text(
        self,
        prompt: str,
        system_instruction: str | None = None,
        model: str | None = None,
        temperature: float = 0.5,
        max_retries: int = 3,
        initial_delay: float = 2.0,
    ) -> str:
        """Generates standard unstructured text response with retries."""
        model_name = model or settings.gemini_model
        config = types.GenerateContentConfig(
            system_instruction=system_instruction, temperature=temperature
        )

        delay = initial_delay
        last_exception = None

        for attempt in range(1, max_retries + 1):
            try:
                logger.info(
                    "Executing text Gemini API generation",
                    extra={
                        "attempt": attempt,
                        "max_retries": max_retries,
                        "model": model_name,
                        "prompt_length": len(prompt),
                    },
                )

                response = self.client.models.generate_content(
                    model=model_name, contents=prompt, config=config
                )
                if response.text:
                    return response.text
                raise ValueError("Received empty text response from Gemini.")
            except Exception as e:
                last_exception = e

                # Halt immediately on non-transient failures
                if not is_transient_error(e):
                    logger.error(
                        "Non-transient error encountered during text generation, raising immediately.",
                        extra={"error": str(e), "model": model_name},
                    )
                    raise e

                # Jitter calculations
                jitter = random.uniform(0.1, 1.0)
                backoff_delay = (delay * (2 ** (attempt - 1))) + jitter

                logger.warning(
                    f"Gemini API text call failed on attempt {attempt}: {e}. Retrying in {backoff_delay:.2f}s..."
                )
                if attempt < max_retries:
                    time.sleep(backoff_delay)
                else:
                    logger.error(f"Gemini API text generation failed after {max_retries} attempts.")

        raise last_exception or RuntimeError("Gemini Service text generation failed.")


def check_service_health() -> dict:
    """
    Performs a health check verifying configuration and dependency availability.
    Does NOT make active paid/external API calls.
    """
    health = {
        "status": "healthy",
        "details": {
            "gemini_sdk_available": False,
            "gemini_key_configured": False,
            "tavily_key_configured": False,
            "reportlab_available": False,
            "python_pptx_available": False,
            "duckduckgo_search_available": False,
        },
    }

    # 1. Check Gemini SDK
    try:
        from google import genai  # noqa: F401

        health["details"]["gemini_sdk_available"] = True
    except ImportError:
        health["status"] = "unhealthy"
        logger.error("google-genai SDK is not installed.")

    # 2. Check API keys configured
    if settings.gemini_api_key:
        health["details"]["gemini_key_configured"] = True
    else:
        health["status"] = "unhealthy"
        logger.warning("Gemini API key is not configured in environment.")

    if settings.tavily_api_key:
        health["details"]["tavily_key_configured"] = True

    # 3. Check PDF dependencies
    try:
        import reportlab  # noqa: F401

        health["details"]["reportlab_available"] = True
    except ImportError:
        health["status"] = "unhealthy"
        logger.error("reportlab library is not installed.")

    # 4. Check PowerPoint dependencies
    try:
        import pptx  # noqa: F401

        health["details"]["python_pptx_available"] = True
    except ImportError:
        health["status"] = "unhealthy"
        logger.error("python-pptx library is not installed.")

    # 5. Check DuckDuckGo Search fallback dependencies
    try:
        from ddgs import DDGS  # noqa: F401

        health["details"]["duckduckgo_search_available"] = True
    except ImportError:
        health["status"] = "unhealthy"
        logger.error("ddgs library is not installed.")

    return health
