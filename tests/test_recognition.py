# tests/test_recognition.py
from unittest.mock import patch, MagicMock
from src.recognition import recognize

# The mock_settings fixture is now in conftest.py

@patch("src.recognition.get_settings")
@patch("src.recognition.OpenAI")
def test_recognize_success(MockOpenAI, mock_get_settings, mock_settings):
    """Test successful recognition."""
    # Setup
    mock_get_settings.return_value = mock_settings
    mock_openai_client = MockOpenAI.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = "Recognized text"
    mock_openai_client.chat.completions.create.return_value = mock_response
    
    # Action
    recognized_text = recognize("fake_base64_string")
    
    # Asserts
    assert recognized_text == "Recognized text"
    mock_openai_client.chat.completions.create.assert_called_once()
