# main.py
import logging
import dropbox
import time
from filelock import FileLock, Timeout

from config import settings
from dbox import DropboxClient
from exceptions import PermanentError, TransientError
from processing import process_single_file

def setup_logging():
    """Configures logging to file and console."""
    # Ensure the log level is correct
    log_level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(settings.LOG_FILE),
            logging.StreamHandler()  # For output to `docker logs`
        ]
    )
    # Reducing "noise" from third-party libraries
    logging.getLogger("dropbox").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def main_workflow():

    logging.info("Starting workflow...")
    
    dbx = DropboxClient(settings.DROPBOX_APP_KEY, settings.DROPBOX_APP_SECRET, settings.DROPBOX_REFRESH_TOKEN)
    
    # Check/create necessary folders in Dropbox
    for folder in [settings.DROPBOX_SOURCE_DIR, settings.DROPBOX_DEST_DIR]:
        # The root folder ("") always exists and doesn't need to be created.
        if folder:
            dbx.create_folder_if_not_exists(folder)

    files_to_process = dbx.list_files(settings.DROPBOX_SOURCE_DIR)
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
                    quarantine_path = f"{settings.DROPBOX_FAILED_DIR}/{entry.name}"
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
                    quarantine_path = f"{settings.DROPBOX_FAILED_DIR}/{entry.name}"
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
        # Standard cron job mode with file lock
        lock = FileLock(settings.LOCK_FILE_PATH)
        try:
            with lock.acquire(timeout=5):
                logging.info("Lock acquired. Starting scheduled application run.")
                main_workflow()
                logging.info("Scheduled run finished. Releasing lock.")
            
        except Timeout:
            logging.warning("Another instance is already running (lock file is busy). Exiting.")
        except Exception as e:
            logging.critical(f"An unexpected error occurred in the main application block: {e}", exc_info=True)
