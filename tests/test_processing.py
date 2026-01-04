# tests/test_processing.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.processing import process_single_file
from src.exceptions import PermanentError

# Fixtures for mock_settings and mock_storage_client can be used from conftest.py


@patch("src.processing.os.path.exists", return_value=True)
@patch("src.processing.os.remove")
@patch("src.processing.get_settings")
@patch("src.processing.convert_from_path")
@patch("src.processing.recognize")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_success(
    mock_create_pdf,
    mock_recognize,
    mock_convert_from_path,
    mock_get_settings,
    mock_os_remove,
    mock_path_exists,
    mock_settings,
    mock_storage_client,
):
    """Test the successful processing of a single file."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_convert_from_path.return_value = [MagicMock()]
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"  # For Google Drive deletion
    file_entry.path_display = "file_id_123"  # For Dropbox deletion

    # Mock LOCAL_BUF_DIR to be a real Path object for the test
    mock_settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    mock_settings.DST_FOLDER = "/processed"

    # Action
    process_single_file(mock_storage_client, file_entry)

    # Asserts
    mock_storage_client.download_file.assert_called_once()
    mock_convert_from_path.assert_called_once()
    mock_recognize.assert_called_once()
    mock_create_pdf.assert_called_once()
    mock_storage_client.upload_file.assert_called_once_with(
        local_path=Path("/tmp/buf/recognized_test.pdf"),
        folder_id="/processed",
        filename="recognized_test.pdf",
    )
    mock_storage_client.delete_file.assert_called_once_with("file_id_123")
    assert mock_os_remove.call_count == 2  # local_pdf_path and result_pdf_path


@patch("src.processing.get_settings")
@patch(
    "src.processing.convert_from_path", side_effect=Exception("PDF processing failed")
)
def test_process_single_file_permanent_error(
    mock_convert_from_path, mock_get_settings, mock_settings, mock_storage_client
):
    """Test that a permanent error is raised when PDF processing fails."""
    # Setup
    mock_get_settings.return_value = mock_settings
    file_entry = MagicMock()
    file_entry.name = "test.pdf"

    # Action and Asserts
    with pytest.raises(PermanentError):
        process_single_file(mock_storage_client, file_entry)

    mock_storage_client.download_file.assert_called_once()
    mock_storage_client.upload_file.assert_not_called()
    mock_storage_client.delete_file.assert_not_called()
