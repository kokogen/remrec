# recognition.py
import base64
import io
import logging
from openai import OpenAI
from .config import get_settings

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
            base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY
        )
    return _client


def image_to_base64(img):
    """Encodes a PIL image object into a Base64 string."""
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()


def recognize(img_base64: str) -> str:
    """
    Sends an image to the recognition API.

    :param img_base64: Base64 encoded image.
    :return: Recognized text.
    """
    settings = get_settings()
    client = get_openai_client()

    try:
        logging.info("Sending image to recognition API...")
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
        logging.info("Recognition successful.")
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Recognition API call failed: {e}", exc_info=True)
        # Re-raise the error for the main loop to handle
        raise
