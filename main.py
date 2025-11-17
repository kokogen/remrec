# main.py
import logging
import os
import dropbox
import time # Добавляем импорт
from filelock import FileLock, Timeout

import config
from dbox import DropboxClient
from recognition import recognize, image_to_base64
import openai # Импорт для отлова ошибок API
from pdf2image import convert_from_path, exceptions as pdf2image_exceptions # Импорт для отлова ошибок конвертации
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Определяем кастомные исключения для более точной обработки ошибок
class PermanentError(Exception):
    """Ошибка, которая не исправится повторной попыткой (например, битый файл)."""
    pass

class TransientError(Exception):
    """Временная ошибка (например, сбой сети), которая может исчезнуть при повторной попытке."""
    pass

def setup_logging():
    """Настраивает логирование в файл и в консоль."""
    # Убедимся, что уровень логирования корректен
    log_level_name = config.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()  # Для вывода в `docker logs`
        ]
    )
    # Уменьшаем "шум" от сторонних библиотек
    logging.getLogger("dropbox").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def txt_to_pdf_line_by_line(txt_content, pdf_path):

    if not config.FONT_PATH.exists():
        logging.error(f"Font file not found at {config.FONT_PATH}. Cannot create PDF.")
        raise FileNotFoundError(f"Font file not found: {config.FONT_PATH}")

    pdfmetrics.registerFont(TTFont('DejaVuSans', str(config.FONT_PATH)))

    doc = SimpleDocTemplate(str(pdf_path), pagesize=LETTER)
    style = ParagraphStyle(
        name='LineStyle', fontName='DejaVuSans', fontSize=12, leading=15
    )

    flowables = [Paragraph(line, style) for line in txt_content.split('\n')]
    doc.build(flowables)
    logging.info(f"PDF created at {pdf_path}")

def process_single_file(dbx_client: DropboxClient, file_entry:dropbox.files.FileMetadata):
    """
    Полный цикл обработки одного файла с детальной обработкой ошибок на каждом шаге.
    При ошибке выбрасывает TransientError или PermanentError.
    """
    local_pdf_path = config.LOCAL_BUF_DIR / file_entry.name
    result_pdf_path = config.LOCAL_BUF_DIR / f"recognized_{file_entry.name}"

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
            pages = convert_from_path(str(local_pdf_path), dpi=config.PDF_DPI)
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
                recognized_texts.append(f"--- Страница {i+1} ---{text}")
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
            dest_path = f"{config.DROPBOX_DEST_DIR}/{result_pdf_path.name}"
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

def main_workflow():

    logging.info("Starting workflow...")
    
    # Проверка наличия всех необходимых секретов
    required_secrets = ["DROPBOX_REFRESH_TOKEN", "DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "OPENAI_API_KEY"]
    if not all(getattr(config, secret) for secret in required_secrets):
        logging.error("One or more required environment variables are missing. Exiting.")
        return

    dbx = DropboxClient(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_REFRESH_TOKEN)
    
    # Проверяем/создаем необходимые папки в Dropbox
    for folder in [config.DROPBOX_SOURCE_DIR, config.DROPBOX_DEST_DIR]:
        # Корневая папка ("") всегда существует, ее создавать не нужно.
        if folder:
            dbx.create_folder_if_not_exists(folder)

    files_to_process = dbx.list_files(config.DROPBOX_SOURCE_DIR)
    if not files_to_process:
        logging.info("No new files to process.")
        return

    logging.info(f"Found {len(files_to_process)} files to process.")
    for entry in files_to_process:
        if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith('.pdf'):
            logging.info(f"--- Processing file: {entry.name} ---")
            start_time = time.monotonic()
            try:
                process_single_file(dbx, entry)
                duration = time.monotonic() - start_time
                logging.info(f"Finished processing {entry.name}. Took {duration:.2f} seconds.")
            
            except PermanentError as e:
                duration = time.monotonic() - start_time
                logging.error(f"PERMANENT ERROR processing file {entry.name} after {duration:.2f} seconds. Moving to quarantine. Error: {e}", exc_info=True)
                try:
                    quarantine_path = f"{config.DROPBOX_FAILED_DIR}/{entry.name}"
                    dbx.move_file(entry.path_display, quarantine_path)
                    logging.warning(f"Moved failed file {entry.name} to quarantine folder.")
                except Exception as move_e:
                    logging.critical(f"CRITICAL: Could not move failed file {entry.name} to quarantine. Error: {move_e}", exc_info=True)

            except TransientError as e:
                duration = time.monotonic() - start_time
                logging.warning(f"TRANSIENT ERROR processing file {entry.name} after {duration:.2f} seconds. Will retry on next run. Error: {e}", exc_info=True)

            except Exception as e:
                duration = time.monotonic() - start_time
                logging.critical(f"UNHANDLED CRITICAL ERROR processing file {entry.name} after {duration:.2f} seconds. Moving to quarantine as a precaution. Error: {e}", exc_info=True)
                try:
                    quarantine_path = f"{config.DROPBOX_FAILED_DIR}/{entry.name}"
                    dbx.move_file(entry.path_display, quarantine_path)
                    logging.warning(f"Moved failed file {entry.name} to quarantine folder as a precaution.")
                except Exception as move_e:
                    logging.error(f"CRITICAL: Could not move unhandled error file {entry.name} to quarantine. Error: {move_e}", exc_info=True)
        else:
            logging.warning(f"Skipping non-PDF or folder entry: {entry.name}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Remarkable Recognizer Workflow.")
    parser.add_argument(
        '--run-once',
        action='store_true',
        help='Run the workflow once immediately without cron or file lock.'
    )
    args = parser.parse_args()

    setup_logging()

    if args.run_once:
        logging.info("Executing a single run via --run-once flag.")
        main_workflow()
        logging.info("Single run finished.")
    else:
        # Стандартный режим работы для cron с блокировкой
        lock = FileLock(config.LOCK_FILE_PATH)
        try:
            with lock.acquire(timeout=5):
                logging.info("Lock acquired. Starting scheduled application run.")
                main_workflow()
                logging.info("Scheduled run finished. Releasing lock.")
            
        except Timeout:
            logging.warning("Another instance is already running (lock file is busy). Exiting.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred in the main application block: {e}", exc_info=True)
