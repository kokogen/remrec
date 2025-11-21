# pdf_utils.py
import logging
from config import settings
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def txt_to_pdf_line_by_line(txt_content: str, pdf_path: str):
    """Saves text content to a PDF, preserving line breaks."""
    if not settings.FONT_PATH.exists():
        logging.error(f"Font file not found at {settings.FONT_PATH}. Cannot create PDF.")
        raise FileNotFoundError(f"Font file not found: {settings.FONT_PATH}")

    pdfmetrics.registerFont(TTFont('DejaVuSans', str(settings.FONT_PATH)))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER)
    style = ParagraphStyle(
        name='LineStyle', fontName='DejaVuSans', fontSize=12, leading=15
    )

    flowables = [Paragraph(line, style) for line in txt_content.split('\n')]
    doc.build(flowables)
    logging.info(f"PDF created at {pdf_path}")

