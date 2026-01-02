# tests/test_pdf_utils.py
from unittest.mock import patch, ANY

from src.pdf_utils import create_reflowed_pdf


@patch("src.pdf_utils.get_settings")
@patch("src.pdf_utils.pdfmetrics.registerFont")
@patch("src.pdf_utils.TTFont")
@patch("src.pdf_utils.SimpleDocTemplate")
@patch("src.pdf_utils.ParagraphStyle")
def test_create_reflowed_pdf(
    MockParagraphStyle,
    MockSimpleDocTemplate,
    MockTTFont,
    mock_registerFont,
    mock_get_settings,
):
    """Test creating a reflowed PDF from text."""
    # Setup
    # Force the style to use a default font during the test to avoid mapping errors
    mock_style = MockParagraphStyle.return_value
    mock_style.fontName = "Helvetica"
    mock_style.textTransform = None  # Prevent ValueError in reportlab

    mock_doc = MockSimpleDocTemplate.return_value
    texts = ["Page 1", "Page 2"]
    output_pdf = "/fake/path/output.pdf"

    # Action
    create_reflowed_pdf(texts, output_pdf)

    # Asserts
    mock_get_settings.assert_called_once()
    mock_registerFont.assert_called_once()
    MockSimpleDocTemplate.assert_called_once_with(str(output_pdf), pagesize=ANY)
    mock_doc.build.assert_called_once()
    # Verify that the style was created with the correct font name in the implementation
    MockParagraphStyle.assert_called_with(
        name='CustomStyle',
        parent=ANY,
        fontName='DejaVuSans',
        fontSize=11,
        leading=14
    )
