from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings
from typing import Optional
import logging
from functools import lru_cache

class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from the environment and the token file.
    """
    TOKEN_STORAGE_FILE: str = ".dropbox.token"

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

    @model_validator(mode='before')
    def clean_and_validate_storage_provider_settings(cls, values):
        provider = values.get('STORAGE_PROVIDER')
        if not provider:
            # If STORAGE_PROVIDER is not in the .env file at all, let BaseSettings handle its default or error.
            return values

        if provider == "dropbox":
            # Ensure Dropbox specific fields are present and remove GDrive specific fields
            required_dropbox_keys = ["DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_SOURCE_DIR", "DROPBOX_DEST_DIR", "DROPBOX_FAILED_DIR"]
            
            # Check for refresh token, either via env var or file (which is handled later)
            has_refresh_token = (
                values.get("DROPBOX_REFRESH_TOKEN") is not None and str(values.get("DROPBOX_REFRESH_TOKEN")).strip() != ""
            )
            # The model_post_init handles DROPBOX_REFRESH_TOKEN_FILE as a fallback.
            # Here we only validate the env var. If neither env var nor file is present, the client will fail later.
            if not has_refresh_token:
                logging.warning("DROPBOX_REFRESH_TOKEN not found in environment. Will attempt to load from .dropbox.token file.")

            for key in required_dropbox_keys:
                if key == "DROPBOX_SOURCE_DIR":
                    # Allow empty string for source dir, which means Dropbox root
                    if values.get(key) is None:
                        raise ValueError(f"{key} is required when STORAGE_PROVIDER is 'dropbox'")
                elif not values.get(key) or not str(values.get(key)).strip():
                    raise ValueError(f"{key} is required and cannot be empty when STORAGE_PROVIDER is 'dropbox'")
            
            # Remove GDrive specific settings if they are present
            gdrive_keys = ["GDRIVE_CREDENTIALS_JSON", "GDRIVE_TOKEN_JSON", "GDRIVE_SOURCE_FOLDER_ID", "GDRIVE_DEST_FOLDER_ID", "GDRIVE_FAILED_FOLDER_ID"]
            for key in gdrive_keys:
                if key in values:
                    del values[key]

        elif provider == "gdrive":
            # Ensure GDrive specific fields are present and remove Dropbox specific fields
            required_gdrive_keys = ["GDRIVE_CREDENTIALS_JSON", "GDRIVE_TOKEN_JSON", "GDRIVE_SOURCE_FOLDER_ID", "GDRIVE_DEST_FOLDER_ID", "GDRIVE_FAILED_FOLDER_ID"]
            for key in required_gdrive_keys:
                if not values.get(key):
                    raise ValueError(f"{key} is required when STORAGE_PROVIDER is 'gdrive'")
            
            # Remove Dropbox specific settings if they are present
            dropbox_keys = ["DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "DROPBOX_REFRESH_TOKEN", "DROPBOX_SOURCE_DIR", "DROPBOX_DEST_DIR", "DROPBOX_FAILED_DIR"]
            for key in dropbox_keys:
                if key in values:
                    del values[key]

        else:
            raise ValueError("Invalid STORAGE_PROVIDER. Must be 'dropbox' or 'gdrive'.")
        
        return values

    def model_post_init(self, __context):
        """
        After initial settings are loaded from the environment,
        try to load a refresh token from the local token file as a fallback.
        """
        token_file = self.BASE_DIR / self.TOKEN_STORAGE_FILE
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
        return self.BASE_DIR.parent / "DejaVuSans.ttf"

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