# main.py
import logging
import time
from typing import Optional, Tuple

from .config import get_settings
from .dbox import DropboxClient
from .gdrive import GoogleDriveClient
from .storage.base import StorageClient
from .exceptions import PermanentError, TransientError
from .processing import process_single_file


def setup_logging():
    """Configures logging to file and console explicitly."""
    settings = get_settings()
    log_level_name = settings.LOG_LEVEL.upper()

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_name)

    # Clear any existing handlers to prevent duplicate logs on re-runs or implicit configs
    if root_logger.handlers:
        for handler in root_logger.handlers:
            root_logger.removeHandler(handler)

    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

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
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


def _init_dropbox_client(settings) -> Optional[DropboxClient]:
    """
    Initializes the Dropbox client by trying environment variables and then a token file.
    """
    storage_client = None
    # 1. Try to use the token from the environment variable (primary for production)
    if settings.DROPBOX_REFRESH_TOKEN_ENV:
        try:
            logging.info(
                "Attempting to connect to Dropbox using token from environment variable..."
            )
            storage_client = DropboxClient(
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET,
                refresh_token=settings.DROPBOX_REFRESH_TOKEN_ENV,
            )
        except Exception:
            logging.warning(
                "Failed to connect using token from environment variable. It might be invalid or expired."
            )
            storage_client = None

    # 2. If the first attempt failed or was skipped, try the token from the file (fallback for local dev)
    if storage_client is None and settings.DROPBOX_REFRESH_TOKEN_FILE:
        try:
            logging.info(
                "Attempting to connect to Dropbox using token from '.dropbox.token' file..."
            )
            storage_client = DropboxClient(
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET,
                refresh_token=settings.DROPBOX_REFRESH_TOKEN_FILE,
            )
        except Exception as e:
            logging.error(
                f"Failed to connect using token from file. Error: {e}", exc_info=True
            )
            storage_client = None

    return storage_client


def _init_gdrive_client(settings) -> Optional[GoogleDriveClient]:
    """Initializes and returns a GoogleDriveClient."""
    try:
        storage_client = GoogleDriveClient(
            credentials_json=settings.GDRIVE_CREDENTIALS_JSON,
            token_json=settings.GDRIVE_TOKEN_JSON,
        )
        return storage_client
    except Exception as e:
        logging.error(
            f"Failed to initialize Google Drive client. Error: {e}", exc_info=True
        )
        return None


def initialize_storage_client(
    settings,
) -> Tuple[Optional[StorageClient], Optional[str], Optional[str], Optional[str]]:
    """
    Initializes and returns the appropriate storage client based on settings.

    Returns a tuple of (storage_client, source_path, dest_path, failed_path).
    """
    storage_client: Optional[StorageClient] = None
    source_path, dest_path, failed_path = None, None, None

    if settings.STORAGE_PROVIDER == "dropbox":
        logging.info("Using Dropbox storage provider.")
        source_path = settings.DROPBOX_SOURCE_DIR
        dest_path = settings.DROPBOX_DEST_DIR
        failed_path = settings.DROPBOX_FAILED_DIR
        storage_client = _init_dropbox_client(settings)

    elif settings.STORAGE_PROVIDER == "gdrive":
        logging.info("Using Google Drive storage provider.")
        source_path = settings.GDRIVE_SOURCE_FOLDER_ID
        dest_path = settings.GDRIVE_DEST_FOLDER_ID
        failed_path = settings.GDRIVE_FAILED_FOLDER_ID
        storage_client = _init_gdrive_client(settings)

    else:
        logging.critical(f"Unknown STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")

    return storage_client, source_path, dest_path, failed_path


def main_workflow():
    logging.info("Starting workflow...")
    settings = get_settings()

    storage_client, source_path, dest_path, failed_path = initialize_storage_client(
        settings
    )

    # 3. If client initialization failed, exit the workflow for this run.
    if storage_client is None:
        logging.critical(
            f"Could not establish a connection to {settings.STORAGE_PROVIDER}."
        )
        return

    # Check necessary folders exist
    try:
        for path in [source_path, dest_path, failed_path]:
            if path:
                storage_client.verify_folder_exists(path)
    except Exception as e: # Catch any error during folder verification
        logging.critical(f"A configured folder for {settings.STORAGE_PROVIDER} does not exist or is inaccessible. Aborting workflow. Error: {e}")
        return # Exit main_workflow if a configured folder is missing or inaccessible

    files_to_process = storage_client.list_files(source_path)
    if not files_to_process:
        logging.info("No new files to process.")
        return

    logging.info(f"Found {len(files_to_process)} files to process.")
    for entry in files_to_process:
        # A simple check for PDF files based on name
        if entry.name.lower().endswith(".pdf"):
            logging.info(f"--- Processing file: {entry.name} ---")
            start_time = time.monotonic()
            try:
                process_single_file(storage_client, entry)
                duration = time.monotonic() - start_time
                logging.info(
                    f"Finished processing {entry.name}. Took {duration:.2f} seconds."
                )

            except PermanentError as e:
                duration = time.monotonic() - start_time
                logging.error(
                    f"PERMANENT ERROR processing file {entry.name} after {duration:.2f} seconds. Moving to quarantine. Error: {e}",
                    exc_info=True,
                )
                try:
                    from_path = f"{source_path}/{entry.name}"
                    quarantine_path = f"{failed_path}/{entry.name}"
                    storage_client.move_file(from_path, quarantine_path)
                    logging.warning(
                        f"Moved failed file {entry.name} to quarantine folder."
                    )
                except Exception as move_e:
                    logging.critical(
                        f"CRITICAL: Could not move failed file {entry.name} to quarantine. Error: {move_e}",
                        exc_info=True,
                    )

            except TransientError as e:
                duration = time.monotonic() - start_time
                logging.warning(
                    f"TRANSIENT ERROR processing file {entry.name} after {duration:.2f} seconds. Will retry on next run. Error: {e}",
                    exc_info=True,
                )

            except Exception as e:
                duration = time.monotonic() - start_time
                logging.critical(
                    f"UNHANDLED CRITICAL ERROR processing file {entry.name} after {duration:.2f} seconds. Moving to quarantine as a precaution. Error: {e}",
                    exc_info=True,
                )
                try:
                    from_path = f"{source_path}/{entry.name}"
                    quarantine_path = f"{failed_path}/{entry.name}"
                    storage_client.move_file(from_path, quarantine_path)
                    logging.warning(
                        f"Moved failed file {entry.name} to quarantine folder as a precaution."
                    )
                except Exception as move_e:
                    logging.error(
                        f"CRITICAL: Could not move unhandled error file {entry.name} to quarantine. Error: {move_e}",
                        exc_info=True,
                    )
        else:
            logging.warning(f"Skipping non-PDF or folder entry: {entry.name}")


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Process reMarkable OCR files from Dropbox."
    )
    parser.add_argument(
        "--run-once", action="store_true", help="Run the workflow once and then exit."
    )
    args = parser.parse_args()

    setup_logging()

    if args.run_once:
        logging.info("Starting application in single-run mode.")
        try:
            main_workflow()
        except Exception as e:
            logging.critical(
                f"An unexpected error occurred during the single run: {e}",
                exc_info=True,
            )
        logging.info("Single run finished.")
    else:
        logging.info(
            f"Starting application in infinite loop mode. Sleep interval: {get_settings().LOOP_SLEEP_SECONDS} seconds."
        )
        while True:
            try:
                main_workflow()
            except Exception as e:
                # This provides a top-level catch to prevent the entire loop from crashing.
                logging.critical(
                    f"An unexpected error occurred in the main loop: {e}", exc_info=True
                )

            logging.info(
                f"Workflow run finished. Sleeping for {get_settings().LOOP_SLEEP_SECONDS} seconds."
            )
            time.sleep(get_settings().LOOP_SLEEP_SECONDS)


if __name__ == "__main__":
    main()