# tests/test_pdf_utils.py
from unittest.mock import patch, MagicMock
from src.pdf_utils import create_reflowed_pdf
from pathlib import Path

@patch("src.pdf_utils.pdfmetrics.registerFont")
@patch("src.pdf_utils.TTFont")
@patch("src.pdf_utils.SimpleDocTemplate")
def test_create_reflowed_pdf_from_text(MockSimpleDocTemplate, MockTTFont, mock_registerFont):
    """Test creating a PDF from a list of texts."""
    # Setup
    mock_doc = MockSimpleDocTemplate.return_value
    
    texts = ["This is page 1 content.", "This is page 2 content with more text."]
    output_pdf_path = Path("output.pdf")
    
    # Action
    create_reflowed_pdf(texts, output_pdf_path)
    
    # Asserts
    mock_doc.build.assert_called_once()
    assert len(mock_doc.build.call_args.args[0]) > 0 # Check that flowables were passed