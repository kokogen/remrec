from pathlib import Path
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
import logging

TOKEN_STORAGE_FILE = ".dropbox.token"

# Define all settings in one class
class Settings(BaseSettings):
    """
    Centralized application configuration with type validation.
    Automatically reads variables from a .env file and the token file.
    """
    # --- Secrets from .env ---
    DROPBOX_APP_KEY: str
    DROPBOX_APP_SECRET: str
    OPENAI_API_KEY: str
    OPENAI_BASE_URL: str
    LOG_LEVEL: str = "INFO"
    DROPBOX_REFRESH_TOKEN: Optional[str] = None

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
    
    @model_validator(mode='after')
    def load_refresh_token(self) -> 'Settings':
        """Load refresh token from file, falling back to environment variable."""
        token_file = self.BASE_DIR / TOKEN_STORAGE_FILE
        
        refresh_token_from_file = None
        if token_file.is_file():
            content = token_file.read_text().strip()
            if content: # Only load if file is not empty
                refresh_token_from_file = content
                logging.info(f"Loading refresh token from file: {token_file}")
            else:
                logging.warning(f"Dropbox token file '{TOKEN_STORAGE_FILE}' exists but is empty. Checking environment variable.")

        if refresh_token_from_file:
            self.DROPBOX_REFRESH_TOKEN = refresh_token_from_file
        elif self.DROPBOX_REFRESH_TOKEN: # Already set from .env
             logging.warning("Loading refresh token from environment variable. Consider using the auth.py script for better security.")
        
        if not self.DROPBOX_REFRESH_TOKEN:
            raise ValueError(
                "Dropbox refresh token not found. "
                f"Please run 'python auth.py' to generate it and save it to '{TOKEN_STORAGE_FILE}' "
                "or ensure DROPBOX_REFRESH_TOKEN is set in your .env file."
            )
        return self

    @property
    def LOCAL_BUF_DIR(self) -> Path:
        return self.BASE_DIR / "buf"

    @property
    def FONT_PATH(self) -> Path:
        return self.BASE_DIR / "DejaVuSans.ttf"

    @property
    def LOG_FILE(self) -> Path:
        return self.BASE_DIR / "app.log"

    # Pydantic configuration to read from the .env file
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra='ignore')

# Create a single settings instance for the entire application
settings = Settings()

# Create necessary directories on startup
settings.LOCAL_BUF_DIR.mkdir(exist_ok=True)
