# tests/test_processing.py
import pytest
from unittest.mock import patch, MagicMock
from processing import process_single_file
from exceptions import PermanentError

@pytest.fixture
def mock_settings():
    """Fixture for mock settings."""
    settings = MagicMock()
    settings.LOCAL_BUF_DIR = MagicMock()
    settings.LOCAL_BUF_DIR.__truediv__.return_value = "mock/path"
    return settings

@pytest.fixture
def mock_storage_client():
    """Fixture for a mock storage client."""
    return MagicMock()

@patch("processing.get_settings")
@patch("processing.pdf_to_images")
@patch("processing.recognize_handwriting")
@patch("processing.create_text_pdf_from_images")
def test_process_single_file_success(
    mock_create_pdf, mock_recognize, mock_pdf_to_images, mock_get_settings,
    mock_settings, mock_storage_client
):
    """Test the successful processing of a single file."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_pdf_to_images.return_value = ["img1.png"]
    mock_recognize.return_value = ["text1"]
    
    file_entry = MagicMock()
    file_entry.name = "test.pdf"
    
    # Action
    process_single_file(mock_storage_client, file_entry)
    
    # Asserts
    mock_storage_client.download_file.assert_called_once()
    mock_pdf_to_images.assert_called_once()
    mock_recognize.assert_called_once()
    mock_create_pdf.assert_called_once()
    mock_storage_client.upload_file.assert_called_once()
    mock_storage_client.delete_file.assert_called_once()

@patch("processing.get_settings")
@patch("processing.pdf_to_images", side_effect=Exception("PDF processing failed"))
def test_process_single_file_permanent_error(
    mock_pdf_to_images, mock_get_settings, mock_settings, mock_storage_client
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