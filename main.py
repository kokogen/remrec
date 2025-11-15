# main.py
import logging
import os
import dropbox
from filelock import FileLock, Timeout

import config
from dbox import DropboxClient
from recognition import recognize, image_to_base64

from pdf2image import convert_from_path
from reportlab.lib.pagesizes import LETTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

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
    """Сохраняет текстовый контент в PDF, сохраняя переносы строк."""
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
    Полный цикл обработки одного файла: скачивание, распознавание, создание PDF,
    загрузка результата, архивация оригинала и очистка.
    """
    local_pdf_path = config.LOCAL_BUF_DIR / file_entry.name
    
    try:
        # 1. Скачать файл
        dbx_client.download_file(file_entry.path_display, local_pdf_path)

        # 2. Конвертировать PDF в изображения и распознать
        logging.info(f"Converting PDF {file_entry.name} to images...")
        pages = convert_from_path(str(local_pdf_path), dpi=200)
        
        recognized_texts = []
        for i, page in enumerate(pages):
            logging.info(f"Recognizing page {i+1}/{len(pages)}...")
            img_b64 = image_to_base64(page)
            text = recognize(img_b64)
            recognized_texts.append(f"--- Страница {i+1} ---\n{text}")

        full_text = "\n\n".join(recognized_texts)

        # 3. Создать итоговый PDF из текста
        result_pdf_path = config.LOCAL_BUF_DIR / f"recognized_{file_entry.name}"
        txt_to_pdf_line_by_line(full_text, result_pdf_path)

        # 4. Загрузить результат в Dropbox
        dest_path = f"{config.DROPBOX_DEST_DIR}/{result_pdf_path.name}"
        dbx_client.upload_file(result_pdf_path, dest_path)

        # 5. Переместить оригинал в архив
        archive_path = f"{config.DROPBOX_ARCHIVE_DIR}/{file_entry.name}"
        dbx_client.move_file(file_entry.path_display, archive_path)
        
        logging.info(f"Successfully processed and archived {file_entry.name}")

    finally:
        # 6. Очистка локальных файлов в любом случае
        logging.info("Cleaning up local files...")
        if os.path.exists(local_pdf_path):
            os.remove(local_pdf_path)
        if 'result_pdf_path' in locals() and os.path.exists(result_pdf_path):
            os.remove(result_pdf_path)

def main_workflow():
    """Основной рабочий процесс приложения."""
    logging.info("Starting workflow...")
    
    # Проверка наличия всех необходимых секретов
    required_secrets = ["DROPBOX_REFRESH_TOKEN", "DROPBOX_APP_KEY", "DROPBOX_APP_SECRET", "OPENAI_API_KEY"]
    if not all(getattr(config, secret) for secret in required_secrets):
        logging.error("One or more required environment variables are missing. Exiting.")
        return

    dbx = DropboxClient(config.DROPBOX_APP_KEY, config.DROPBOX_APP_SECRET, config.DROPBOX_REFRESH_TOKEN)
    
    # Проверяем/создаем необходимые папки в Dropbox
    for folder in [config.DROPBOX_SOURCE_DIR, config.DROPBOX_DEST_DIR, config.DROPBOX_ARCHIVE_DIR]:
        dbx.create_folder_if_not_exists(folder)

    files_to_process = dbx.list_files(config.DROPBOX_SOURCE_DIR)
    if not files_to_process:
        logging.info("No new files to process.")
        return

    logging.info(f"Found {len(files_to_process)} files to process.")
    for entry in files_to_process:
        if isinstance(entry, dropbox.files.FileMetadata) and entry.name.lower().endswith('.pdf'):
            logging.info(f"--- Processing file: {entry.name} ---")
            try:
                process_single_file(dbx, entry)
            except Exception as e:
                logging.error(f"FATAL: Failed to process file {entry.name}. Error: {e}", exc_info=True)
        else:
            logging.warning(f"Skipping non-PDF or folder entry: {entry.name}")

if __name__ == "__main__":
    setup_logging()
    
    lock = FileLock(config.LOCK_FILE_PATH)
    try:
        # Пытаемся захватить "замок". Если он занят, выходим через 5 секунд.
        with lock.acquire(timeout=5):
            logging.info("Lock acquired. Starting application.")
            main_workflow()
            logging.info("Application finished. Releasing lock.")
        
    except Timeout:
        logging.warning("Another instance is already running. Exiting.")
    except Exception as e:
        logging.critical(f"An unexpected error occurred in the main application block: {e}", exc_info=True)
