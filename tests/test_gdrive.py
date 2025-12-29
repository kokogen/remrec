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
def test_gdrive_client_init_success(MockCredentials, MockBuild, mock_credentials, mock_token):
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
    MockBuild.assert_called_once_with('drive', 'v3', credentials=ANY)
    assert client.service == mock_service


@patch("src.gdrive.build")
@patch("src.gdrive.Credentials")
def test_gdrive_client_init_failure(MockCredentials, MockBuild, mock_credentials, mock_token):
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
    with patch("src.gdrive.build") as MockBuild, patch("src.gdrive.Credentials") as MockCredentials:
        MockCredentials.from_authorized_user_info.return_value = MagicMock(valid=True)
        mock_service = MagicMock() # Create a fresh mock service for each test
        MockBuild.return_value = mock_service

        # Mock the create method chain for ensure_folder_path_exists tests
        mock_service.files.return_value.list.return_value.execute.return_value = {"files": []} # Default list for ensure_folder_path_exists
        mock_service.files.return_value.create.return_value.execute.return_value = {"id": "new_folder_id"} # Default create for ensure_folder_path_exists
        
        client_instance = GoogleDriveClient(
            credentials_json=json.dumps(mock_credentials),
            token_json=json.dumps(mock_token),
        )
        # Ensure mocks are reset after client creation
        mock_service.reset_mock()
        yield client_instance

def test_ensure_folder_path_exists_simple(client):
    """Test creating a simple, one-level folder that doesn't exist."""
    # Setup
    client.service.files().list().execute.return_value = {"files": []}
    client.service.files().create().execute.return_value = {"id": "new_folder_id"}

    # Action
    folder_id = client.ensure_folder_path_exists("New Folder")

    # Asserts
    assert folder_id == "new_folder_id"
    client.service.files().create().execute.assert_called_once()

def test_ensure_folder_path_exists_nested(client):
    """Test creating a nested folder path."""
    # Setup to simulate that no folders exist
    client.service.files().list().execute.side_effect = [
        {"files": []},  # No "Parent" folder
        {"files": []},  # No "Child" folder
    ]
    # Simulate creation calls
    client.service.files().create().execute.side_effect = [
        {"id": "parent_id"},
        {"id": "child_id"},
    ]

    # Action
    folder_id = client.ensure_folder_path_exists("Parent/Child")

    # Asserts
    assert folder_id == "child_id"
    assert client.service.files().create().execute.call_count == 2
    
def test_verify_folder_id_exists_success(client):
    """Test that folder verification succeeds if the folder exists."""
    client.service.files().get().execute.return_value = {
        "id": "test_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder"
    }

    folder_id = client.verify_folder_exists("test_id")
    assert folder_id == "test_id"

def test_verify_folder_id_exists_permanent_error(client):
    """Test that a PermanentError is raised if the folder ID does not exist."""
    from googleapiclient.errors import HttpError
    
    # Simulate a 404 Not Found error from the Google Drive API
    client.service.files().get.side_effect = HttpError(
        resp=MagicMock(status=404),
        content=b'{"error": {"message": "File not found"}}'
    )
    
    with pytest.raises(PermanentError, match="not found"):
        client.verify_folder_exists("non_existent_id")

def test_list_files_success(client):
    """Test listing files successfully."""
    client.service.files().get().execute.return_value = {
        "id": "folder_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder"
    }
    client.service.files().list().execute.return_value = {
        "files": [{"id": "file_id", "name": "test.pdf"}]
    }
    
    files = client.list_files("folder_id")
    
    assert len(files) == 1
    assert files[0]["name"] == "test.pdf"
    
@patch("src.gdrive.io.FileIO")
def test_download_file_success(MockFileIO, client):
    """Test downloading a file successfully."""
    client.ensure_folder_path_exists = MagicMock(return_value="folder_id")
    client._find_file_id_by_name = MagicMock(return_value="file_id")
    
    mock_downloader = MagicMock()
    mock_downloader.next_chunk.side_effect = [(None, True)]
    # Mock http.request directly to avoid "not enough values to unpack" ValueError
    mock_downloader.http.request.return_value = (MagicMock(status=200), b"file_content")
    client.service.files().get_media.return_value = mock_downloader
    
    client.download_file("/remote/path/test.pdf", "/local/path/test.pdf")
    
    client.service.files().get_media.assert_called_once_with(fileId="file_id")

@patch("src.gdrive.MediaFileUpload")
def test_upload_file_success(MockMediaFileUpload, client):
    """Test uploading a file successfully."""
    client.ensure_folder_path_exists = MagicMock(return_value="folder_id")
    client._find_file_id_by_name = MagicMock(return_value=None)
    
    client.upload_file("/local/path/test.pdf", "/remote/path/test.pdf")
    
    MockMediaFileUpload.assert_called_once_with(
        "/local/path/test.pdf", resumable=True
    )
    client.service.files().create.assert_called_once()
    
def test_delete_file_success(client):
    """Test deleting a file successfully."""
    client.ensure_folder_path_exists = MagicMock(return_value="folder_id")
    client._find_file_id_by_name = MagicMock(return_value="file_id")
    
    client.delete_file("/remote/path/test.pdf")
    
    client.service.files().delete.assert_called_once_with(fileId="file_id")

def test_move_file_success(client):
    """Test moving a file successfully."""
    client.ensure_folder_path_exists = MagicMock(side_effect=["from_folder_id", "to_folder_id"])
    client._find_file_id_by_name = MagicMock(return_value="file_id")
    client.service.files().get().execute.return_value = {"parents": ["old_parent"]}
    
    client.move_file("/from/path/test.pdf", "/to/path/test.pdf")
    
    client.service.files().update.assert_called_once()
