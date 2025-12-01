from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import logging

TOKEN_STORAGE_FILE = ".dropbox.token"


# Define all settings in one class
class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from the environment and the token file.
    """

    # --- Secrets from .env ---
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"
    # The two potential sources for the refresh token. The application logic will decide the priority.
    DROPBOX_REFRESH_TOKEN_ENV: Optional[str] = Field(
        None, alias="DROPBOX_REFRESH_TOKEN"
    )
    DROPBOX_REFRESH_TOKEN_FILE: Optional[str] = None

    # --- Dropbox Paths (must be set in .env) ---
    DROPBOX_SOURCE_DIR: str
    DROPBOX_DEST_DIR: str
    DROPBOX_FAILED_DIR: str

    # --- AI Settings (must be set in .env) ---
    RECOGNITION_MODEL: str
    RECOGNITION_PROMPT: str
    PDF_DPI: int

    # --- Workflow Settings (must be set in .env) ---
    LOOP_SLEEP_SECONDS: int

    # --- Constants and Computed Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent

    def model_post_init(self, __context):
        """
        After initial settings are loaded from the environment,
        try to load a refresh token from the local token file as a fallback.
        """
        token_file = self.BASE_DIR / TOKEN_STORAGE_FILE
        if token_file.is_file():
            content = token_file.read_text().strip()
            if content:
                self.DROPBOX_REFRESH_TOKEN_FILE = content
                logging.info(f"Found refresh token in file: {token_file}")

    @property
    def LOCAL_BUF_DIR(self) -> Path:
        return self.BASE_DIR / "buf"

    @property
    def FONT_PATH(self) -> Path:
        return self.BASE_DIR / "DejaVuSans.ttf"

    @property
    def LOG_FILE(self) -> Path:
        return self.BASE_DIR / "app.log"


# Create a single settings instance for the entire application
settings = Settings()

# Create necessary directories on startup
settings.LOCAL_BUF_DIR.mkdir(exist_ok=True)
