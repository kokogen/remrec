# tests/conftest.py
import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Since we refactored config.py, we can now safely import the Settings class
# without triggering the validation error.
from src.config import Settings, get_settings


@pytest.fixture
def mock_settings():
    """
    Provides a mock of the application settings for testing.
    This avoids the need for environment variables during tests.
    """
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "dropbox"
    settings.DROPBOX_APP_KEY = "test_key"
    settings.DROPBOX_APP_SECRET = "test_secret"
    settings.OPENAI_API_KEY = "test_api_key"
    settings.OPENAI_BASE_URL = "https://api.openai.com/v1"
    settings.DROPBOX_SOURCE_DIR = "/source"
    settings.DROPBOX_DEST_DIR = "/dest"
    settings.DROPBOX_FAILED_DIR = "/failed"
    settings.RECOGNITION_MODEL = "gpt-4"
    settings.RECOGNITION_PROMPT = "test prompt"
    settings.PDF_DPI = 300
    settings.LOOP_SLEEP_SECONDS = 1
    settings.DROPBOX_UPLOAD_CHUNK_SIZE = 1024
    settings.BASE_DIR = Path("/tmp")
    settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    settings.FONT_PATH = Path("/tmp/font.ttf")
    settings.LOG_FILE = Path("/tmp/app.log")

    # --- Mock Path objects ---
    # Create a MagicMock for the FONT_PATH attribute
    mock_font_path = MagicMock(spec=Path)
    mock_font_path.exists.return_value = True
    mock_font_path.__str__.return_value = (
        "/tmp/font.ttf"  # To satisfy str() calls if any
    )
    settings.FONT_PATH = mock_font_path

    settings.BASE_DIR = Path("/tmp")
    settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    settings.LOG_FILE = Path("/tmp/app.log")

    return settings


@pytest.fixture
def mock_storage_client():
    """Fixture for a mock storage client."""
    return MagicMock()


@pytest.fixture(autouse=True)
def patch_settings_class(monkeypatch, mock_settings):
    """
    This autouse fixture automatically replaces the `Settings` class constructor.
    Any part of the app code that calls `Settings()` during a test run will
    receive the `mock_settings` instance instead of a real settings object.
    This is a robust way to ensure no real settings are ever loaded.
    """
    # We also need to clear the cache on get_settings, because it might have been
    # called and cached a real instance during test collection.
    get_settings.cache_clear()
    monkeypatch.setattr("src.config.Settings", lambda *args, **kwargs: mock_settings)
