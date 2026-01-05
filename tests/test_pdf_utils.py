# tests/test_pdf_utils.py
from unittest.mock import patch
from src.pdf_utils import create_reflowed_pdf


@patch("src.pdf_utils.Paragraph")  # Patch Paragraph directly
@patch("src.pdf_utils.TTFont")
@patch("src.pdf_utils.SimpleDocTemplate")
@patch("src.pdf_utils.pdfmetrics")
@patch("src.pdf_utils.get_settings")
def test_create_reflowed_pdf_with_font(
    mock_get_settings,
    mock_pdfmetrics,
    MockSimpleDocTemplate,
    MockTTFont,
    MockParagraph,
    mock_settings,
):
    """
    Test creating a reflowed PDF when the custom font is found.
    """
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_settings.FONT_PATH.exists.return_value = True  # Simulate font exists
    mock_doc = MockSimpleDocTemplate.return_value
    texts = ["Page 1", "Page 2"]
    output_pdf = "/fake/path/output.pdf"

    # Action
    create_reflowed_pdf(texts, output_pdf)

    # Assert
    mock_settings.FONT_PATH.exists.assert_called_once()
    MockTTFont.assert_called_once_with("DejaVuSans", str(mock_settings.FONT_PATH))
    mock_pdfmetrics.registerFont.assert_called_once()
    mock_pdfmetrics.registerFontFamily.assert_called_once_with(
        "DejaVuSans",
        normal="DejaVuSans",
        bold="DejaVuSans",
        italic="DejaVuSans",
        boldItalic="DejaVuSans",
    )
    mock_doc.build.assert_called_once()

    # Check that the Paragraph style uses DejaVuSans
    # The last call to Paragraph is the one with the content
    last_call_args = MockParagraph.call_args.args
    style_used = last_call_args[1]
    assert style_used.fontName == "DejaVuSans"


@patch("src.pdf_utils.Paragraph")
@patch("src.pdf_utils.SimpleDocTemplate")
@patch("src.pdf_utils.pdfmetrics")
@patch("src.pdf_utils.get_settings")
def test_create_reflowed_pdf_font_fallback(
    mock_get_settings,
    mock_pdfmetrics,
    MockSimpleDocTemplate,
    MockParagraph,
    mock_settings,
):
    """
    Test creating a reflowed PDF falls back to Helvetica when the custom font is missing.
    """
    # Arrange
    mock_get_settings.return_value = mock_settings
    mock_settings.FONT_PATH.exists.return_value = False  # Simulate font is missing
    mock_doc = MockSimpleDocTemplate.return_value
    texts = ["Page 1"]
    output_pdf = "/fake/path/output.pdf"

    # Action
    create_reflowed_pdf(texts, output_pdf)

    # Assert
    mock_settings.FONT_PATH.exists.assert_called_once()
    mock_pdfmetrics.registerFont.assert_not_called()  # Should not be called for fallback
    mock_pdfmetrics.registerFontFamily.assert_not_called()

    # Check that the Paragraph style uses Helvetica
    # The last call to Paragraph is the one with the content
    last_call_args = MockParagraph.call_args.args
    style_used = last_call_args[1]
    assert style_used.fontName == "Helvetica"

    mock_doc.build.assert_called_once()
