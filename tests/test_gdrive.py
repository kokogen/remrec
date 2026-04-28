# tests/test_gdrive.py
import pytest
from unittest.mock import patch, MagicMock, ANY
import json

from src.gdrive import (
    GoogleDriveClient,
    _escape_drive_query_value,
    _extract_google_client_config,
)
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


@pytest.mark.parametrize(
    ("credentials_data", "expected_client_id", "expected_client_secret"),
    [
        (
            {
                "installed": {
                    "client_id": "installed_client_id",
                    "client_secret": "installed_client_secret",
                }
            },
            "installed_client_id",
            "installed_client_secret",
        ),
        (
            {
                "web": {
                    "client_id": "web_client_id",
                    "client_secret": "web_client_secret",
                }
            },
            "web_client_id",
            "web_client_secret",
        ),
        (
            {
                "client_id": "top_level_client_id",
                "client_secret": "top_level_client_secret",
            },
            "top_level_client_id",
            "top_level_client_secret",
        ),
    ],
)
def test_extract_google_client_config_supported_shapes(
    credentials_data, expected_client_id, expected_client_secret
):
    """Test extracting OAuth client config from supported credentials shapes."""
    client_config = _extract_google_client_config(credentials_data)

    assert client_config["client_id"] == expected_client_id
    assert client_config["client_secret"] == expected_client_secret


def test_extract_google_client_config_missing_config():
    """Test missing OAuth client config returns None."""
    assert (
        _extract_google_client_config({"installed": {"client_id": "missing_secret"}})
        is None
    )


def test_escape_drive_query_value_escapes_quotes_and_backslashes():
    """Google Drive query literals require backslash escaping."""
    assert _escape_drive_query_value(r"Bob's \ notes") == r"Bob\'s \\ notes"


@patch("src.gdrive.build")
@patch("src.gdrive.Credentials")
def test_gdrive_client_init_success(
    MockCredentials, MockBuild, mock_credentials, mock_token
):
    """Test successful initialization of GoogleDriveClient."""
    # Setup
    mock_creds = MagicMock(valid=True)
    MockCredentials.from_authorized_user_info.return_value = mock_creds
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
    assert mock_creds.client_id == "test_client_id"
    assert mock_creds.client_secret == "test_client_secret"


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
        "files": [
            {
                "id": "file_id",
                "name": "test.pdf",
                "mimeType": "application/pdf",
            }
        ]
    }

    files = client.list_files("folder_id")

    assert len(files) == 1
    assert files[0].name == "test.pdf"


def test_list_files_with_pagination_and_folder_filtering(client):
    """Test listing paginated Google Drive files while excluding folders."""
    client.service.files().get().execute.return_value = {
        "id": "folder_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder",
    }
    client.service.files().list().execute.side_effect = [
        {
            "files": [
                {
                    "id": "file_id_1",
                    "name": "first.pdf",
                    "mimeType": "application/pdf",
                },
                {
                    "id": "folder_child_id",
                    "name": "folder.pdf",
                    "mimeType": "application/vnd.google-apps.folder",
                },
            ],
            "nextPageToken": "next-page",
        },
        {
            "files": [
                {
                    "id": "file_id_2",
                    "name": "second.pdf",
                    "mimeType": "application/pdf",
                }
            ]
        },
    ]
    client.service.files().list.reset_mock()

    files = client.list_files("folder_id")

    assert [item.name for item in files] == ["first.pdf", "second.pdf"]
    assert client.service.files().list.call_count == 2
    client.service.files().list.assert_any_call(
        q="'folder_id' in parents and trashed=false",
        fields="nextPageToken, files(id, name, mimeType)",
        pageToken=None,
    )
    client.service.files().list.assert_any_call(
        q="'folder_id' in parents and trashed=false",
        fields="nextPageToken, files(id, name, mimeType)",
        pageToken="next-page",
    )


def test_list_files_escapes_folder_id_in_query(client):
    """Folder IDs with query metacharacters should not break Drive search syntax."""
    client.service.files().get().execute.return_value = {
        "id": "folder_id",
        "name": "Test Folder",
        "mimeType": "application/vnd.google-apps.folder",
    }
    client.service.files().list().execute.return_value = {"files": []}
    client.service.files().list.reset_mock()

    client.list_files(r"folder'id\part")

    client.service.files().list.assert_called_once_with(
        q=r"'folder\'id\\part' in parents and trashed=false",
        fields="nextPageToken, files(id, name, mimeType)",
        pageToken=None,
    )


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


def test_file_exists_success(client):
    """Test checking for an existing file by name."""
    client._find_file_id_by_name = MagicMock(return_value="existing_file_id")

    exists = client.file_exists("folder_id", "recognized_test.pdf")

    assert exists is True
    client._find_file_id_by_name.assert_called_once_with(
        "recognized_test.pdf", "folder_id"
    )


def test_file_exists_missing(client):
    """Test checking for a missing file by name."""
    client._find_file_id_by_name = MagicMock(return_value=None)

    exists = client.file_exists("folder_id", "recognized_test.pdf")

    assert exists is False


def test_find_file_id_by_name_escapes_filename_and_folder_id(client):
    """File lookup should escape names before interpolating Drive query strings."""
    client.service.files().list().execute.return_value = {
        "files": [{"id": "existing_file_id", "name": "recognized"}]
    }
    client.service.files().list.reset_mock()

    file_id = client._find_file_id_by_name(r"Bob's \ note.pdf", r"folder'id\part")

    assert file_id == "existing_file_id"
    client.service.files().list.assert_called_once_with(
        q=r"name='Bob\'s \\ note.pdf' and 'folder\'id\\part' in parents and trashed=false",
        fields="files(id, name)",
    )


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
