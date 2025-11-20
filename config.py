# config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Определяем все настройки в одном классе
class Settings(BaseSettings):
    """
    Централизованная конфигурация приложения с валидацией типов.
    Автоматически читает переменные из .env файла.
    """
    # --- Секреты из .env ---
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    DROPBOX_REFRESH_TOKEN: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"

    # --- Пути в Dropbox (можно переопределить в .env) ---
    DROPBOX_SOURCE_DIR: str = ""
    DROPBOX_DEST_DIR: str = "/rm2"
    DROPBOX_FAILED_DIR: str = "/failed_files"

    # --- Настройки AI (можно переопределить в .env) ---
    RECOGNITION_MODEL: str = "gemini-2.5-flash"
    RECOGNITION_PROMPT: str = "Распознай рукописный текст на изображении."
    PDF_DPI: int = 200

    # --- Константы и вычисляемые пути ---
    # Эти поля не читаются из .env, а вычисляются на лету
    BASE_DIR: Path = Path(__file__).resolve().parent
    
    @property
    def LOCAL_BUF_DIR(self) -> Path:
        return self.BASE_DIR / "buf"

    @property
    def FONT_PATH(self) -> Path:
        return self.BASE_DIR / "DejaVuSans.ttf"

    @property
    def LOCK_FILE_PATH(self) -> Path:
        return self.BASE_DIR / "app.lock"

    @property
    def LOG_FILE(self) -> Path:
        return self.BASE_DIR / "app.log"

    # Конфигурация Pydantic для чтения из .env файла
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

# Создаем единственный экземпляр настроек для всего приложения
settings = Settings()

# Создаем необходимые директории при старте
settings.LOCAL_BUF_DIR.mkdir(exist_ok=True)