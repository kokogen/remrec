# tests/test_recognition.py
import pytest
from unittest.mock import patch, MagicMock

# Импортируем тестируемую функцию
from recognition import recognize


@patch("recognition.OpenAI")
def test_recognize_success(mock_openai_class, mock_settings):
    """
    Тест успешного вызова API распознавания.
    """
    # 1. Настройка мока
    # Мы имитируем и сам класс OpenAI, и объект, который он создает
    mock_client_instance = MagicMock()
    mock_openai_class.return_value = mock_client_instance

    # Настраиваем мок для ответа от API
    mock_api_response = MagicMock()
    mock_api_response.choices[0].message.content = "Expected recognized text"
    mock_client_instance.chat.completions.create.return_value = mock_api_response

    fake_base64_image = "fake_base64_string"

    # 2. Вызов тестируемой функции
    result = recognize(fake_base64_image)

    # 3. Проверки
    # Убеждаемся, что клиент OpenAI был создан с правильными параметрами из mock_settings
    mock_openai_class.assert_called_once_with(
        base_url=mock_settings.OPENAI_BASE_URL, api_key=mock_settings.OPENAI_API_KEY
    )

    # Проверяем, что метод create был вызван один раз
    mock_client_instance.chat.completions.create.assert_called_once()

    # Проверяем, что результат функции соответствует тому, что вернул мок
    assert result == "Expected recognized text"


@patch("recognition.OpenAI")
def test_recognize_api_error(mock_openai_class, mock_settings):
    """
    Тест обработки ошибки при вызове API.
    """
    # 1. Настройка мока для выброса исключения
    mock_client_instance = MagicMock()
    mock_openai_class.return_value = mock_client_instance

    api_error = Exception("API connection failed")
    mock_client_instance.chat.completions.create.side_effect = api_error

    fake_base64_image = "another_fake_base64_string"

    # 2. Вызов и проверка исключения
    # Используем pytest.raises для проверки, что функция действительно выбросила исключение
    with pytest.raises(Exception) as excinfo:
        recognize(fake_base64_image)

    # 3. Проверка
    # Убеждаемся, что это именно то исключение, которое мы "запланировали"
    assert excinfo.value == api_error
    mock_openai_class.assert_called_once_with(
        base_url=mock_settings.OPENAI_BASE_URL, api_key=mock_settings.OPENAI_API_KEY
    )
    mock_client_instance.chat.completions.create.assert_called_once()
