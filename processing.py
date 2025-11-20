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
    Полный цикл обработки одного файла с детальной обработкой ошибок на каждом шаге.
    При ошибке выбрасывает TransientError или PermanentError.
    """
    local_pdf_path = settings.LOCAL_BUF_DIR / file_entry.name
    result_pdf_path = settings.LOCAL_BUF_DIR / f"recognized_{file_entry.name}"

    try:
        # 1. Скачать файл
        try:
            dbx_client.download_file(file_entry.path_display, local_pdf_path)
        except dropbox.exceptions.ApiError as e:
            # Ошибки Dropbox API могут быть временными
            raise TransientError(f"Dropbox API error during download: {e}") from e

        # 2. Конвертировать PDF в изображения
        try:
            logging.info(f"Converting PDF {file_entry.name} to images...")
            pages = convert_from_path(str(local_pdf_path), dpi=settings.PDF_DPI)
            if not pages:
                raise PermanentError("PDF conversion resulted in 0 pages.")
        except (pdf2image_exceptions.PDFPageCountError, pdf2image_exceptions.PDFSyntaxError) as e:
            # Эти ошибки указывают на битый или некорректный PDF
            raise PermanentError(f"Corrupted or invalid PDF file: {e}") from e
        except Exception as e:
            # Любая другая ошибка конвертации, скорее всего, тоже перманентна для этого файла
            raise PermanentError(f"PDF conversion failed: {e}") from e

        # 3. Распознать текст
        recognized_texts = []
        for i, page in enumerate(pages):
            logging.info(f"Recognizing page {i+1}/{len(pages)}...")
            try:
                img_b64 = image_to_base64(page)
                text = recognize(img_b64)
                recognized_texts.append(f"--- Страница {i+1} ---\n{text}")
            except openai.APIConnectionError as e:
                raise TransientError("Recognition API connection error") from e
            except openai.RateLimitError as e:
                raise TransientError("Recognition API rate limit exceeded") from e
            except openai.BadRequestError as e:
                raise PermanentError(f"Recognition API bad request (invalid image?): {e}") from e
            except openai.AuthenticationError as e:
                raise PermanentError(f"Recognition API authentication error (check API key): {e}") from e

        full_text = "\n\n".join(recognized_texts)

        # 4. Создать итоговый PDF из текста
        txt_to_pdf_line_by_line(full_text, result_pdf_path)

        # 5. Загрузить результат в Dropbox
        try:
            dest_path = f"{settings.DROPBOX_DEST_DIR}/{result_pdf_path.name}"
            dbx_client.upload_file(result_pdf_path, dest_path)
        except dropbox.exceptions.ApiError as e:
            raise TransientError(f"Dropbox API error during upload: {e}") from e

        # 6. Удалить оригинал
        try:
            dbx_client.delete_file(file_entry.path_display)
        except dropbox.exceptions.ApiError as e:
            # Если не удалось удалить, это не критично, но нужно залогировать
            logging.warning(f"Could not delete original file {file_entry.name} after processing. Error: {e}")

        logging.info(f"Successfully processed and deleted {file_entry.name}")

    finally:
        # 7. Очистка локальных файлов в любом случае
        logging.info("Cleaning up local files...")
        if os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)
        if os.path.exists(result_pdf_path):
            os.remove(result_pdf_path)
