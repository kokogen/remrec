# tests/test_recognition.py
from unittest.mock import patch, MagicMock
import pytest

import src.recognition as recognition
from src.exceptions import RecognitionPermanentError, RecognitionTransientError
from src.recognition import _extract_recognized_text, recognize

# The mock_settings fixture is now in conftest.py


@pytest.fixture(autouse=True)
def reset_openai_client():
    """Ensure recognition tests do not reuse a cached client across cases."""
    recognition._client = None
    yield
    recognition._client = None


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
    MockOpenAI.assert_called_once_with(
        base_url=mock_settings.OPENAI_BASE_URL,
        api_key=mock_settings.OPENAI_API_KEY,
        timeout=mock_settings.OPENAI_TIMEOUT_SECONDS,
        max_retries=mock_settings.OPENAI_MAX_RETRIES,
    )
    mock_openai_client.chat.completions.create.assert_called_once()


@patch("src.recognition.get_settings")
@patch("src.recognition.OpenAI")
def test_recognize_rate_limit_is_transient(
    MockOpenAI, mock_get_settings, mock_settings, monkeypatch
):
    """Recognition provider rate limits should be surfaced as retryable errors."""

    class FakeRateLimitError(Exception):
        pass

    monkeypatch.setattr(recognition.openai, "RateLimitError", FakeRateLimitError)
    mock_get_settings.return_value = mock_settings
    mock_openai_client = MockOpenAI.return_value
    mock_openai_client.chat.completions.create.side_effect = FakeRateLimitError(
        "rate limit"
    )

    with pytest.raises(RecognitionTransientError, match="rate limit"):
        recognize("fake_base64_string")


@patch("src.recognition.get_settings")
@patch("src.recognition.OpenAI")
def test_recognize_empty_response_is_permanent(
    MockOpenAI, mock_get_settings, mock_settings
):
    """Malformed successful responses should not be retried forever."""
    mock_get_settings.return_value = mock_settings
    mock_openai_client = MockOpenAI.return_value
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = ""
    mock_openai_client.chat.completions.create.return_value = mock_response

    with pytest.raises(RecognitionPermanentError, match="empty text"):
        recognize("fake_base64_string")


def _completion_with_content(content):
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = content
    return completion


def test_extract_recognized_text_strips_text():
    """Recognition text should be normalized before PDF generation."""
    completion = _completion_with_content("  Recognized text\n")

    text = _extract_recognized_text(completion, max_text_chars=100)

    assert text == "Recognized text"


def test_extract_recognized_text_malformed_response_is_permanent():
    """Malformed successful API responses should not be retried forever."""
    completion = MagicMock()
    completion.choices = []

    with pytest.raises(RecognitionPermanentError, match="malformed response"):
        _extract_recognized_text(completion, max_text_chars=100)


def test_extract_recognized_text_whitespace_response_is_permanent():
    """Whitespace-only API responses should not produce blank PDFs."""
    completion = _completion_with_content("   \n\t")

    with pytest.raises(RecognitionPermanentError, match="empty text"):
        _extract_recognized_text(completion, max_text_chars=100)


def test_extract_recognized_text_non_string_response_is_permanent():
    """Non-string content is not valid recognized text."""
    completion = _completion_with_content([{"type": "text", "text": "hello"}])

    with pytest.raises(RecognitionPermanentError, match="non-text content"):
        _extract_recognized_text(completion, max_text_chars=100)


def test_extract_recognized_text_too_large_response_is_permanent():
    """Oversized recognition responses should be rejected before PDF generation."""
    completion = _completion_with_content("x" * 101)

    with pytest.raises(RecognitionPermanentError, match="too much text"):
        _extract_recognized_text(completion, max_text_chars=100)
