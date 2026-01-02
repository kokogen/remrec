from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import Optional, Any
import logging
from functools import lru_cache

class Settings(BaseSettings):
    """
    Centralized application configuration.
    It defines general settings and then provider-specific ones.
    The validator ensures that the correct folder paths/IDs are assigned
    to the generic SRC_FOLDER, DST_FOLDER, and FAILED_FOLDER attributes.
    """
    # --- General Settings ---
    STORAGE_PROVIDER: str = "dropbox"
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"
    RECOGNITION_MODEL: str = "gemini-pro-vision"
    RECOGNITION_PROMPT: str
    PDF_DPI: int = 200
    LOOP_SLEEP_SECONDS: int = 60

    # --- Generic Folder Settings (populated by validator) ---
    SRC_FOLDER: str = ""
    DST_FOLDER: str = ""
    FAILED_FOLDER: str = ""

    # --- Dropbox Settings ---
    DROPBOX_APP_KEY: Optional[str] = None
    DROPBOX_APP_SECRET: Optional[str] = None
    DROPBOX_REFRESH_TOKEN_ENV: Optional[str] = Field(None, alias="DROPBOX_REFRESH_TOKEN")
    DROPBOX_REFRESH_TOKEN_FILE: Optional[str] = None
    DROPBOX_SOURCE_DIR: Optional[str] = "/"
    DROPBOX_DEST_DIR: Optional[str] = "/processed"
    DROPBOX_FAILED_DIR: Optional[str] = "/failed"
    DROPBOX_UPLOAD_CHUNK_SIZE: int = 128 * 1024 * 1024

    # --- Google Drive Settings ---
    GDRIVE_CREDENTIALS_JSON: Optional[str] = None
    GDRIVE_TOKEN_JSON: Optional[str] = None
    GDRIVE_SOURCE_FOLDER_ID: Optional[str] = None
    GDRIVE_DEST_FOLDER_ID: Optional[str] = None
    GDRIVE_FAILED_FOLDER_ID: Optional[str] = None

    # --- Constants and Computed Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent # Project root
    TOKEN_STORAGE_FILE: Path = BASE_DIR / ".dropbox.token"

    @model_validator(mode='after')
    def set_provider_folders(self) -> 'Settings':
        if self.STORAGE_PROVIDER == 'dropbox':
            self.SRC_FOLDER = self.DROPBOX_SOURCE_DIR
            self.DST_FOLDER = self.DROPBOX_DEST_DIR
            self.FAILED_FOLDER = self.DROPBOX_FAILED_DIR

            # DEBUG LOGGING
            logging.info(f"DEBUG: Initial DROPBOX_SOURCE_DIR = '{self.DROPBOX_SOURCE_DIR}'")
            logging.info(f"DEBUG: SRC_FOLDER set to = '{self.SRC_FOLDER}'")

            # Perform validation
            if not self.DROPBOX_APP_KEY:
                raise ValueError("For Dropbox, APP_KEY must be set.")
            if not self.DROPBOX_APP_SECRET:
                raise ValueError("For Dropbox, APP_SECRET must be set.")
            if self.DROPBOX_SOURCE_DIR is None: # Can be empty string, but not None
                raise ValueError("For Dropbox, SOURCE_DIR must be set (can be empty for root).")
            if not self.DST_FOLDER: # DST_FOLDER gets value from DROPBOX_DEST_DIR
                raise ValueError("For Dropbox, DEST_FOLDER must be set.")
            if not self.FAILED_FOLDER: # FAILED_FOLDER gets value from DROPBOX_FAILED_DIR
                raise ValueError("For Dropbox, FAILED_FOLDER must be set.")

            if not (self.DROPBOX_REFRESH_TOKEN_ENV or self.TOKEN_STORAGE_FILE.exists()):
                 logging.warning("Dropbox refresh token not found in env or file.")

        elif self.STORAGE_PROVIDER == 'gdrive':
            self.SRC_FOLDER = self.GDRIVE_SOURCE_FOLDER_ID
            self.DST_FOLDER = self.GDRIVE_DEST_FOLDER_ID
            self.FAILED_FOLDER = self.GDRIVE_FAILED_FOLDER_ID
            if not all([self.GDRIVE_CREDENTIALS_JSON, self.GDRIVE_TOKEN_JSON, self.SRC_FOLDER, self.DST_FOLDER, self.FAILED_FOLDER]):
                raise ValueError("For Google Drive, CREDENTIALS_JSON, TOKEN_JSON and all FOLDER_IDs must be set.")
        else:
            raise ValueError("Invalid STORAGE_PROVIDER. Must be 'dropbox' or 'gdrive'.")
        return self

    def model_post_init(self, __context: Any) -> None:
        """Load Dropbox token from file if it exists."""
        if self.TOKEN_STORAGE_FILE.is_file():
            self.DROPBOX_REFRESH_TOKEN_FILE = self.TOKEN_STORAGE_FILE.read_text().strip()
            logging.info(f"Loaded Dropbox refresh token from {self.TOKEN_STORAGE_FILE}")

    @property
    def LOCAL_BUF_DIR(self) -> Path:
        return self.BASE_DIR / "src" / "buf"

    @property
    def FONT_PATH(self) -> Path:
        return self.BASE_DIR / "DejaVuSans.ttf"

    @property
    def LOG_FILE(self) -> Path:
        return self.BASE_DIR / "app.log"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    The first call to this function will initialize the settings.
    """
    settings = Settings()
    logging.info("--- Loaded Application Settings ---")
    for key, value in settings.model_dump().items():
        if any(s in key.lower() for s in ["key", "secret", "token"]):
            logging.info(f"{key}: **********")
        else:
            logging.info(f"{key}: {value}")
    logging.info("------------------------------------")
    
    # Create buffer directory if it doesn't exist.
    (settings.BASE_DIR / "src" / "buf").mkdir(exist_ok=True)
    return settings
