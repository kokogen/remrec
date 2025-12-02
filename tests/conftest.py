# tests/conftest.py
import pytest
from unittest.mock import MagicMock
from pathlib import Path

# Since we refactored config.py, we can now safely import the Settings class
# without triggering the validation error.
from config import Settings

@pytest.fixture
def mock_settings():
    """
    Provides a mock of the application settings for testing.
    This avoids the need for environment variables during tests.
    """
    settings = MagicMock(spec=Settings)
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
    settings.BASE_DIR = Path("/tmp")
    settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    settings.FONT_PATH = Path("/tmp/font.ttf")
    settings.LOG_FILE = Path("/tmp/app.log")
    
    # Mock the .exists() method for paths
    settings.FONT_PATH.exists.return_value = True
    
    return settings

@pytest.fixture(autouse=True)
def patch_get_settings(monkeypatch, mock_settings):
    """
    This autouse fixture automatically replaces `get_settings()` with a function
    that returns our `mock_settings` instance. This means any part of the app
    code that calls `get_settings()` during a test run will receive the
    mocked settings.
    """
    monkeypatch.setattr("config.get_settings", lambda: mock_settings)
