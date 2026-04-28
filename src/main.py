# main.py
import logging
import logging.handlers
import time
from enum import Enum
from typing import Optional, Tuple

from .config import get_settings
from .dbox import DropboxClient
from .gdrive import GoogleDriveClient
from .storage.base import StorageClient
from .exceptions import PermanentError, StorageAuthError, StorageError, TransientError
from .processing import process_single_file


class WorkflowStatus(Enum):
    SUCCESS = "success"
    CONFIGURATION_ERROR = "configuration_error"
    TRANSIENT_ERROR = "transient_error"
    PERMANENT_ERROR = "permanent_error"
    UNHANDLED_ERROR = "unhandled_error"

    @property
    def is_success(self) -> bool:
        return self is WorkflowStatus.SUCCESS


def setup_logging():
    """
    Configures logging to file and console explicitly.
    Sets up timed rotating log files.
    """
    settings = get_settings()
    log_level_name = settings.LOG_LEVEL.upper()

    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level_name)

    # Clear any existing handlers to prevent duplicate logs
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

    # Add TimedRotatingFileHandler
    log_dir = settings.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir / "remrec.log"

    try:
        # Rotate logs at midnight, keep 30 days of backups
        file_handler = logging.handlers.TimedRotatingFileHandler(
            log_file_path, when="midnight", interval=1, backupCount=30
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except IOError as e:
        root_logger.error(f"Failed to set up file logging to {log_file_path}: {e}")

    # Reducing "noise" from third-party libraries
    logging.getLogger("dropbox").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)


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
        source_path = settings.SRC_FOLDER
        dest_path = settings.DST_FOLDER
        failed_path = settings.FAILED_FOLDER
        try:
            storage_client = DropboxClient(
                app_key=settings.DROPBOX_APP_KEY,
                app_secret=settings.DROPBOX_APP_SECRET,
                refresh_token=settings.DROPBOX_REFRESH_TOKEN,
            )
            logging.info("Dropbox client initialized successfully.")
        except StorageAuthError as e:
            logging.error(
                f"Dropbox authentication failed. Please check your token and app credentials. Error: {e}"
            )
            storage_client = None
        except StorageError as e:
            logging.error(
                f"Failed to initialize Dropbox client due to a storage error: {e}",
                exc_info=True,
            )
            storage_client = None

    elif settings.STORAGE_PROVIDER == "gdrive":
        logging.info("Using Google Drive storage provider.")
        source_path = settings.SRC_FOLDER
        dest_path = settings.DST_FOLDER
        failed_path = settings.FAILED_FOLDER
        storage_client = _init_gdrive_client(settings)

    else:
        logging.critical(f"Unknown STORAGE_PROVIDER: {settings.STORAGE_PROVIDER}")

    return storage_client, source_path, dest_path, failed_path


def _quarantine_file(
    storage_client: StorageClient, file_id: str, file_name: str, failed_folder_id: str
):
    """Moves a file to the quarantine folder and logs the outcome."""
    try:
        storage_client.move_file(file_id, failed_folder_id)
        logging.warning(
            f"Moved failed file {file_name} to quarantine folder {failed_folder_id}."
        )
    except Exception as move_e:
        logging.critical(
            f"CRITICAL: Could not move failed file {file_name} to quarantine. Error: {move_e}",
            exc_info=True,
        )


def main_workflow() -> WorkflowStatus:
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
        return WorkflowStatus.CONFIGURATION_ERROR

    # Check necessary folders exist
    try:
        for path in [source_path, dest_path, failed_path]:
            # An empty string is a valid path for Dropbox (root), so we check for None
            if path is not None:
                storage_client.verify_folder_exists(path)
    except Exception as e:  # Catch any error during folder verification
        logging.critical(
            f"A configured folder for {settings.STORAGE_PROVIDER} does not exist or is inaccessible. Aborting workflow. Error: {e}"
        )
        return WorkflowStatus.CONFIGURATION_ERROR

    files_to_process = storage_client.list_files(source_path)
    if not files_to_process:
        logging.info("No new files to process.")
        return WorkflowStatus.SUCCESS

    logging.info(f"Found {len(files_to_process)} files to process.")
    workflow_status = WorkflowStatus.SUCCESS
    for entry in files_to_process:
        # A simple check for PDF files based on name
        if entry.name.lower().endswith(".pdf"):
            logging.info(f"--- Processing file: {entry.name} ---")
            start_time = time.monotonic()
            try:
                process_single_file(storage_client, entry, dest_path)
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
                _quarantine_file(storage_client, entry.id, entry.name, failed_path)
                workflow_status = WorkflowStatus.PERMANENT_ERROR

            except TransientError as e:
                duration = time.monotonic() - start_time
                logging.warning(
                    f"TRANSIENT ERROR processing file {entry.name} after {duration:.2f} seconds. Will retry on next run. Error: {e}",
                    exc_info=True,
                )
                workflow_status = WorkflowStatus.TRANSIENT_ERROR

            except Exception as e:
                duration = time.monotonic() - start_time
                logging.critical(
                    f"UNHANDLED CRITICAL ERROR processing file {entry.name} after {duration:.2f} seconds. Moving to quarantine as a precaution. Error: {e}",
                    exc_info=True,
                )
                _quarantine_file(storage_client, entry.id, entry.name, failed_path)
                workflow_status = WorkflowStatus.UNHANDLED_ERROR
        else:
            logging.warning(f"Skipping non-PDF or folder entry: {entry.name}")
    return workflow_status


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
            workflow_status = main_workflow()
        except Exception as e:
            logging.critical(
                f"An unexpected error occurred during the single run: {e}",
                exc_info=True,
            )
            raise SystemExit(1) from e
        logging.info("Single run finished.")
        raise SystemExit(0 if workflow_status.is_success else 1)
    else:
        settings = get_settings()
        logging.info(
            f"Starting application in infinite loop mode. Sleep interval: {settings.LOOP_SLEEP_SECONDS} seconds."
        )
        failure_count = 0
        max_backoff_time = 600  # 10 minutes

        while True:
            try:
                workflow_status = main_workflow()
                if not workflow_status.is_success:
                    raise RuntimeError(
                        f"Workflow finished with {workflow_status.value}"
                    )
                # Reset failure count on success
                if failure_count > 0:
                    logging.info("Workflow successful, resetting failure backoff.")
                    failure_count = 0

                # Normal sleep after successful run
                logging.info(
                    f"Workflow run finished. Sleeping for {settings.LOOP_SLEEP_SECONDS} seconds."
                )
                time.sleep(settings.LOOP_SLEEP_SECONDS)

            except Exception as e:
                # This provides a top-level catch to prevent the entire loop from crashing.
                failure_count += 1
                backoff_time = min(
                    max_backoff_time,
                    settings.LOOP_SLEEP_SECONDS * (2**failure_count),
                )
                logging.critical(
                    f"An unexpected error occurred in the main loop (failure #{failure_count}). "
                    f"Backing off for {backoff_time} seconds. Error: {e}",
                    exc_info=True,
                )
                time.sleep(backoff_time)


if __name__ == "__main__":
    main()
