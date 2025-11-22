# config.py
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# Define all settings in one class
class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from a .env file.
    """
    # --- Secrets from .env ---
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    DROPBOX_REFRESH_TOKEN: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"

    # --- Dropbox Paths (can be overridden in .env) ---
    DROPBOX_SOURCE_DIR: str = ""
    DROPBOX_DEST_DIR: str = "/rm2"
    DROPBOX_FAILED_DIR: str = "/failed_files"

    # --- AI Settings (can be overridden in .env) ---
    RECOGNITION_MODEL: str = "gemini-2.5-flash"
    RECOGNITION_PROMPT: str = "Recognize the handwritten text in the image."
    PDF_DPI: int = 200

    # --- Workflow Settings (can be overridden in .env) ---
    LOCK_TIMEOUT: int = 5

    # --- Constants and Computed Paths ---
    # These fields are not read from .env but are computed on the fly
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

    # Pydantic configuration to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

# Create a single settings instance for the entire application
settings = Settings()

# Create necessary directories on startup
settings.LOCAL_BUF_DIR.mkdir(exist_ok=True)
