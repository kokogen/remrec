# tests/test_dbox.py
import pytest
from unittest.mock import patch, ANY
from dropbox.exceptions import ApiError
from dropbox.files import ListFolderResult, FileMetadata

from dbox import DropboxClient


@patch("dbox.dropbox.Dropbox")
def test_dropbox_client_init_success(MockDropbox):
    """Тест успешной инициализации клиента."""
    # 1. Настройка
    mock_dbx_instance = MockDropbox.return_value

    # 2. Вызов
    client = DropboxClient("key", "secret", "token")

    # 3. Проверки
    MockDropbox.assert_called_once_with(
        app_key="key", app_secret="secret", oauth2_refresh_token="token"
    )
    mock_dbx_instance.users_get_current_account.assert_called_once()
    assert client.dbx == mock_dbx_instance


@patch("dbox.dropbox.Dropbox", side_effect=Exception("Auth failed"))
def test_dropbox_client_init_failure(MockDropbox):
    """Тест неудачной инициализации клиента."""
    with pytest.raises(Exception, match="Auth failed"):
        DropboxClient("key", "secret", "token")


@pytest.fixture
def client():
    """Фикстура, которая создает экземпляр клиента с замоканным SDK."""
    with patch("dbox.dropbox.Dropbox") as MockDropbox:
        mock_dbx_instance = MockDropbox.return_value
        client_instance = DropboxClient("key", "secret", "token")
        # Сбрасываем счетчики вызовов после инициализации для чистоты тестов
        mock_dbx_instance.reset_mock()
        yield client_instance


def test_list_files_success_single_page(client):
    """Тест успешного получения списка файлов (одна страница)."""
    mock_result = ListFolderResult(
        entries=[FileMetadata(name="test.pdf")], has_more=False, cursor=None
    )
    client.dbx.files_list_folder.return_value = mock_result

    files = client.list_files("/some_path")

    client.dbx.files_list_folder.assert_called_once_with("/some_path")
    client.dbx.files_list_folder_continue.assert_not_called()
    assert len(files) == 1
    assert files[0].name == "test.pdf"


def test_list_files_with_pagination(client):
    """Тест успешного получения списка файлов с пагинацией."""
    # 1. Настройка моков для двух страниц
    mock_result_page1 = ListFolderResult(
        entries=[FileMetadata(name="file1.pdf")], has_more=True, cursor="cursor123"
    )
    mock_result_page2 = ListFolderResult(
        entries=[FileMetadata(name="file2.pdf")], has_more=False, cursor=None
    )

    # Настраиваем, чтобы первый вызов вернул первую страницу, а второй - вторую
    client.dbx.files_list_folder.return_value = mock_result_page1
    client.dbx.files_list_folder_continue.return_value = mock_result_page2

    # 2. Вызов
    files = client.list_files("/some_path")

    # 3. Проверки
    client.dbx.files_list_folder.assert_called_once_with("/some_path")
    client.dbx.files_list_folder_continue.assert_called_once_with("cursor123")
    assert len(files) == 2
    assert files[0].name == "file1.pdf"
    assert files[1].name == "file2.pdf"


def test_list_files_api_error(client):
    """Тест ошибки API при получении списка файлов."""
    client.dbx.files_list_folder.side_effect = ApiError(None, None, None, None)

    files = client.list_files("/some_path")

    assert files == []


def test_download_file_success(client):
    """Тест успешной загрузки файла."""
    client.download_file("/dbx_path", "/local_path")
    client.dbx.files_download_to_file.assert_called_once_with(
        "/local_path", "/dbx_path"
    )


def test_download_file_api_error(client):
    """Тест ошибки API при скачивании файла."""
    client.dbx.files_download_to_file.side_effect = ApiError(None, None, None, None)
    with pytest.raises(ApiError):
        client.download_file("/dbx_path", "/local_path")


# Аналогичные тесты можно написать для upload_file, move_file, delete_file.
# Для краткости добавим один пример для upload.


@patch("builtins.open")
def test_upload_file_success(mock_open, client):
    """Тест успешной выгрузки файла."""
    mock_file_handle = mock_open.return_value.__enter__.return_value
    mock_file_handle.read.return_value = b"file_content"

    # Создаем мок для Path-объекта
    mock_local_path = MagicMock()
    mock_local_path.stat.return_value.st_size = 100  # Размер меньше чанка

    client.upload_file(mock_local_path, "/dbx_path")

    mock_open.assert_called_once_with(mock_local_path, "rb")
    client.dbx.files_upload.assert_called_once_with(
        b"file_content", "/dbx_path", mode=ANY
    )


def test_delete_file_success(client):
    """Тест успешного удаления файла."""
    client.delete_file("/dbx_path")
    client.dbx.files_delete_v2.assert_called_once_with("/dbx_path")


def test_delete_file_api_error(client):
    """Тест ошибки при удалении файла."""
    client.dbx.files_delete_v2.side_effect = ApiError(None, None, None, None)
    with pytest.raises(ApiError):
        client.delete_file("/dbx_path")
