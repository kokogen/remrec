from openai import OpenAI
import base64
import io

client = OpenAI(
  base_url="https://neuroapi.host/v1",
  api_key="sk-x8po9rlu5sZD9ihq511x2XeZzeLCPgobOall5Jvlw3L1zWGa",
)

def image_to_base64(img):
    buffered = io.BytesIO()
    img.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode()

def recognize(img_base64):
    completion = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Распознай рукописный текст на изображении."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_base64}"}}
                ]
            }
        ]
    )
    return completion.choices[0].message.content



