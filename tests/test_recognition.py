# tests/test_recognition.py
import pytest
from unittest.mock import patch, MagicMock

# Импортируем тестируемую функцию
from recognition import recognize


@patch("recognition.client.chat.completions.create")
def test_recognize_success(mock_create_completion):
    """
    Тест успешного вызова API распознавания.
    """
    # 1. Настройка мока
    # Мы создаем "магический" мок, который позволяет имитировать вложенную структуру ответа API
    mock_response = MagicMock()
    mock_response.choices[0].message.content = "Expected recognized text"
    mock_create_completion.return_value = mock_response

    fake_base64_image = "fake_base64_string"

    # 2. Вызов тестируемой функции
    result = recognize(fake_base64_image)

    # 3. Проверки
    # Проверяем, что метод create был вызван один раз
    mock_create_completion.assert_called_once()

    # Проверяем, что результат функции соответствует тому, что вернул мок
    assert result == "Expected recognized text"


@patch("recognition.client.chat.completions.create")
def test_recognize_api_error(mock_create_completion):
    """
    Тест обработки ошибки при вызове API.
    """
    # 1. Настройка мока для выброса исключения
    api_error = Exception("API connection failed")
    mock_create_completion.side_effect = api_error

    fake_base64_image = "another_fake_base64_string"

    # 2. Вызов и проверка исключения
    # Используем pytest.raises для проверки, что функция действительно выбросила исключение
    with pytest.raises(Exception) as excinfo:
        recognize(fake_base64_image)

    # 3. Проверка
    # Убеждаемся, что это именно то исключение, которое мы "запланировали"
    assert excinfo.value == api_error
    mock_create_completion.assert_called_once()
