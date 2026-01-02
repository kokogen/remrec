# pdf_utils.py
import logging
from .config import get_settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def create_reflowed_pdf(page_contents: list[str], pdf_path: str):
    """
    Saves a list of text contents (one per page) to a multi-page PDF,
    reflowing the text to fit the page width and adding page breaks.
    """
    settings = get_settings()
    if not settings.FONT_PATH.exists():
        logging.error(
            f"Font file not found at {settings.FONT_PATH}. Cannot create PDF."
        )
        raise FileNotFoundError(f"Font file not found: {settings.FONT_PATH}")

    # Register the font
    pdfmetrics.registerFont(TTFont("DejaVuSans", str(settings.FONT_PATH)))

    # Basic setup for the document
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    # Create a custom style that uses our font
    custom_style = ParagraphStyle(
        name="CustomStyle",
        parent=styles["Normal"],
        fontName="DejaVuSans",
        fontSize=11,
        leading=14,
    )

    flowables = []
    # Process each page content
    for i, page_content in enumerate(page_contents):
        title_text = f"--- Page {i + 1} ---"

        # Replace newlines in the content with <br/> for ReportLab Paragraph
        content_text = page_content.replace("\n", "<br/>")

        # Add title paragraph
        flowables.append(Paragraph(title_text, styles["h2"]))
        # Add content paragraph
        flowables.append(Paragraph(content_text, custom_style))
        # Add a page break after each page's content, but not for the last one
        if i < len(page_contents) - 1:
            flowables.append(PageBreak())

    doc.build(flowables)
    logging.info(f"Reflowed PDF created at {pdf_path}")
