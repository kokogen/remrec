# tests/test_config.py
import pytest
from pydantic import ValidationError
from src.config import Settings
from unittest.mock import patch


@pytest.fixture
def base_dropbox_settings_data():
    """Provides a base dictionary for valid Dropbox settings."""
    return {
        "STORAGE_PROVIDER": "dropbox",
        "OPENAI_API_KEY": "test",
        "OPENAI_BASE_URL": "test",
        "RECOGNITION_PROMPT": "test",
        "PDF_DPI": 200,
        "LOOP_SLEEP_SECONDS": 120,
        "DROPBOX_APP_KEY": "test",
        "DROPBOX_APP_SECRET": "test",
        "DROPBOX_SOURCE_DIR": "/source",
        "DROPBOX_DEST_DIR": "/dest",
        "DROPBOX_FAILED_DIR": "/failed",
    }


@patch("os.getenv", return_value=None)
@patch("src.config.Path.is_file", return_value=False)
def test_settings_dropbox_missing_refresh_token_raises_error(
    mock_is_file, mock_getenv, base_dropbox_settings_data
):
    """
    Ensures that a ValueError is raised if the Dropbox refresh token is not found
    in either environment variables or the token file.
    """
    with pytest.raises(ValueError, match="Dropbox refresh token not found"):
        Settings(**base_dropbox_settings_data)


@patch("os.getenv")
@patch("src.config.Path.is_file", return_value=False)
def test_settings_dropbox_token_from_env_succeeds(
    mock_is_file, mock_getenv, base_dropbox_settings_data
):
    """
    Ensures the Dropbox refresh token is correctly loaded from environment variables.
    """
    mock_getenv.return_value = "env_token_value"

    settings = Settings(**base_dropbox_settings_data)
    assert settings.DROPBOX_REFRESH_TOKEN == "env_token_value"
    mock_getenv.assert_called_once_with("DROPBOX_REFRESH_TOKEN")
    mock_is_file.assert_not_called()  # Should not be called if env var is present


@patch("os.getenv", return_value=None)  # Ensure no env var
@patch("src.config.Path.is_file")
@patch("src.config.Path.read_text")
def test_settings_dropbox_token_from_file_succeeds(
    mock_read_text, mock_is_file, mock_getenv, base_dropbox_settings_data
):
    """
    Ensures the Dropbox refresh token is correctly loaded from the token file.
    """
    mock_is_file.return_value = True
    mock_read_text.return_value = "file_token_value"

    settings = Settings(**base_dropbox_settings_data)
    assert settings.DROPBOX_REFRESH_TOKEN == "file_token_value"
    mock_getenv.assert_called_once_with("DROPBOX_REFRESH_TOKEN")
    mock_is_file.assert_called_once()
    mock_read_text.assert_called_once()


@patch("os.getenv")
@patch("src.config.Path.is_file")
@patch("src.config.Path.read_text")
def test_settings_dropbox_env_token_has_precedence(
    mock_read_text, mock_is_file, mock_getenv, base_dropbox_settings_data
):
    """
    Ensures the environment variable token takes precedence over the file token.
    """
    mock_getenv.return_value = "env_token_value"
    mock_is_file.return_value = True
    mock_read_text.return_value = "file_token_value"

    settings = Settings(**base_dropbox_settings_data)
    assert settings.DROPBOX_REFRESH_TOKEN == "env_token_value"
    mock_getenv.assert_called_once_with("DROPBOX_REFRESH_TOKEN")
    mock_is_file.assert_not_called()  # Not called because env var takes precedence


@patch("os.getenv", return_value="test_token")  # Ensure token is present
@patch("src.config.Path.is_file", return_value=False)
def test_settings_dropbox_missing_source_dir_raises_error(
    mock_is_file, mock_getenv, monkeypatch, base_dropbox_settings_data
):
    """
    Ensures that a ValueError is raised if DROPBOX_SOURCE_DIR is not provided.
    """
    monkeypatch.delenv("DROPBOX_SOURCE_DIR", raising=False)
    data = base_dropbox_settings_data.copy()
    data.pop("DROPBOX_SOURCE_DIR")

    with pytest.raises(ValueError, match="For Dropbox, SOURCE_DIR must be set"):
        Settings(**data)


@patch("os.getenv", return_value="test_token")  # Ensure token is present
@patch("src.config.Path.is_file", return_value=False)
def test_settings_dropbox_valid_config_succeeds(
    mock_is_file, mock_getenv, base_dropbox_settings_data
):
    """
    Ensures that a valid Dropbox configuration passes validation.
    """
    try:
        Settings(**base_dropbox_settings_data)
    except ValidationError as e:
        pytest.fail(f"Valid Dropbox configuration failed validation: {e}")
