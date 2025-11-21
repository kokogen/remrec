# processing.py
import logging
import os
import dropbox
import openai
from pdf2image import convert_from_path, exceptions as pdf2image_exceptions

from config import settings
from dbox import DropboxClient
from exceptions import PermanentError, TransientError
from recognition import image_to_base64, recognize
from pdf_utils import txt_to_pdf_line_by_line

def process_single_file(dbx_client: DropboxClient, file_entry: dropbox.files.FileMetadata):
    """
    Full processing cycle for a single file with detailed error handling at each step.
    Raises TransientError or PermanentError on failure.
    """
    local_pdf_path = settings.LOCAL_BUF_DIR / file_entry.name
    result_pdf_path = settings.LOCAL_BUF_DIR / f"recognized_{file_entry.name}"

    try:
        # 1. Download the file
        try:
            dbx_client.download_file(file_entry.path_display, local_pdf_path)
        except dropbox.exceptions.ApiError as e:
            # Dropbox API errors can be temporary
            raise TransientError(f"Dropbox API error during download: {e}") from e

        # 2. Convert PDF to images
        try:
            logging.info(f"Converting PDF {file_entry.name} to images...")
            pages = convert_from_path(str(local_pdf_path), dpi=settings.PDF_DPI)
            if not pages:
                raise PermanentError("PDF conversion resulted in 0 pages.")
        except (pdf2image_exceptions.PDFPageCountError, pdf2image_exceptions.PDFSyntaxError) as e:
            # These errors indicate a corrupted or invalid PDF
            raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
        except Exception as e:
            # Any other conversion error is likely also permanent for this file
            raise PermanentError(f"PDF conversion failed: {e}") from e

        # 3. Recognize text
        recognized_texts = []
        for i, page in enumerate(pages):
            logging.info(f"Recognizing page {i+1}/{len(pages)}...")
            try:
                img_b64 = image_to_base64(page)
                text = recognize(img_b64)
                recognized_texts.append(f"--- Page {i+1} ---\n{text}")
            except openai.APIConnectionError as e:
                raise TransientError("Recognition API connection error") from e
            except openai.RateLimitError as e:
                raise TransientError("Recognition API rate limit exceeded") from e
            except openai.BadRequestError as e:
                raise PermanentError(f"Recognition API bad request (invalid image?): {e}") from e
            except openai.AuthenticationError as e:
                raise PermanentError(f"Recognition API authentication error (check API key): {e}") from e

        full_text = "\n\n".join(recognized_texts)

        # 4. Create a result PDF from the text
        txt_to_pdf_line_by_line(full_text, result_pdf_path)

        # 5. Upload the result to Dropbox
        try:
            dest_path = f"{settings.DROPBOX_DEST_DIR}/{result_pdf_path.name}"
            dbx_client.upload_file(result_pdf_path, dest_path)
        except dropbox.exceptions.ApiError as e:
            raise TransientError(f"Dropbox API error during upload: {e}") from e

        # 6. Delete the original file
        try:
            dbx_client.delete_file(file_entry.path_display)
        except dropbox.exceptions.ApiError as e:
            # If deletion fails, it's not critical, but should be logged
            logging.warning(f"Could not delete original file {file_entry.name} after processing. Error: {e}")

        logging.info(f"Successfully processed and deleted {file_entry.name}")

    finally:
        # 7. Clean up local files in any case
        logging.info("Cleaning up local files...")
        if os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)
        if os.path.exists(result_pdf_path):
            os.remove(result_pdf_path)

