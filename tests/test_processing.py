# tests/test_processing.py
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from src.processing import process_single_file
from src.exceptions import PermanentError, TransientError

# Fixtures for mock_settings and mock_storage_client can be used from conftest.py


@patch("pathlib.Path.is_file", return_value=True)
@patch("pathlib.Path.unlink")
@patch("src.processing.get_settings")
@patch("src.processing.convert_from_path")
@patch("src.processing.RecognitionClient")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_success(
    mock_create_pdf,
    mock_recognition_client,
    mock_convert_from_path,
    mock_get_settings,
    mock_path_unlink,
    mock_path_is_file,
    mock_settings,
    mock_storage_client,
):
    """Test the successful processing of a single file."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_convert_from_path.return_value = [MagicMock()]
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    # Mock LOCAL_BUF_DIR to be a real Path object for the test
    mock_settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    mock_settings.DST_FOLDER = "/processed"
    mock_settings.PROCESSED_FOLDER = "/processed_files"

    mock_recognize = mock_recognition_client.return_value.recognize

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
    mock_storage_client.move_file.assert_called_once_with(
        "file_id_123", "/processed_files"
    )
    mock_storage_client.delete_file.assert_not_called()
    assert mock_path_unlink.call_count == 2  # local_pdf_path and result_pdf_path


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


@patch("pathlib.Path.is_file", return_value=True)
@patch("pathlib.Path.unlink")
@patch("src.processing.get_settings")
@patch("src.processing.convert_from_path")
@patch("src.processing.RecognitionClient")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_move_fails(
    mock_create_pdf,
    mock_recognition_client,
    mock_convert_from_path,
    mock_get_settings,
    mock_path_unlink,
    mock_path_is_file,
    mock_settings,
    mock_storage_client,
):
    """Test that a TransientError is raised if moving the original file fails."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_convert_from_path.return_value = [MagicMock()]
    mock_storage_client.move_file.side_effect = Exception("Move failed")
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    mock_settings.LOCAL_BUF_DIR = Path("/tmp/buf")
    mock_settings.DST_FOLDER = "/processed"
    mock_settings.PROCESSED_FOLDER = "/processed_files"

    # Action & Asserts
    with pytest.raises(TransientError, match="Failed to move original file"):
        process_single_file(mock_storage_client, file_entry)

    # Verify that we tried to do everything up to the move
    mock_storage_client.download_file.assert_called_once()
    mock_convert_from_path.assert_called_once()
    mock_recognition_client.return_value.recognize.assert_called_once()
    mock_create_pdf.assert_called_once()
    mock_storage_client.upload_file.assert_called_once()
    mock_storage_client.move_file.assert_called_once_with(
        "file_id_123", "/processed_files"
    )
    # Ensure original is not deleted
    mock_storage_client.delete_file.assert_not_called()
