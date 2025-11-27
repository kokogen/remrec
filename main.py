# main.py
import logging
import dropbox
import time

from config import settings
from dbox import DropboxClient
from exceptions import PermanentError, TransientError
from processing import process_single_file

def setup_logging():
    """Configures logging to file and console explicitly."""
    log_level_name = settings.LOG_LEVEL.upper()
    log_level = getattr(logging, log_level_name, logging.INFO)

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear any existing handlers to prevent duplicate logs on re-runs or implicit configs
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Add StreamHandler (for console output)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    root_logger.addHandler(stream_handler)

    # Add FileHandler
    try:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except IOError as e:
        # Log to console if file logging fails (e.g., permissions)
        root_logger.error(f"Failed to set up file logging to {settings.LOG_FILE}: {e}")

    # Reducing "noise" from third-party libraries
    logging.getLogger("dropbox").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

def main_workflow():
    logging.info("Starting workflow...")
    
    dbx = None
    
    # --- Smart Dropbox Client Initialization ---
    # 1. Try to use the token from the environment variable (primary for production)
    if settings.DROPBOX_REFRESH_TOKEN_ENV:
        try:
            logging.info("Attempting to connect to Dropbox using token from environment variable...")
            dbx = DropboxClient(
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET,
                refresh_token=settings.DROPBOX_REFRESH_TOKEN_ENV
            )
        except Exception:
            logging.warning("Failed to connect using token from environment variable. It might be invalid or expired.")
            dbx = None # Explicitly set to None on failure

    # 2. If the first attempt failed or was skipped, try the token from the file (fallback for local dev)
    if dbx is None and settings.DROPBOX_REFRESH_TOKEN_FILE:
        try:
            logging.info("Attempting to connect to Dropbox using token from '.dropbox.token' file...")
            dbx = DropboxClient(
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET,
                refresh_token=settings.DROPBOX_REFRESH_TOKEN_FILE
            )
        except Exception as e:
            logging.error(f"Failed to connect using token from file. Error: {e}", exc_info=True)
            dbx = None

    # 3. If both attempts failed, exit the workflow for this run.
    if dbx is None:
        logging.critical("Could not establish a connection to Dropbox. Both environment variable and token file methods failed or were not configured.")
        return # Stop the workflow for this cycle

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

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Process reMarkable OCR files from Dropbox.")
    parser.add_argument("--run-once", action="store_true", help="Run the workflow once and then exit.")
    args = parser.parse_args()

    setup_logging()

    if args.run_once:
        logging.info("Starting application in single-run mode.")
        try:
            main_workflow()
        except Exception as e:
            logging.critical(f"An unexpected error occurred during the single run: {e}", exc_info=True)
        logging.info("Single run finished.")
    else:
        logging.info(f"Starting application in infinite loop mode. Sleep interval: {settings.LOOP_SLEEP_SECONDS} seconds.")
        while True:
            try:
                main_workflow()
            except Exception as e:
                # This provides a top-level catch to prevent the entire loop from crashing.
                logging.critical(f"An unexpected error occurred in the main loop: {e}", exc_info=True)
            
            logging.info(f"Workflow run finished. Sleeping for {settings.LOOP_SLEEP_SECONDS} seconds.")
            time.sleep(settings.LOOP_SLEEP_SECONDS)

if __name__ == "__main__":
    main()
