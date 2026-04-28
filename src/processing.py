# processing.py
import hashlib
import logging
import tempfile
from pdf2image import (
    convert_from_path,
    exceptions as pdf2image_exceptions,
    pdfinfo_from_path,
)
from typing import List
from pathlib import Path
from filelock import FileLock, Timeout

from .config import get_settings
from .storage.base import StorageClient
from .storage.dto import FileMetadata
from .exceptions import PermanentError, StorageError
from .recognition import image_to_base64, recognize
from .pdf_utils import create_reflowed_pdf


def _download_pdf(storage_client: StorageClient, file_id: str, local_pdf_path: Path):
    """Downloads a PDF to local storage."""
    try:
        storage_client.download_file(file_id, local_pdf_path)
    except StorageError:
        raise


def _get_pdf_page_count(local_pdf_path: Path) -> int:
    """Returns the number of pages in a PDF."""
    try:
        pdf_info = pdfinfo_from_path(str(local_pdf_path))
        page_count = int(pdf_info.get("Pages", 0))
        if page_count <= 0:
            raise PermanentError("PDF has no pages.")
        return page_count
    except (
        pdf2image_exceptions.PDFPageCountError,
        pdf2image_exceptions.PDFSyntaxError,
    ) as e:
        raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
    except PermanentError:
        raise
    except Exception as e:
        raise PermanentError(f"Could not read PDF metadata: {e}") from e


def _convert_pdf_page(local_pdf_path: Path, page_number: int):
    """Converts one PDF page to an image."""
    try:
        pages = convert_from_path(
            str(local_pdf_path),
            dpi=get_settings().PDF_DPI,
            first_page=page_number,
            last_page=page_number,
        )
        if len(pages) != 1:
            raise PermanentError(
                f"PDF page {page_number} conversion returned no image."
            )
        return pages[0]
    except (
        pdf2image_exceptions.PDFPageCountError,
        pdf2image_exceptions.PDFSyntaxError,
    ) as e:
        raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
    except PermanentError:
        raise
    except Exception as e:
        raise PermanentError(f"PDF page {page_number} conversion failed: {e}") from e


def _recognize_pdf_pages(local_pdf_path: Path) -> List[str]:
    """Recognizes text from a PDF one page at a time."""
    page_count = _get_pdf_page_count(local_pdf_path)
    logging.info(f"Converting and recognizing {page_count} PDF page(s)...")
    recognized_texts = []
    for page_number in range(1, page_count + 1):
        logging.info(f"Recognizing page {page_number}/{page_count}...")
        page = _convert_pdf_page(local_pdf_path, page_number)
        try:
            img_b64 = image_to_base64(page)
            text = recognize(img_b64)
            recognized_texts.append(text)
        finally:
            page.close()
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
    except StorageError:
        raise


def _file_lock_path(buffer_dir: Path, file_id: str) -> Path:
    """Returns a stable lock path for a provider file ID."""
    lock_digest = hashlib.sha256(file_id.encode("utf-8")).hexdigest()
    return buffer_dir / "locks" / f"{lock_digest}.lock"


def _delete_original_file(storage_client: StorageClient, file_entry: FileMetadata):
    """Deletes the original file after the result is known to exist."""
    try:
        storage_client.delete_file(file_entry.id)
        logging.info(f"Successfully processed and deleted {file_entry.name}")
    except Exception as e:
        logging.warning(
            f"Could not delete original file {file_entry.name} after processing. Error: {e}"
        )


def process_single_file(
    storage_client: StorageClient, file_entry: FileMetadata, destination_path: str
):
    """
    Full processing cycle for a single file with detailed error handling.
    This function orchestrates the download, conversion, recognition, and upload.
    """
    settings = get_settings()
    settings.LOCAL_BUF_DIR.mkdir(parents=True, exist_ok=True)
    lock_path = _file_lock_path(settings.LOCAL_BUF_DIR, file_entry.id)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with FileLock(str(lock_path), timeout=0):
            result_filename = f"recognized_{file_entry.name}"
            if storage_client.file_exists(destination_path, result_filename):
                logging.info(
                    f"Recognized result {result_filename} already exists. "
                    f"Skipping OCR for {file_entry.name}."
                )
                _delete_original_file(storage_client, file_entry)
                return

            with tempfile.TemporaryDirectory(
                prefix="remrec-", dir=settings.LOCAL_BUF_DIR
            ) as temp_dir_name:
                temp_dir = Path(temp_dir_name)
                local_pdf_path = temp_dir / file_entry.name
                result_pdf_path = temp_dir / result_filename

                # 1. Download
                _download_pdf(storage_client, file_entry.id, local_pdf_path)

                # 2. Convert and Recognize Text
                recognized_texts = _recognize_pdf_pages(local_pdf_path)

                # 3. Create and Upload PDF
                _create_and_upload_pdf(
                    storage_client, recognized_texts, result_pdf_path, destination_path
                )

                # 4. Delete Original File
                _delete_original_file(storage_client, file_entry)
    except Timeout:
        logging.warning(
            f"Skipping {file_entry.name}: another worker is already processing it."
        )
