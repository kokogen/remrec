# tests/test_processing.py
import pytest
from unittest.mock import patch, MagicMock
from filelock import Timeout
from src.processing import process_single_file
from src.exceptions import PermanentError

# Fixtures for mock_settings and mock_storage_client can be used from conftest.py


@patch("src.processing.get_settings")
@patch("src.processing.pdfinfo_from_path")
@patch("src.processing.convert_from_path")
@patch("src.processing.recognize")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_success(
    mock_create_pdf,
    mock_recognize,
    mock_convert_from_path,
    mock_pdfinfo_from_path,
    mock_get_settings,
    mock_settings,
    mock_storage_client,
    tmp_path,
):
    """Test the successful processing of a single file."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_pdfinfo_from_path.return_value = {"Pages": 1}
    mock_convert_from_path.return_value = [MagicMock()]
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"  # For Google Drive deletion
    file_entry.path_display = "file_id_123"  # For Dropbox deletion

    # Mock LOCAL_BUF_DIR to be a real Path object for the test
    mock_settings.LOCAL_BUF_DIR = tmp_path
    mock_settings.DST_FOLDER = "/processed"

    process_single_file(mock_storage_client, file_entry, mock_settings.DST_FOLDER)

    # Asserts
    mock_storage_client.file_exists.assert_called_once_with(
        "/processed", "recognized_test.pdf"
    )
    mock_storage_client.download_file.assert_called_once()
    mock_pdfinfo_from_path.assert_called_once()
    mock_convert_from_path.assert_called_once_with(
        mock_storage_client.download_file.call_args.args[1].as_posix(),
        dpi=mock_settings.PDF_DPI,
        first_page=1,
        last_page=1,
    )
    mock_recognize.assert_called_once()
    mock_create_pdf.assert_called_once()
    upload_call = mock_storage_client.upload_file.call_args.kwargs
    assert upload_call["local_path"].name == "recognized_test.pdf"
    assert upload_call["local_path"].parent.parent == tmp_path
    assert upload_call["folder_id"] == "/processed"
    assert upload_call["filename"] == "recognized_test.pdf"
    mock_storage_client.delete_file.assert_called_once_with("file_id_123")


@patch("src.processing.get_settings")
@patch("src.processing.pdfinfo_from_path")
@patch(
    "src.processing.convert_from_path", side_effect=Exception("PDF processing failed")
)
def test_process_single_file_permanent_error(
    mock_convert_from_path,
    mock_pdfinfo_from_path,
    mock_get_settings,
    mock_settings,
    mock_storage_client,
    tmp_path,
):
    """Test that a permanent error is raised when PDF processing fails."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_pdfinfo_from_path.return_value = {"Pages": 1}
    mock_settings.LOCAL_BUF_DIR = tmp_path
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    # Action and Asserts
    with pytest.raises(PermanentError):
        process_single_file(mock_storage_client, file_entry, "dummy_dest_path")

    mock_storage_client.download_file.assert_called_once()
    mock_pdfinfo_from_path.assert_called_once()
    mock_convert_from_path.assert_called_once()
    mock_storage_client.upload_file.assert_not_called()
    mock_storage_client.delete_file.assert_not_called()


@patch("src.processing.get_settings")
@patch("src.processing.pdfinfo_from_path")
@patch("src.processing.convert_from_path")
def test_process_single_file_zero_page_pdf_is_permanent_error(
    mock_convert_from_path,
    mock_pdfinfo_from_path,
    mock_get_settings,
    mock_settings,
    mock_storage_client,
    tmp_path,
):
    """PDF metadata with zero pages should fail before page conversion."""
    mock_get_settings.return_value = mock_settings
    mock_settings.LOCAL_BUF_DIR = tmp_path
    mock_pdfinfo_from_path.return_value = {"Pages": 0}
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    with pytest.raises(PermanentError, match="PDF has no pages"):
        process_single_file(mock_storage_client, file_entry, "dummy_dest_path")

    mock_storage_client.download_file.assert_called_once()
    mock_pdfinfo_from_path.assert_called_once()
    mock_convert_from_path.assert_not_called()
    mock_storage_client.upload_file.assert_not_called()
    mock_storage_client.delete_file.assert_not_called()


@patch("src.processing.get_settings")
@patch("src.processing.pdfinfo_from_path")
@patch("src.processing.convert_from_path")
@patch("src.processing.recognize")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_converts_and_closes_pages_one_at_a_time(
    mock_create_pdf,
    mock_recognize,
    mock_convert_from_path,
    mock_pdfinfo_from_path,
    mock_get_settings,
    mock_settings,
    mock_storage_client,
    tmp_path,
):
    """Ensures large PDFs are processed page-by-page instead of all at once."""
    mock_get_settings.return_value = mock_settings
    mock_settings.LOCAL_BUF_DIR = tmp_path
    mock_pdfinfo_from_path.return_value = {"Pages": 2}
    first_page = MagicMock()
    second_page = MagicMock()
    mock_convert_from_path.side_effect = [[first_page], [second_page]]
    mock_recognize.side_effect = ["page one", "page two"]
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    process_single_file(mock_storage_client, file_entry, "/processed")

    assert mock_convert_from_path.call_count == 2
    assert mock_convert_from_path.call_args_list[0].kwargs["first_page"] == 1
    assert mock_convert_from_path.call_args_list[0].kwargs["last_page"] == 1
    assert mock_convert_from_path.call_args_list[1].kwargs["first_page"] == 2
    assert mock_convert_from_path.call_args_list[1].kwargs["last_page"] == 2
    first_page.close.assert_called_once_with()
    second_page.close.assert_called_once_with()
    mock_create_pdf.assert_called_once()
    assert mock_create_pdf.call_args.args[0] == ["page one", "page two"]


@patch("src.processing.get_settings")
@patch("src.processing.convert_from_path")
@patch("src.processing.pdfinfo_from_path")
@patch("src.processing.recognize")
@patch("src.processing.create_reflowed_pdf")
def test_process_single_file_skips_ocr_when_result_exists(
    mock_create_pdf,
    mock_recognize,
    mock_convert_from_path,
    mock_pdfinfo_from_path,
    mock_get_settings,
    mock_settings,
    mock_storage_client,
    tmp_path,
):
    """Test that existing output prevents duplicate OCR work."""
    mock_get_settings.return_value = mock_settings
    mock_settings.LOCAL_BUF_DIR = tmp_path
    mock_storage_client.file_exists.return_value = True
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    process_single_file(mock_storage_client, file_entry, "/processed")

    mock_storage_client.file_exists.assert_called_once_with(
        "/processed", "recognized_test.pdf"
    )
    mock_storage_client.download_file.assert_not_called()
    mock_pdfinfo_from_path.assert_not_called()
    mock_convert_from_path.assert_not_called()
    mock_recognize.assert_not_called()
    mock_create_pdf.assert_not_called()
    mock_storage_client.upload_file.assert_not_called()
    mock_storage_client.delete_file.assert_called_once_with("file_id_123")


@patch("src.processing.FileLock")
@patch("src.processing.get_settings")
def test_process_single_file_skips_when_file_is_locked(
    mock_get_settings, mock_file_lock, mock_settings, mock_storage_client, tmp_path
):
    """Test that a file already locked by another worker is skipped."""
    mock_get_settings.return_value = mock_settings
    mock_settings.LOCAL_BUF_DIR = tmp_path
    mock_file_lock.return_value.__enter__.side_effect = Timeout("locked")
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    file_entry.id = "file_id_123"

    process_single_file(mock_storage_client, file_entry, "dummy_dest_path")

    mock_storage_client.download_file.assert_not_called()
    mock_storage_client.upload_file.assert_not_called()
    mock_storage_client.delete_file.assert_not_called()
