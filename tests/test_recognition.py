# tests/test_recognition.py
from unittest.mock import patch, MagicMock

# Импортируем тестируемую функцию
from recognition import recognize, get_openai_client
import recognition  # Импортируем модуль целиком


@patch("recognition.get_openai_client")
def test_recognize_success(mock_get_client, mock_settings):
    """
    Тест успешного вызова API распознавания.
    """
    # 1. Настройка мока
    mock_client_instance = MagicMock()
    mock_get_client.return_value = mock_client_instance

    mock_api_response = MagicMock()
    mock_api_response.choices[0].message.content = "Expected recognized text"
    mock_client_instance.chat.completions.create.return_value = mock_api_response

    fake_base64_image = "fake_base64_string"

    # 2. Вызов тестируемой функции
    # Поскольку get_settings используется в recognize, а мы его мокаем в conftest,
    # нам не нужно его передавать явно.
    result = recognize(fake_base64_image)

    # 3. Проверки
    mock_get_client.assert_called_once()
    mock_client_instance.chat.completions.create.assert_called_once()
    assert result == "Expected recognized text"


@patch("recognition.get_openai_client")
def test_recognize_api_error(mock_get_client, mock_settings):
    """
    Тест обработки ошибки при вызове API.
    """
    # 1. Настройка мока
    mock_client_instance = MagicMock()
    mock_get_client.return_value = mock_client_instance

    api_error = Exception("API connection failed")
    mock_client_instance.chat.completions.create.side_effect = api_error

    fake_base64_image = "another_fake_base64_string"

    # 2. Вызов и проверка исключения
    with patch("recognition.get_settings", return_value=mock_settings):
        try:
            recognize(fake_base64_image)
            # Если исключение не было вызвано, тест должен провалиться
            assert False, "Exception was not raised"
        except Exception as e:
            # 3. Проверка
            assert e == api_error

    mock_get_client.assert_called_once()
    mock_client_instance.chat.completions.create.assert_called_once()


# Дополнительный тест, чтобы убедиться, что кеширование клиента работает
@patch("recognition.OpenAI")
def test_get_openai_client_caching(mock_openai_class):
    """
    Тест, который проверяет, что клиент OpenAI создается только один раз.
    """
    # Сбрасываем "состояние" нашего модуля перед тестом
    recognition._client = None

    mock_client_instance = MagicMock()
    mock_openai_class.return_value = mock_client_instance

    # Вызываем функцию дважды
    client1 = get_openai_client()
    client2 = get_openai_client()

    # Проверяем, что обе переменные указывают на один и тот же объект
    assert client1 is client2
    # И самое главное: проверяем, что класс OpenAI был вызван для создания объекта только один раз
    mock_openai_class.assert_called_once()
