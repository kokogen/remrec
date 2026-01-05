# dbox.py
import dropbox
from dropbox.files import WriteMode, CommitInfo, FileMetadata as DropboxFileMetadata
from dropbox.exceptions import ApiError
import logging
import os
from .config import get_settings
from .storage.base import StorageClient
from .storage.dto import FileMetadata  # Our custom DTO


class DropboxClient(StorageClient):
    """
    Client for interacting with the Dropbox API, implementing the StorageClient interface.
    """

    def __init__(self, app_key, app_secret, refresh_token):
        try:
            self.dbx = dropbox.Dropbox(
                app_key=app_key,
                app_secret=app_secret,
                oauth2_refresh_token=refresh_token,
            )
            # Verify successful authentication by requesting current user info
            self.dbx.users_get_current_account()
            logging.info("Dropbox client initialized successfully.")
        except Exception as e:
            logging.error(
                f"Failed to initialize Dropbox client. Check your credentials. Error: {e}"
            )
            raise

    def list_files(self, folder_id: str):
        """
        Returns a list of all files in the specified Dropbox directory,
        handling pagination automatically.
        """
        try:
            logging.info(f"Listing files in Dropbox path: '{folder_id}'")
            result = self.dbx.files_list_folder(folder_id)  # Non-recursive
            all_entries = result.entries
            while result.has_more:
                logging.info("Found more files, continuing listing...")
                result = self.dbx.files_list_folder_continue(result.cursor)
                all_entries.extend(result.entries)

            # Convert Dropbox metadata to our standardized DTO
            file_dtos = []
            for entry in all_entries:
                if isinstance(entry, DropboxFileMetadata):
                    file_dtos.append(
                        FileMetadata(
                            id=entry.path_display,
                            name=entry.name,
                            path=entry.path_display,
                            folder_id=folder_id,
                        )
                    )
            return file_dtos
        except ApiError as e:
            logging.error(f"Failed to list files in Dropbox path '{folder_id}': {e}")
            return []

    def download_file(self, file_id: str, local_path: str):
        """Downloads a file from Dropbox to the local filesystem."""
        try:
            logging.info(f"Downloading {file_id} to {local_path}...")
            self.dbx.files_download_to_file(str(local_path), file_id)
        except ApiError as e:
            logging.error(f"Failed to download file '{file_id}': {e}")
            raise

    def upload_file(self, local_path: str, folder_id: str, filename: str):
        """Uploads a local file to Dropbox using chunked uploading for efficiency."""
        settings = get_settings()
        chunk_size = settings.DROPBOX_UPLOAD_CHUNK_SIZE
        remote_path = f"{folder_id}/{filename}".replace(
            "//", "/"
        )  # Handle root folder case

        file_size = local_path.stat().st_size
        if file_size < chunk_size:
            # If file is smaller than chunk size, use a single upload
            with open(local_path, "rb") as f:
                try:
                    logging.info(
                        f"Uploading {local_path} to {remote_path} (single upload)..."
                    )
                    self.dbx.files_upload(
                        f.read(), remote_path, mode=WriteMode("overwrite")
                    )
                except ApiError as e:
                    logging.error(f"Failed to upload file to '{remote_path}': {e}")
                    raise
        else:
            # Use chunked upload for larger files
            with open(local_path, "rb") as f:
                try:
                    logging.info(
                        f"Starting chunked upload for {local_path} to {remote_path}..."
                    )
                    upload_session_start_result = self.dbx.files_upload_session_start(
                        f.read(chunk_size)
                    )
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell(),
                    )
                    commit_info = CommitInfo(
                        path=remote_path, mode=WriteMode("overwrite")
                    )

                    while f.tell() < file_size:
                        next_chunk = f.read(chunk_size)
                        if (file_size - f.tell()) <= chunk_size:
                            # Last chunk
                            logging.info(f"Uploading final chunk for {remote_path}...")
                            self.dbx.files_upload_session_finish(
                                next_chunk, cursor, commit_info
                            )
                        else:
                            # Middle chunk
                            logging.info(
                                f"Uploading chunk for {remote_path} (offset: {f.tell()})..."
                            )
                            self.dbx.files_upload_session_append_v2(next_chunk, cursor)
                            cursor.offset = f.tell()
                    logging.info(f"Chunked upload completed for {remote_path}.")
                except ApiError as e:
                    logging.error(
                        f"Failed to upload file to '{remote_path}' using chunked upload: {e}"
                    )
                    raise

    def move_file(self, file_id: str, to_folder_id: str):
        """Moves a file within Dropbox."""
        try:
            filename = os.path.basename(file_id)
            to_path = f"{to_folder_id}/{filename}".replace("//", "/")
            logging.info(f"Moving {file_id} to {to_path}...")
            self.dbx.files_move_v2(file_id, to_path)
        except ApiError as e:
            logging.error(f"Failed to move file from '{file_id}' to '{to_path}': {e}")
            raise

    def delete_file(self, file_id: str):
        """Deletes a file or folder in Dropbox."""
        try:
            logging.info(f"Deleting {file_id}...")
            self.dbx.files_delete_v2(file_id)
        except ApiError as e:
            logging.error(f"Failed to delete path '{file_id}': {e}")
            raise

    def verify_folder_exists(self, folder_id: str):
        """
        Verifies if a folder exists.
        Raises an ApiError if the folder does not exist or is inaccessible.
        """
        try:
            # For Dropbox, an empty string signifies the root folder, which always exists.
            if folder_id == "":
                logging.info("Dropbox root folder '' specified, which always exists.")
                return

            self.dbx.files_get_metadata(folder_id)
            logging.info(f"Dropbox folder '{folder_id}' exists.")
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                logging.critical(
                    f"Configured Dropbox folder '{folder_id}' does not exist."
                )
                raise  # Re-raise the error to be handled upstream (e.g., in main.py)
            else:
                logging.error(f"Error accessing Dropbox folder '{folder_id}': {e}")
                raise  # Re-raise for other API errors (e.g., permissions)
