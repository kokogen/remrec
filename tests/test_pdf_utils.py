# tests/test_pdf_utils.py
import pytest
from unittest.mock import patch, MagicMock, call, ANY

from pdf_utils import txt_to_pdf_line_by_line

# Патчим все зависимости, чтобы изолировать нашу функцию
@patch('pdf_utils.settings')
@patch('pdf_utils.pdfmetrics.registerFont')
@patch('pdf_utils.TTFont')
@patch('pdf_utils.SimpleDocTemplate')
@patch('pdf_utils.Paragraph')
def test_txt_to_pdf_success(
    mock_paragraph, mock_doc_template, mock_ttfont, mock_register_font, mock_config
):
    """
    Тест успешного вызова функции txt_to_pdf_line_by_line.
    """
    # 1. Настройка моков
    mock_config.FONT_PATH.exists.return_value = True
    mock_doc_instance = MagicMock()
    mock_doc_template.return_value = mock_doc_instance
    
    test_content = "Line 1\nLine 2"
    pdf_path = "/fake/path/doc.pdf"

    # 2. Вызов функции
    txt_to_pdf_line_by_line(test_content, pdf_path)

    # 3. Проверки
    mock_config.FONT_PATH.exists.assert_called_once()
    mock_register_font.assert_called_once()
    mock_doc_template.assert_called_once_with(pdf_path, pagesize=pytest.approx((612.0, 792.0)))

    # Проверяем, что Paragraph был вызван для каждой строки
    expected_calls = [call("Line 1", ANY), call("Line 2", ANY)]
    # Используем ANY из unittest.mock, так как нам не важен объект стиля
    mock_paragraph.assert_has_calls(expected_calls)

    # Проверяем, что итоговый документ был построен
    mock_doc_instance.build.assert_called_once()

@patch('pdf_utils.settings')
def test_txt_to_pdf_font_not_found(mock_config):
    """
    Тест на случай, когда файл шрифта не найден.
    """
    # 1. Настройка мока
    mock_config.FONT_PATH.exists.return_value = False

    # 2. Вызов и проверка исключения
    with pytest.raises(FileNotFoundError, match="Font file not found"):
        txt_to_pdf_line_by_line("some text", "/fake/path.pdf")

    # 3. Проверка
    mock_config.FONT_PATH.exists.assert_called_once()

