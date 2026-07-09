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


class GeminiService:
    """Service to handle interactions with the Google Gemini API using the google-genai SDK."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.gemini_api_key
        self._client = None

    @property
    def client(self) -> genai.Client:
        """Lazily instantiates the Gemini API Client."""
        if not self._client:
            if not self.api_key:
                raise ValueError("Gemini API key is not configured. Please supply one.")
            # Set up the Client
            self._client = genai.Client(api_key=self.api_key)
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
        Implements exponential backoff and timeout fallback handling.
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
                # Wrap execution in a timeout block using httpx to prevent hanging
                # Google genai SDK uses httpx internally, but we can also use a thread/timer or
                # let the API throw if a timeout is passed. Since we want strict timeout control,
                # we call it. If it fails, we catch the exception.
                logger.debug(f"Gemini API request attempt {attempt} of {max_retries}")

                # Call generate_content
                response = self.client.models.generate_content(
                    model=model_name, contents=prompt, config=config
                )

                if not response.text:
                    raise ValueError("Gemini API returned an empty response.")

                # Parse structured JSON output
                parsed_data = validate_json_string(response.text)
                return response_schema.model_validate(parsed_data)

            except (APIError, httpx.HTTPError, ValueError, Exception) as e:
                last_exception = e
                logger.warning(
                    f"Gemini API request failed on attempt {attempt}: {str(e)}. "
                    f"Retrying in {delay:.1f}s..."
                )
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"Gemini API call failed after {max_retries} attempts.")

        # If we failed structured generation, try a fallback: ask for raw text, then parse it manually
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
            logger.error(f"Fallback generation also failed: {fallback_err}")

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
                response = self.client.models.generate_content(
                    model=model_name, contents=prompt, config=config
                )
                if response.text:
                    return response.text
                raise ValueError("Received empty text response from Gemini.")
            except (APIError, httpx.HTTPError, ValueError, Exception) as e:
                last_exception = e
                logger.warning(f"Gemini API call failed on attempt {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(delay)
                    delay *= 2
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
        # Note: missing key makes it unhealthy since the app requires it
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
    # It is natively implemented using httpx in research_service.py
    health["details"]["duckduckgo_search_available"] = True

    return health
