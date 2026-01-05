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
    font_name = "DejaVuSans"

    # --- Font Registration ---
    font_path = settings.FONT_PATH
    bold_font_path = font_path.with_name("DejaVuSans-Bold.ttf")
    italic_font_path = font_path.with_name("DejaVuSans-Oblique.ttf")
    bold_italic_font_path = font_path.with_name("DejaVuSans-BoldOblique.ttf")

    # Register the base font if it exists
    if font_path.exists():
        pdfmetrics.registerFont(TTFont(font_name, str(font_path)))

        # Register bold and italic variants if they exist, otherwise fallback to normal
        bold_font_name = font_name
        if bold_font_path.exists():
            bold_font_name = "DejaVuSans-Bold"
            pdfmetrics.registerFont(TTFont(bold_font_name, str(bold_font_path)))
        else:
            logging.warning(f"Bold font not found at {bold_font_path}, using normal.")

        italic_font_name = font_name
        if italic_font_path.exists():
            italic_font_name = "DejaVuSans-Oblique"
            pdfmetrics.registerFont(TTFont(italic_font_name, str(italic_font_path)))
        else:
            logging.warning(
                f"Italic font not found at {italic_font_path}, using normal."
            )

        bold_italic_font_name = font_name
        if bold_italic_font_path.exists():
            bold_italic_font_name = "DejaVuSans-BoldOblique"
            pdfmetrics.registerFont(
                TTFont(bold_italic_font_name, str(bold_italic_font_path))
            )

        pdfmetrics.registerFontFamily(
            font_name,
            normal=font_name,
            bold=bold_font_name,
            italic=italic_font_name,
            boldItalic=bold_italic_font_name,
        )
    else:
        logging.warning(
            f"Font file not found at {font_path}. Using default ReportLab font."
        )
        font_name = "Helvetica"  # Fallback to a default font

    # Basic setup for the document
    doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
    styles = getSampleStyleSheet()
    # Create a custom style that uses our font
    custom_style = ParagraphStyle(
        name="CustomStyle",
        parent=styles["Normal"],
        fontName=font_name,
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
