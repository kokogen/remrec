# tests/test_main.py
from unittest.mock import patch, MagicMock
from src.main import initialize_storage_client
from src.config import Settings
from src.dbox import DropboxClient


@patch("src.main._init_dropbox_client")
def test_initialize_storage_client_dropbox_returns_tuple(mock_init_dropbox):
    """
    Ensures initialize_storage_client returns a tuple of 4 elements
    for the Dropbox provider, which would have caught the previous TypeError.
    """
    # Arrange
    settings = MagicMock(spec=Settings)
    settings.STORAGE_PROVIDER = "dropbox"
    settings.DROPBOX_SOURCE_DIR = "/source"
    settings.DROPBOX_DEST_DIR = "/dest"
    settings.DROPBOX_FAILED_DIR = "/failed"
    settings.DROPBOX_REFRESH_TOKEN_ENV = "some_token"  # Needs to be set for the check
    mock_dropbox_client = MagicMock(spec=DropboxClient)
    mock_init_dropbox.return_value = mock_dropbox_client

    # Action
    result = initialize_storage_client(settings)

    # Assert
    assert isinstance(result, tuple), "Should return a tuple"
    assert len(result) == 4, "Tuple should have 4 elements (client, src, dst, failed)"
    assert result[0] == mock_dropbox_client
    assert result[1] == "/source"
    assert result[2] == "/dest"
    assert result[3] == "/failed"
    mock_init_dropbox.assert_called_once_with(settings)


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
