# tests/test_recognition.py
import pytest
from unittest.mock import patch, MagicMock
from recognition import recognize_handwriting

@pytest.fixture
def mock_settings():
    """Fixture for mock settings."""
    settings = MagicMock()
    settings.RECOGNITION_PROMPT = "Recognize this"
    settings.RECOGNITION_MODEL = "gemini-pro-vision"
    return settings

@patch("recognition.get_settings")
@patch("recognition.OpenAI")
def test_recognize_handwriting_success(MockOpenAI, mock_get_settings, mock_settings):
    """Test successful handwriting recognition."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_openai_client = MockOpenAI.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Recognized text"
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    # Action
    with patch("builtins.open", new_callable=pytest.mock.mock_open, read_data=b"imagedata"):
        texts = recognize_handwriting(["img1.png"])
    
    # Asserts
    assert texts == ["Recognized text"]
    mock_openai_client.chat.completions.create.assert_called_once()