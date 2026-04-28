# tests/test_main.py
from unittest.mock import patch, MagicMock
import pytest

from src.main import WorkflowStatus, initialize_storage_client, main, main_workflow
from src.config import Settings
from src.dbox import DropboxClient
from src.exceptions import StorageAuthError, StoragePermanentError, TransientError
from src.storage.dto import FileMetadata
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
    settings.SRC_FOLDER = "/source"
    settings.DST_FOLDER = "/dest"
    settings.FAILED_FOLDER = "/failed"
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
    settings.SRC_FOLDER = "/source"
    settings.DST_FOLDER = "/dest"
    settings.FAILED_FOLDER = "/failed"
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
        "Dropbox authentication failed. Please check your token and app credentials. Error: Dropbox authentication failed during initialize client"
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
    settings.SRC_FOLDER = "/source"
    settings.DST_FOLDER = "/dest"
    settings.FAILED_FOLDER = "/failed"
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
        "Failed to initialize Dropbox client due to a storage error: Unexpected Dropbox error during initialize client: network error",
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
    settings.SRC_FOLDER = "gdrive_source"
    settings.DST_FOLDER = "gdrive_dest"
    settings.FAILED_FOLDER = "gdrive_failed"
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


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
def test_main_workflow_returns_configuration_error_when_client_missing(
    mock_initialize_storage_client, mock_get_settings, mock_settings
):
    """Ensures workflow status records storage initialization failures."""
    mock_get_settings.return_value = mock_settings
    mock_initialize_storage_client.return_value = (None, "/source", "/dest", "/failed")

    status = main_workflow()

    assert status == WorkflowStatus.CONFIGURATION_ERROR


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
def test_main_workflow_returns_success_when_no_files(
    mock_initialize_storage_client, mock_get_settings, mock_settings
):
    """Ensures an empty source folder is a successful workflow run."""
    mock_get_settings.return_value = mock_settings
    storage_client = MagicMock()
    storage_client.list_files.return_value = []
    mock_initialize_storage_client.return_value = (
        storage_client,
        "/source",
        "/dest",
        "/failed",
    )

    status = main_workflow()

    assert status == WorkflowStatus.SUCCESS


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
@patch("src.main.process_single_file", side_effect=TransientError("network"))
def test_main_workflow_returns_transient_error_for_retryable_file_failure(
    mock_process_single_file,
    mock_initialize_storage_client,
    mock_get_settings,
    mock_settings,
):
    """Ensures retryable file failures are visible to run-once callers."""
    mock_get_settings.return_value = mock_settings
    storage_client = MagicMock()
    storage_client.list_files.return_value = [
        FileMetadata(id="file_id", name="test.pdf", path="/source/test.pdf")
    ]
    mock_initialize_storage_client.return_value = (
        storage_client,
        "/source",
        "/dest",
        "/failed",
    )

    status = main_workflow()

    assert status == WorkflowStatus.TRANSIENT_ERROR


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
def test_main_workflow_returns_transient_error_when_listing_source_fails_temporarily(
    mock_initialize_storage_client, mock_get_settings, mock_settings
):
    """Ensures source listing transient failures are visible to run-once callers."""
    mock_get_settings.return_value = mock_settings
    storage_client = MagicMock()
    storage_client.list_files.side_effect = TransientError("temporary API failure")
    mock_initialize_storage_client.return_value = (
        storage_client,
        "/source",
        "/dest",
        "/failed",
    )

    status = main_workflow()

    assert status == WorkflowStatus.TRANSIENT_ERROR


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
def test_main_workflow_returns_configuration_error_when_listing_source_is_unauthorized(
    mock_initialize_storage_client, mock_get_settings, mock_settings
):
    """Ensures storage auth failures while listing source are configuration errors."""
    mock_get_settings.return_value = mock_settings
    storage_client = MagicMock()
    storage_client.list_files.side_effect = StorageAuthError("bad token")
    mock_initialize_storage_client.return_value = (
        storage_client,
        "/source",
        "/dest",
        "/failed",
    )

    status = main_workflow()

    assert status == WorkflowStatus.CONFIGURATION_ERROR


@patch("src.main.get_settings")
@patch("src.main.initialize_storage_client")
def test_main_workflow_returns_permanent_error_for_other_storage_listing_failures(
    mock_initialize_storage_client, mock_get_settings, mock_settings
):
    """Ensures non-retryable source listing storage failures do not crash run-once."""
    mock_get_settings.return_value = mock_settings
    storage_client = MagicMock()
    storage_client.list_files.side_effect = StoragePermanentError("bad request")
    mock_initialize_storage_client.return_value = (
        storage_client,
        "/source",
        "/dest",
        "/failed",
    )

    status = main_workflow()

    assert status == WorkflowStatus.PERMANENT_ERROR


@patch("src.main.setup_logging")
@patch("src.main.main_workflow", return_value=WorkflowStatus.SUCCESS)
@patch("sys.argv", ["remrec", "--run-once"])
def test_main_run_once_exits_zero_on_success(mock_main_workflow, mock_setup_logging):
    """Ensures run-once mode exposes successful workflows via process exit code."""
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 0


@patch("src.main.setup_logging")
@patch("src.main.main_workflow", return_value=WorkflowStatus.TRANSIENT_ERROR)
@patch("sys.argv", ["remrec", "--run-once"])
def test_main_run_once_exits_nonzero_on_failure(mock_main_workflow, mock_setup_logging):
    """Ensures run-once mode exposes failed workflows via process exit code."""
    with pytest.raises(SystemExit) as exc_info:
        main()

    assert exc_info.value.code == 1
