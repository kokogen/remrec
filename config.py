from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from functools import lru_cache

TOKEN_STORAGE_FILE = ".dropbox.token"


# Define all settings in one class
class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from the environment and the token file.
    """

    # --- General Settings ---
    STORAGE_PROVIDER: str = "dropbox"  # "dropbox" or "gdrive"
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"

    # --- Dropbox Settings (optional) ---
    DROPBOX_APP_KEY: Optional[str] = None
    DROPBOX_APP_SECRET: Optional[str] = None
    DROPBOX_REFRESH_TOKEN_ENV: Optional[str] = Field(
        None, alias="DROPBOX_REFRESH_TOKEN"
    )
    DROPBOX_REFRESH_TOKEN_FILE: Optional[str] = None
    DROPBOX_SOURCE_DIR: Optional[str] = None
    DROPBOX_DEST_DIR: Optional[str] = None
    DROPBOX_FAILED_DIR: Optional[str] = None

    # --- Google Drive Settings (optional) ---
    GDRIVE_CREDENTIALS_JSON: Optional[str] = None
    GDRIVE_TOKEN_JSON: Optional[str] = None
    GDRIVE_SOURCE_FOLDER_ID: Optional[str] = None
    GDRIVE_DEST_FOLDER_ID: Optional[str] = None
    GDRIVE_FAILED_FOLDER_ID: Optional[str] = None

    # --- AI Settings (must be set in .env) ---
    RECOGNITION_MODEL: str = Field(
        "gemini-pro-vision", validation_alias="RECOGNITION_MODEL"
    )
    DROPBOX_UPLOAD_CHUNK_SIZE: int = Field(
        128 * 1024 * 1024, validation_alias="DROPBOX_UPLOAD_CHUNK_SIZE"
    )  # 128 MB default
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


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    The first call to this function will initialize the settings.
    """
    settings = Settings()
    settings.LOCAL_BUF_DIR.mkdir(exist_ok=True)
    return settings
