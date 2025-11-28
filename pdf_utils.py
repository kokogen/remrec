# pdf_utils.py
import logging
import re
from config import settings
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def create_reflowed_pdf(txt_content: str, pdf_path: str):
    """
    Saves text content to a multi-page PDF, reflowing the text to fit the
    page width and creating page breaks based on a separator.
    """
    if not settings.FONT_PATH.exists():
        logging.error(f"Font file not found at {settings.FONT_PATH}. Cannot create PDF.")
        raise FileNotFoundError(f"Font file not found: {settings.FONT_PATH}")

    # Register the font
    pdfmetrics.registerFont(TTFont('DejaVuSans', str(settings.FONT_PATH)))

    # Basic setup for the document
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    # Create a custom style that uses our font
    custom_style = ParagraphStyle(
        name='CustomStyle',
        parent=styles['Normal'],
        fontName='DejaVuSans',
        fontSize=11,
        leading=14,
    )

    flowables = []
    # Split the text by the page separator. The separator is '--- Page X ---'
    # We use a regex to split and keep the separator as a title.
    pages = re.split(r'(\n*--- Page \d+ ---\n*)', txt_content)

    # The first element might be empty if the text starts with the separator
    if pages and not pages[0].strip():
        pages.pop(0)

    # Process pages in pairs: [separator, content, separator, content, ...]
    for i in range(0, len(pages), 2):
        if i + 1 < len(pages):
            title_text = pages[i].strip()
            content_text = pages[i+1].strip()
            
            # Replace newlines in the content with <br/> for ReportLab Paragraph
            content_text = content_text.replace('\n', '<br/>')

            # Add title paragraph
            flowables.append(Paragraph(title_text, styles['h2']))
            # Add content paragraph
            flowables.append(Paragraph(content_text, custom_style))
            # Add a page break after each page's content, but not for the last one
            if i + 2 < len(pages):
                flowables.append(PageBreak())

    doc.build(flowables)
    logging.info(f"Reflowed PDF created at {pdf_path}")
