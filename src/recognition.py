# recognition.py
import base64
import io
import logging
import openai
from openai import OpenAI
from .config import get_settings
from .exceptions import (
    RecognitionAuthError,
    RecognitionPermanentError,
    RecognitionTransientError,
)

# Global variable to hold the client instance.
# Using a private-like name to discourage direct access.
_client: OpenAI | None = None


def get_openai_client() -> OpenAI:
    """
    Initializes and returns the OpenAI client, caching it for subsequent calls.
    This "lazy loading" pattern prevents the client from being created at
    module import time, which is crucial for testing.
    """
    global _client
    if _client is None:
        logging.info("Initializing OpenAI client for the first time.")
        settings = get_settings()
        _client = OpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY,
            timeout=settings.OPENAI_TIMEOUT_SECONDS,
            max_retries=settings.OPENAI_MAX_RETRIES,
        )
    return _client


def image_to_base64(img):
    """Encodes a PIL image object into a Base64 string."""
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


def _extract_recognized_text(completion, max_text_chars: int) -> str:
    """Extracts and validates recognized text from a chat completion response."""
    try:
        content = completion.choices[0].message.content
    except (AttributeError, IndexError) as e:
        raise RecognitionPermanentError(
            "Recognition API returned malformed response"
        ) from e

    if not isinstance(content, str):
        raise RecognitionPermanentError("Recognition API returned non-text content")

    text = content.strip()
    if not text:
        raise RecognitionPermanentError("Recognition API returned empty text")

    if len(text) > max_text_chars:
        raise RecognitionPermanentError(
            f"Recognition API returned too much text ({len(text)} chars)"
        )

    return text


def recognize(img_base64: str) -> str:
    """
    Sends an image to the recognition API.

    :param img_base64: Base64 encoded image.
    :return: Recognized text.
    """
    settings = get_settings()
    client = get_openai_client()

    logging.info("Sending image to recognition API...")
    try:
        completion = client.chat.completions.create(
            model=settings.RECOGNITION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": settings.RECOGNITION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{img_base64}"
                            },
                        },
                    ],
                }
            ],
        )
    except openai.APIConnectionError as e:
        raise RecognitionTransientError("Recognition API connection error") from e
    except openai.RateLimitError as e:
        raise RecognitionTransientError("Recognition API rate limit exceeded") from e
    except openai.APITimeoutError as e:
        raise RecognitionTransientError("Recognition API timeout") from e
    except openai.InternalServerError as e:
        raise RecognitionTransientError("Recognition API server error") from e
    except openai.AuthenticationError as e:
        raise RecognitionAuthError("Recognition API authentication failed") from e
    except openai.PermissionDeniedError as e:
        raise RecognitionAuthError("Recognition API permission denied") from e
    except openai.BadRequestError as e:
        raise RecognitionPermanentError(
            f"Recognition API bad request (invalid image or prompt): {e}"
        ) from e
    except openai.APIStatusError as e:
        if e.status_code >= 500 or e.status_code in {408, 409, 429}:
            raise RecognitionTransientError(
                f"Recognition API transient status {e.status_code}"
            ) from e
        raise RecognitionPermanentError(
            f"Recognition API permanent status {e.status_code}: {e}"
        ) from e
    except openai.OpenAIError as e:
        raise RecognitionTransientError(f"Recognition API error: {e}") from e

    content = _extract_recognized_text(
        completion, max_text_chars=settings.RECOGNITION_MAX_TEXT_CHARS
    )

    logging.info("Recognition successful.")
    return content
