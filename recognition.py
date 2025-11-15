# recognition.py
import base64
import io
import logging
from openai import OpenAI
import config

try:
    client = OpenAI(
        base_url=config.OPENAI_BASE_URL,
        api_key=config.OPENAI_API_KEY
    )
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    # Если клиент не инициализируется, нет смысла продолжать
    raise

def image_to_base64(img):
    """Кодирует объект изображения PIL в строку Base64."""
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def recognize(img_base64: str) -> str:
    """
    Отправляет изображение в API для распознавания текста.

    :param img_base64: Изображение, закодированное в Base64.
    :return: Распознанный текст.
    """
    try:
        logging.info("Sending image to recognition API...")
        completion = client.chat.completions.create(
            model=config.RECOGNITION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": config.RECOGNITION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}
                        }
                    ]
                }
            ]
        )
        logging.info("Recognition successful.")
        return completion.choices[0].message.content
    except Exception as e:
        logging.error(f"Recognition API call failed: {e}", exc_info=True)
        # Пробрасываем ошибку выше, чтобы основной цикл мог ее обработать
        raise