# processing.py
import logging
import os
import openai
from pdf2image import convert_from_path, exceptions as pdf2image_exceptions
from typing import List
from pathlib import Path
from PIL.Image import Image

from .config import get_settings
from .storage.base import StorageClient
from .storage.dto import FileMetadata
from .exceptions import PermanentError, TransientError
from .recognition import image_to_base64, recognize
from .pdf_utils import create_reflowed_pdf


def _download_and_convert(
    storage_client: StorageClient, file_id: str, local_pdf_path: Path
) -> List[Image]:
    """Downloads a PDF and converts it to a list of images."""
    try:
        storage_client.download_file(file_id, local_pdf_path)
    except Exception as e:
        raise TransientError(f"API error during download: {e}") from e

    try:
        logging.info(f"Converting PDF {local_pdf_path.name} to images...")
        pages = convert_from_path(str(local_pdf_path), dpi=get_settings().PDF_DPI)
        if not pages:
            raise PermanentError("PDF conversion resulted in 0 pages.")
        return pages
    except (
        pdf2image_exceptions.PDFPageCountError,
        pdf2image_exceptions.PDFSyntaxError,
    ) as e:
        raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
    except Exception as e:
        raise PermanentError(f"PDF conversion failed: {e}") from e


def _recognize_pages(pages: List[Image]) -> List[str]:
    """Recognizes text from a list of images."""
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
    return recognized_texts


def _create_and_upload_pdf(
    storage_client: StorageClient,
    recognized_texts: List[str],
    result_pdf_path: Path,
    destination_path: str,
):
    """Creates a result PDF and uploads it to storage."""
    create_reflowed_pdf(recognized_texts, result_pdf_path)
    try:
        storage_client.upload_file(
            local_path=result_pdf_path,
            folder_id=destination_path,
            filename=result_pdf_path.name,
        )
    except Exception as e:
        raise TransientError(f"API error during upload: {e}") from e


def _cleanup_local_files(paths: List[Path]):
    """Removes temporary local files."""
    logging.info("Cleaning up local files...")
    for path in paths:
        if os.path.exists(path):
            os.remove(path)


def process_single_file(
    storage_client: StorageClient, file_entry: FileMetadata, destination_path: str
):
    """
    Full processing cycle for a single file with detailed error handling.
    This function orchestrates the download, conversion, recognition, and upload.
    """
    settings = get_settings()
    local_pdf_path = settings.LOCAL_BUF_DIR / file_entry.name
    result_pdf_path = settings.LOCAL_BUF_DIR / f"recognized_{file_entry.name}"

    try:
        # 1. Download and Convert
        pages = _download_and_convert(storage_client, file_entry.id, local_pdf_path)

        # 2. Recognize Text
        recognized_texts = _recognize_pages(pages)

        # 3. Create and Upload PDF
        _create_and_upload_pdf(
            storage_client, recognized_texts, result_pdf_path, destination_path
        )

        # 4. Delete Original File
        try:
            storage_client.delete_file(file_entry.id)
            logging.info(f"Successfully processed and deleted {file_entry.name}")
        except Exception as e:
            logging.warning(
                f"Could not delete original file {file_entry.name} after processing. Error: {e}"
            )

    finally:
        # 5. Clean up local files
        _cleanup_local_files([local_pdf_path, result_pdf_path])
