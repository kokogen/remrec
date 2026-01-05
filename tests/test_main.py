# tests/test_main.py
from unittest.mock import patch, MagicMock
from src.main import initialize_storage_client
from src.config import Settings
from src.dbox import DropboxClient
import dropbox.exceptions


@patch("src.dbox.dropbox.Dropbox")  # Patch the actual Dropbox API client
def test_initialize_storage_client_dropbox_success(MockDropbox):
    """
    Ensures initialize_storage_client correctly initializes DropboxClient
    and returns a tuple of 4 elements on success.
    """
    # Arrange
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "dropbox"
    settings.DROPBOX_SOURCE_DIR = "/source"
    settings.DROPBOX_DEST_DIR = "/dest"
    settings.DROPBOX_FAILED_DIR = "/failed"
    type(settings).DROPBOX_APP_KEY = "test_key"
    type(settings).DROPBOX_APP_SECRET = "test_secret"
    type(settings).DROPBOX_REFRESH_TOKEN = "some_token"

    mock_dbx_instance = MockDropbox.return_value
    mock_dbx_instance.users_get_current_account.return_value = (
        MagicMock()
    )  # Simulate successful auth

    # Action
    storage_client, source_path, dest_path, failed_path = initialize_storage_client(
        settings
    )

    # Assert
    assert isinstance(storage_client, DropboxClient)
    assert source_path == "/source"
    assert dest_path == "/dest"
    assert failed_path == "/failed"
    MockDropbox.assert_called_once_with(
        app_key="test_key",
        app_secret="test_secret",
        oauth2_refresh_token="some_token",
    )
    mock_dbx_instance.users_get_current_account.assert_called_once()


@patch("src.dbox.dropbox.Dropbox")  # Patch the actual Dropbox API client
@patch("src.main.logging")
def test_initialize_storage_client_dropbox_auth_error(MockLogging, MockDropbox):
    """
    Ensures initialize_storage_client handles Dropbox AuthError during initialization.
    """
    # Arrange
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "dropbox"
    settings.DROPBOX_SOURCE_DIR = "/source"
    settings.DROPBOX_DEST_DIR = "/dest"
    settings.DROPBOX_FAILED_DIR = "/failed"
    type(settings).DROPBOX_APP_KEY = "test_key"
    type(settings).DROPBOX_APP_SECRET = "test_secret"
    type(settings).DROPBOX_REFRESH_TOKEN = "invalid_token"

    mock_dbx_instance = MockDropbox.return_value
    mock_dbx_instance.users_get_current_account.side_effect = (
        dropbox.exceptions.AuthError("bad_auth", None)
    )

    # Action
    storage_client, _, _, _ = initialize_storage_client(settings)

    # Assert
    assert storage_client is None
    MockLogging.error.assert_called_once_with(
        "Dropbox authentication failed. Please check your token and app credentials. Error: AuthError('bad_auth', None)"
    )
    MockDropbox.assert_called_once()
    mock_dbx_instance.users_get_current_account.assert_called_once()


@patch("src.dbox.dropbox.Dropbox")  # Patch the actual Dropbox API client
@patch("src.main.logging")
def test_initialize_storage_client_dropbox_generic_exception(MockLogging, MockDropbox):
    """
    Ensures initialize_storage_client handles generic exceptions during Dropbox initialization.
    """
    # Arrange
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "dropbox"
    settings.DROPBOX_SOURCE_DIR = "/source"
    settings.DROPBOX_DEST_DIR = "/dest"
    settings.DROPBOX_FAILED_DIR = "/failed"
    type(settings).DROPBOX_APP_KEY = "test_key"
    type(settings).DROPBOX_APP_SECRET = "test_secret"
    type(settings).DROPBOX_REFRESH_TOKEN = "some_token"

    mock_dbx_instance = MockDropbox.return_value
    mock_dbx_instance.users_get_current_account.side_effect = ValueError(
        "network error"
    )

    # Action
    storage_client, _, _, _ = initialize_storage_client(settings)

    # Assert
    assert storage_client is None
    MockLogging.error.assert_called_once_with(
        "Failed to initialize Dropbox client due to an unexpected error: network error",
        exc_info=True,
    )
    MockDropbox.assert_called_once()
    mock_dbx_instance.users_get_current_account.assert_called_once()


@patch("src.main._init_gdrive_client")
def test_initialize_storage_client_gdrive_returns_tuple(mock_init_gdrive):
    """
    Ensures initialize_storage_client returns a tuple of 4 elements
    for the Google Drive provider.
    """
    # Arrange
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "gdrive"
    settings.GDRIVE_SOURCE_FOLDER_ID = "gdrive_source"
    settings.GDRIVE_DEST_FOLDER_ID = "gdrive_dest"
    settings.GDRIVE_FAILED_FOLDER_ID = "gdrive_failed"
    mock_gdrive_client = MagicMock()
    mock_init_gdrive.return_value = mock_gdrive_client

    # Action
    result = initialize_storage_client(settings)

    # Assert
    assert isinstance(result, tuple), "Should return a tuple"
    assert len(result) == 4, "Tuple should have 4 elements (client, src, dst, failed)"
    assert result[0] == mock_gdrive_client
    assert result[1] == "gdrive_source"
    assert result[2] == "gdrive_dest"
    assert result[3] == "gdrive_failed"
    mock_init_gdrive.assert_called_once_with(settings)
