# tests/test_pdf_utils.py
import pytest
from unittest.mock import patch, MagicMock, call, ANY
from reportlab.platypus import Paragraph, PageBreak

from pdf_utils import create_reflowed_pdf

# We need to mock the classes from reportlab that are used in the function
@patch('pdf_utils.settings')
@patch('pdf_utils.SimpleDocTemplate')
def test_create_reflowed_pdf_success(
    mock_doc_template, mock_config
):
    """
    Test the successful creation of a reflowed, multi-page PDF.
    """
    # 1. Setup mocks
    # Mock the FONT_PATH to behave like a Path object with an .exists() method
    # and a string representation that points to the real font file.
    font_path_mock = MagicMock()
    font_path_mock.exists.return_value = True
    font_path_mock.__str__.return_value = "DejaVuSans.ttf"
    mock_config.FONT_PATH = font_path_mock
    
    mock_doc_instance = MagicMock()
    mock_doc_template.return_value = mock_doc_instance
    
    # Test content spanning multiple pages
    test_content = (
        "--- Page 1 ---\n"
        "This is the first line of page one.\nThis is the second."
        "\n\n"
        "--- Page 2 ---\n"
        "This is the only line of page two."
    )
    pdf_path = "/fake/path/doc.pdf"

    # 2. Call the function
    create_reflowed_pdf(test_content, pdf_path)

    # 3. Assertions
    mock_config.FONT_PATH.exists.assert_called_once()
    
    # Check that SimpleDocTemplate was initialized correctly
    mock_doc_template.assert_called_once_with(pdf_path, pagesize=ANY)

    # Check that the document was built with a list of flowables
    mock_doc_instance.build.assert_called_once()
    
    # Inspect the list of flowables passed to the build method
    flowables = mock_doc_instance.build.call_args[0][0]
    
    # Expected structure: [Para(Title1), Para(Content1), PageBreak, Para(Title2), Para(Content2)]
    assert len(flowables) == 5
    
    # Check the types of flowables
    assert isinstance(flowables[0], Paragraph) # Title 1
    assert isinstance(flowables[1], Paragraph) # Content 1
    assert isinstance(flowables[2], PageBreak) # Page Break
    assert isinstance(flowables[3], Paragraph) # Title 2
    assert isinstance(flowables[4], Paragraph) # Content 2

    # Check the content of the Paragraphs, ensuring newlines were replaced
    assert flowables[0].text == "--- Page 1 ---"
    assert flowables[1].text == "This is the first line of page one.<br/>This is the second."
    assert flowables[3].text == "--- Page 2 ---"
    assert flowables[4].text == "This is the only line of page two."


@patch('pdf_utils.settings')
def test_create_reflowed_pdf_font_not_found(mock_config):
    """
    Test that a FileNotFoundError is raised if the font file does not exist.
    """
    # 1. Setup mock
    mock_config.FONT_PATH.exists.return_value = False

    # 2. Call and assert exception
    with pytest.raises(FileNotFoundError, match="Font file not found"):
        create_reflowed_pdf("some text", "/fake/path.pdf")

    # 3. Assert check was made
    mock_config.FONT_PATH.exists.assert_called_once()
