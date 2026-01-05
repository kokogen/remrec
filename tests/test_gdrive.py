# tests/test_gdrive.py
import pytest
from unittest.mock import patch, MagicMock, ANY
import json

from src.gdrive import GoogleDriveClient
from src.exceptions import PermanentError


@pytest.fixture
def mock_credentials():
    """Fixture for mock Google credentials."""
    return {
        "installed": {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "scopes": ["https://www.googleapis.com/auth/drive"],
        }
    }


@pytest.fixture
def mock_token():
    """Fixture for a mock token."""
    return {
        "token": "test_token",
        "refresh_token": "test_refresh_token",
        "token_uri": "https://oauth2.googleapis.com/token",
        "client_id": "test_client_id",
        "client_secret": "test_client_secret",
        "scopes": ["https://www.googleapis.com/auth/drive"],
    }


@patch("src.gdrive.build")
@patch("src.gdrive.Credentials")
def test_gdrive_client_init_success(
    MockCredentials, MockBuild, mock_credentials, mock_token
):
    """Test successful initialization of GoogleDriveClient."""
    # Setup
    MockCredentials.from_authorized_user_info.return_value = MagicMock(valid=True)
    mock_service = MockBuild.return_value

    # Action
    client = GoogleDriveClient(
        credentials_json=json.dumps(mock_credentials),
        token_json=json.dumps(mock_token),
    )

    # Asserts
    MockCredentials.from_authorized_user_info.assert_called_once()
    MockBuild.assert_called_once_with("drive", "v3", credentials=ANY)
    assert client.service == mock_service


@patch("src.gdrive.build")
@patch("src.gdrive.Credentials")
def test_gdrive_client_init_failure(
    MockCredentials, MockBuild, mock_credentials, mock_token
):
    """Test failed initialization of GoogleDriveClient."""
    # Setup
    MockCredentials.from_authorized_user_info.side_effect = Exception("Auth failed")

    # Action and Asserts
    with pytest.raises(Exception, match="Auth failed"):
        GoogleDriveClient(
            credentials_json=json.dumps(mock_credentials),
            token_json=json.dumps(mock_token),
        )


@pytest.fixture
def client(mock_credentials, mock_token):
    """Fixture to create a GoogleDriveClient instance with mocked dependencies."""
    with (
        patch("src.gdrive.build") as MockBuild,
        patch("src.gdrive.Credentials") as MockCredentials,
    ):
        MockCredentials.from_authorized_user_info.return_value = MagicMock(valid=True)
        mock_service = MagicMock()
        MockBuild.return_value = mock_service

        client_instance = GoogleDriveClient(
            credentials_json=json.dumps(mock_credentials),
            token_json=json.dumps(mock_token),
        )
        mock_service.reset_mock()
        yield client_instance


def test_verify_folder_exists_success(client):
    """Test that folder verification succeeds if the folder exists."""
    client.service.files().get().execute.return_value = {
        "id": "test_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder",
    }

    # This method now returns None on success and raises an error on failure.
    # The test passes if no exception is raised.
    client.verify_folder_exists("test_id")


def test_verify_folder_exists_permanent_error(client):
    """Test that a PermanentError is raised if the folder ID does not exist."""
    from googleapiclient.errors import HttpError

    # Simulate a 404 Not Found error from the Google Drive API
    client.service.files().get.side_effect = HttpError(
        resp=MagicMock(status=404), content=b'{"error": {"message": "File not found"}}'
    )

    with pytest.raises(PermanentError, match="not found"):
        client.verify_folder_exists("non_existent_id")


def test_list_files_success(client):
    """Test listing files successfully."""
    client.service.files().get().execute.return_value = {
        "id": "folder_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder",
    }
    client.service.files().list().execute.return_value = {
        "files": [{"id": "file_id", "name": "test.pdf"}]
    }

    files = client.list_files("folder_id")

    assert len(files) == 1
    assert files[0].name == "test.pdf"


@patch("src.gdrive.MediaIoBaseDownload")
@patch("src.gdrive.io.FileIO")
def test_download_file_success(MockFileIO, MockMediaIoBaseDownload, client):
    """Test downloading a file successfully using its file ID."""
    mock_downloader_instance = MockMediaIoBaseDownload.return_value
    mock_downloader_instance.next_chunk.return_value = (None, True)

    file_id_to_download = "some_file_id"
    local_path = "/local/path/test.pdf"

    client.download_file(file_id_to_download, local_path)

    client.service.files().get_media.assert_called_once_with(fileId=file_id_to_download)
    MockFileIO.assert_called_once_with(local_path, "wb")
    MockMediaIoBaseDownload.assert_called_once()


@patch("src.gdrive.MediaFileUpload")
def test_upload_file_success(MockMediaFileUpload, client):
    """Test uploading a file successfully."""
    client._find_file_id_by_name = MagicMock(return_value=None)  # No existing file

    client.upload_file("/local/path/test.pdf", "folder_id", "test.pdf")

    MockMediaFileUpload.assert_called_once_with("/local/path/test.pdf", resumable=True)
    client.service.files().create.assert_called_once_with(
        body={"name": "test.pdf", "parents": ["folder_id"]},
        media_body=MockMediaFileUpload.return_value,
        fields="id",
    )
    client.service.files().create().execute.assert_called_once()


def test_delete_file_success(client):
    """Test deleting a file successfully by its file ID."""
    file_id_to_delete = "some_file_id"

    client.delete_file(file_id_to_delete)

    client.service.files().delete.assert_called_once_with(fileId=file_id_to_delete)
    client.service.files().delete().execute.assert_called_once()


def test_move_file_success(client):
    """Test moving a file successfully."""
    client.service.files().get().execute.return_value = {
        "parents": ["old_parent_id"],
        "name": "test.pdf",
    }

    client.move_file("file_id_to_move", "to_folder_id")

    client.service.files().update.assert_called_once_with(
        fileId="file_id_to_move",
        addParents="to_folder_id",
        removeParents="old_parent_id",
        body={"name": "test.pdf"},
        fields="id, parents",
    )
    client.service.files().update().execute.assert_called_once()
