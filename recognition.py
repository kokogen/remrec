# recognition.py
import base64
import io
import logging
from openai import OpenAI
from config import get_settings


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
    try:
        client = OpenAI(
            base_url=settings.OPENAI_BASE_URL, api_key=settings.OPENAI_API_KEY
        )
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
