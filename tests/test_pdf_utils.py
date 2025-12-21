# tests/test_pdf_utils.py
import pytest
from unittest.mock import patch, MagicMock
from pdf_utils import create_text_pdf_from_images
from pathlib import Path

@patch("pdf_utils.Image")
@patch("pdf_utils.reportlab.platypus.SimpleDocTemplate")
@patch("pdf_utils.reportlab.platypus.ImageReader")
def test_create_text_pdf_from_images(MockImageReader, MockSimpleDocTemplate, MockImage):
    """Test creating a PDF from a list of images and texts."""
    # Setup
    mock_doc = MockSimpleDocTemplate.return_value
    mock_image = MagicMock()
    mock_image.size = (100, 200)
    MockImage.open.return_value = mock_image
    
    image_paths = [Path("img1.png"), Path("img2.png")]
    texts = ["text1", "text2"]
    output_pdf_path = Path("output.pdf")
    
    # Action
    create_text_pdf_from_images(image_paths, texts, output_pdf_path)
    
    # Asserts
    assert MockImage.open.call_count == 2
    assert mock_doc.build.call_count == 1