import pytest
from unittest.mock import patch, MagicMock
import dropbox

# Импортируем нужные классы для моков
from dbox import DropboxClient
from exceptions import PermanentError, TransientError
from processing import process_single_file

# Создаем базовые моки для зависимостей, которые используются во всех тестах
@pytest.fixture
def mock_dbx_client():
    """Фикстура для мока нашего кастомного клиента Dropbox."""
    # Используем spec=DropboxClient, чтобы мок имел те же методы
    return MagicMock(spec=DropboxClient)

@pytest.fixture
def mock_file_entry():
    """Фикстура для мока метаданных файла из Dropbox."""
    file_entry = MagicMock(spec=dropbox.files.FileMetadata)
    file_entry.name = "test.pdf"
    file_entry.path_display = "/test.pdf"
    return file_entry

# Патчим все внешние зависимости модуля processing
@patch('processing.os.remove')
@patch('processing.os.path.exists', return_value=True)
@patch('processing.create_reflowed_pdf')
@patch('processing.recognize')
@patch('processing.image_to_base64', return_value="fake_base64")
@patch('processing.convert_from_path')
def test_process_single_file_happy_path(
    mock_convert, mock_b64, mock_recognize, mock_txt_to_pdf,
    mock_os_exists, mock_os_remove, mock_dbx_client, mock_file_entry
):
    """Тест "счастливого пути", когда все операции успешны."""
    # 1. Настройка моков
    mock_convert.return_value = [MagicMock()] # Возвращаем одну "страницу"
    mock_recognize.return_value = "Recognized Text"

    # 2. Вызов функции
    process_single_file(mock_dbx_client, mock_file_entry)

    # 3. Проверки
    mock_dbx_client.download_file.assert_called_once()
    mock_convert.assert_called_once()
    mock_recognize.assert_called_once()
    mock_txt_to_pdf.assert_called_once()
    mock_dbx_client.upload_file.assert_called_once()
    mock_dbx_client.delete_file.assert_called_once_with("/test.pdf")
    assert mock_os_remove.call_count == 2

@patch('processing.os.remove')
@patch('processing.os.path.exists', return_value=True)
@patch('processing.recognize', side_effect=TransientError("API limit"))
@patch('processing.convert_from_path')
def test_process_single_file_recognition_fails_transient(
    mock_convert, mock_recognize, mock_os_exists, mock_os_remove, mock_dbx_client, mock_file_entry
):
    """Тест, когда API распознавания возвращает временную ошибку."""
    mock_convert.return_value = [MagicMock()]

    with pytest.raises(TransientError, match="API limit"):
        process_single_file(mock_dbx_client, mock_file_entry)

    mock_dbx_client.download_file.assert_called_once()
    mock_dbx_client.upload_file.assert_not_called()
    mock_dbx_client.delete_file.assert_not_called()
    assert mock_os_remove.call_count > 0

@patch('processing.os.remove')
@patch('processing.os.path.exists', return_value=True)
@patch('processing.recognize')
@patch('processing.convert_from_path', side_effect=PermanentError("Corrupted PDF"))
def test_process_single_file_pdf_conversion_fails_permanent(
    mock_convert, mock_recognize, mock_os_exists, mock_os_remove, mock_dbx_client, mock_file_entry
):
    """Тест, когда конвертация PDF падает с перманентной ошибкой."""
    with pytest.raises(PermanentError, match="PDF conversion failed: Corrupted PDF"):
        process_single_file(mock_dbx_client, mock_file_entry)

    mock_dbx_client.download_file.assert_called_once()
    mock_convert.assert_called_once()
    mock_recognize.assert_not_called()
    mock_dbx_client.upload_file.assert_not_called()
    assert mock_os_remove.call_count > 0
