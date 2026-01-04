# processing.py
import logging
import os
import openai
from pdf2image import convert_from_path, exceptions as pdf2image_exceptions
from typing import Any

from .config import get_settings
from .storage.base import StorageClient
from .exceptions import PermanentError, TransientError
from .recognition import image_to_base64, recognize
from .pdf_utils import create_reflowed_pdf


def process_single_file(storage_client: StorageClient, file_entry: Any):
    """
    Full processing cycle for a single file with detailed error handling at each step.
    Works with any client that implements the StorageClient interface.
    """
    settings = get_settings()

    is_dropbox = settings.STORAGE_PROVIDER == "dropbox"

    if is_dropbox:
        file_name = file_entry.name
        file_path = file_entry.path_display
    else:  # Google Drive
        file_name = file_entry.get("name")
        file_id = file_entry.get("id")  # Use the file ID directly
        # file_path is not used for Google Drive download/delete anymore

    local_pdf_path = settings.LOCAL_BUF_DIR / file_name
    result_pdf_path = settings.LOCAL_BUF_DIR / f"recognized_{file_name}"

    try:
        # 1. Download the file
        try:
            if is_dropbox:
                storage_client.download_file(file_path, local_pdf_path)
            else:  # Google Drive
                storage_client.download_file(file_id, local_pdf_path)  # Pass file_id
        except Exception as e:
            raise TransientError(f"API error during download: {e}") from e

        # 2. Convert PDF to images
        try:
            logging.info(f"Converting PDF {file_name} to images...")
            pages = convert_from_path(str(local_pdf_path), dpi=settings.PDF_DPI)
            if not pages:
                raise PermanentError("PDF conversion resulted in 0 pages.")
        except (
            pdf2image_exceptions.PDFPageCountError,
            pdf2image_exceptions.PDFSyntaxError,
        ) as e:
            raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
        except Exception as e:
            raise PermanentError(f"PDF conversion failed: {e}") from e

        # 3. Recognize text
        recognized_texts = []
        for i, page in enumerate(pages):
            logging.info(f"Recognizing page {i + 1}/{len(pages)}...")
            try:
                img_b64 = image_to_base64(page)
                text = recognize(img_b64)
                recognized_texts.append(text)
            except openai.APIConnectionError as e:
                raise TransientError("Recognition API connection error") from e
            except openai.RateLimitError as e:
                raise TransientError("Recognition API rate limit exceeded") from e
            except openai.BadRequestError as e:
                raise PermanentError(
                    f"Recognition API bad request (invalid image?): {e}"
                ) from e
            except openai.AuthenticationError as e:
                raise PermanentError(
                    f"Recognition API authentication error (check API key): {e}"
                ) from e

        # 4. Create a result PDF from the text
        create_reflowed_pdf(recognized_texts, result_pdf_path)

        # 5. Upload the result
        try:
            # Use the new abstract upload method
            storage_client.upload_file(
                local_path=result_pdf_path,
                folder_id=settings.DST_FOLDER,
                filename=result_pdf_path.name,
            )
        except Exception as e:
            raise TransientError(f"API error during upload: {e}") from e

        # 6. Delete the original file
        try:
            if is_dropbox:
                storage_client.delete_file(file_path)
            else:  # Google Drive
                storage_client.delete_file(file_id)  # Use file_id for Google Drive
        except Exception as e:
            logging.warning(
                f"Could not delete original file {file_name} after processing. Error: {e}"
            )

        logging.info(f"Successfully processed and deleted {file_name}")

    finally:
        # 7. Clean up local files in any case
        logging.info("Cleaning up local files...")
        if os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)
        if os.path.exists(result_pdf_path):
            os.remove(result_pdf_path)
