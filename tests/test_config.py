# tests/test_config.py
import pytest
from pydantic import ValidationError
from src.config import Settings


def test_settings_dropbox_missing_source_dir_raises_error(monkeypatch):
    """
    Ensures that if STORAGE_PROVIDER is 'dropbox', a ValueError is raised
    if DROPBOX_SOURCE_DIR is not provided. This test catches configuration
    errors that could lead to the app scanning the wrong directory.
    """
    # Temporarily remove the env var if it exists to ensure a clean test
    monkeypatch.delenv("DROPBOX_SOURCE_DIR", raising=False)

    with pytest.raises(ValidationError) as excinfo:
        Settings(
            STORAGE_PROVIDER="dropbox",
            OPENAI_API_KEY="test",
            OPENAI_BASE_URL="test",
            RECOGNITION_PROMPT="test",
            PDF_DPI=200,
            LOOP_SLEEP_SECONDS=120,
            DROPBOX_APP_KEY="test",
            DROPBOX_APP_SECRET="test",
            DROPBOX_DEST_DIR="/dest",
            DROPBOX_FAILED_DIR="/failed",
            # DROPBOX_SOURCE_DIR is intentionally omitted
        )
    # Check that the validation error is for the right reason
    assert "For Dropbox, SOURCE_DIR must be set" in str(excinfo.value)


def test_settings_dropbox_valid_config_succeeds():
    """
    Ensures that a valid Dropbox configuration passes validation.
    """
    try:
        Settings(
            STORAGE_PROVIDER="dropbox",
            OPENAI_API_KEY="test",
            OPENAI_BASE_URL="test",
            RECOGNITION_PROMPT="test",
            PDF_DPI=200,
            LOOP_SLEEP_SECONDS=120,
            DROPBOX_APP_KEY="test",
            DROPBOX_APP_SECRET="test",
            DROPBOX_SOURCE_DIR="/source",
            DROPBOX_DEST_DIR="/dest",
            DROPBOX_FAILED_DIR="/failed",
        )
    except ValidationError as e:
        pytest.fail(f"Valid Dropbox configuration failed validation: {e}")
