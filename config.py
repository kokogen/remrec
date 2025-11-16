# config.py
import os
from pathlib import Path
from dotenv import load_dotenv

# Корневая директория проекта
BASE_DIR = Path(__file__).resolve().parent

# Загружаем переменные окружения из .env файла
# Убедитесь, что .env файл существует в той же директории, что и этот скрипт
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Please create it.")


# --- Секреты ---
DROPBOX_APP_KEY = os.getenv("DROPBOX_APP_KEY")
DROPBOX_APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
DROPBOX_REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL")

# --- Пути в Dropbox ---
DROPBOX_SOURCE_DIR = "/"  # Папка, где ищем новые файлы
DROPBOX_DEST_DIR = "/txt"    # Папка для сохранения результатов

# --- Локальные пути (внутри контейнера) ---
LOCAL_BUF_DIR = BASE_DIR / "buf"
# Убедитесь, что шрифт DejaVuSans.ttf лежит в корне проекта
FONT_PATH = BASE_DIR / "DejaVuSans.ttf" 
LOCK_FILE_PATH = BASE_DIR / "app.lock"

# --- Настройки AI ---
RECOGNITION_MODEL = "gemini-2.5-flash"
RECOGNITION_PROMPT = "Распознай рукописный текст на изображении."

# --- Настройки логирования ---
LOG_FILE = BASE_DIR / "app.log"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Создаем необходимые директории
LOCAL_BUF_DIR.mkdir(exist_ok=True)
