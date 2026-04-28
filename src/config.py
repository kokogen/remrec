from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any, Literal, Optional
import logging
from functools import lru_cache
import os
import tempfile


class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from the environment and the token file.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- General Settings ---
    STORAGE_PROVIDER: Literal["dropbox", "gdrive"] = "dropbox"
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    OPENAI_TIMEOUT_SECONDS: float = Field(120.0, gt=0)
    OPENAI_MAX_RETRIES: int = Field(2, ge=0)
    LOG_LEVEL: str = "INFO"

    # --- Dynamic Provider-Specific Settings (set by validator) ---
    SRC_FOLDER: Optional[str] = None
    DST_FOLDER: Optional[str] = None
    FAILED_FOLDER: Optional[str] = None

    # --- Dropbox Settings (optional) ---
    DROPBOX_APP_KEY: Optional[str] = None
    DROPBOX_APP_SECRET: Optional[str] = None
    DROPBOX_REFRESH_TOKEN: Optional[str] = None
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
    RECOGNITION_MAX_TEXT_CHARS: int = Field(100_000, gt=0)
    RECOGNITION_PROMPT: str
    PDF_DPI: int

    # --- Workflow Settings (must be set in .env) ---
    LOOP_SLEEP_SECONDS: int

    # --- Constants and Computed Paths ---
    BASE_DIR: Path = Path(__file__).resolve().parent.parent  # Project root
    TOKEN_STORAGE_FILE: Path = BASE_DIR / ".dropbox.token"
    LOCAL_BUF_DIR: Path = Path(tempfile.gettempdir()) / "remrec"

    def _set_provider_folders(self) -> None:
        if self.STORAGE_PROVIDER == "dropbox":
            self.SRC_FOLDER = self.DROPBOX_SOURCE_DIR
            self.DST_FOLDER = self.DROPBOX_DEST_DIR
            self.FAILED_FOLDER = self.DROPBOX_FAILED_DIR

            # Perform validation
            if not self.DROPBOX_APP_KEY:
                raise ValueError("For Dropbox, APP_KEY must be set.")
            if not self.DROPBOX_APP_SECRET:
                raise ValueError("For Dropbox, APP_SECRET must be set.")
            if self.DROPBOX_SOURCE_DIR is None:  # Can be empty string, but not None
                raise ValueError(
                    "For Dropbox, SOURCE_DIR must be set (can be empty for root)."
                )
            if not self.DST_FOLDER:  # DST_FOLDER gets value from DROPBOX_DEST_DIR
                raise ValueError("For Dropbox, DEST_FOLDER must be set.")
            if (
                not self.FAILED_FOLDER
            ):  # FAILED_FOLDER gets value from DROPBOX_FAILED_DIR
                raise ValueError("For Dropbox, FAILED_FOLDER must be set.")

        elif self.STORAGE_PROVIDER == "gdrive":
            self.SRC_FOLDER = self.GDRIVE_SOURCE_FOLDER_ID
            self.DST_FOLDER = self.GDRIVE_DEST_FOLDER_ID
            self.FAILED_FOLDER = self.GDRIVE_FAILED_FOLDER_ID
            if not all(
                [
                    self.GDRIVE_CREDENTIALS_JSON,
                    self.GDRIVE_TOKEN_JSON,
                    self.SRC_FOLDER,
                    self.DST_FOLDER,
                    self.FAILED_FOLDER,
                ]
            ):
                raise ValueError(
                    "For Google Drive, CREDENTIALS_JSON, TOKEN_JSON and all FOLDER_IDs must be set."
                )

    def model_post_init(self, __context: Any) -> None:
        """Load Dropbox token from file if it exists and run validations."""
        # Ensure base directories are set first
        self._set_provider_folders()

        # Centralize Dropbox token resolution and validation
        if self.STORAGE_PROVIDER == "dropbox":
            env_token = os.getenv("DROPBOX_REFRESH_TOKEN")
            if env_token:
                self.DROPBOX_REFRESH_TOKEN = env_token
                logging.debug("Using Dropbox token from environment variable.")
            elif self.TOKEN_STORAGE_FILE.is_file():
                self.DROPBOX_REFRESH_TOKEN = self.TOKEN_STORAGE_FILE.read_text().strip()
                logging.info(
                    f"Loaded Dropbox refresh token from {self.TOKEN_STORAGE_FILE}"
                )
            else:
                raise ValueError(
                    "Dropbox refresh token not found in DROPBOX_REFRESH_TOKEN env var or in .dropbox.token file. "
                    "Please run `python src/auth.py` to generate one."
                )

    @property
    def FONT_PATH(self) -> Path:
        return self.BASE_DIR / "DejaVuSans.ttf"


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached instance of the application settings.
    The first call to this function will initialize the settings.
    """
    settings = Settings()
    logging.info("--- Application Settings Summary ---")
    logging.info(f"STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")
    logging.info(f"RECOGNITION_MODEL: {settings.RECOGNITION_MODEL}")
    logging.info(f"LOOP_SLEEP_SECONDS: {settings.LOOP_SLEEP_SECONDS}")
    logging.info(f"LOG_LEVEL: {settings.LOG_LEVEL}")
    logging.info("------------------------------------")

    # Create buffer directory if it doesn't exist.
    settings.LOCAL_BUF_DIR.mkdir(parents=True, exist_ok=True)
    return settings
