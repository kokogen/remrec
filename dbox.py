# dbox.py
import dropbox
from dropbox.files import WriteMode, CommitInfo
from dropbox.exceptions import ApiError
import logging
from config import get_settings

class DropboxClient:
    """
    Client for interacting with the Dropbox API using the official SDK.
    Automatically manages token refreshes.
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

    def list_files(self, path):
        """
        Returns a list of all files in the specified Dropbox directory,
        handling pagination automatically.
        """
        try:
            logging.info(f"Listing files in Dropbox path: '{path}'")
            result = self.dbx.files_list_folder(path)
            all_entries = result.entries
            while result.has_more:
                logging.info("Found more files, continuing listing...")
                result = self.dbx.files_list_folder_continue(result.cursor)
                all_entries.extend(result.entries)
            return all_entries
        except ApiError as e:
            logging.error(f"Failed to list files in Dropbox path '{path}': {e}")
            return []

    def download_file(self, dropbox_path, local_path):
        """Downloads a file from Dropbox to the local filesystem."""
        try:
            logging.info(f"Downloading {dropbox_path} to {local_path}...")
            self.dbx.files_download_to_file(str(local_path), dropbox_path)
        except ApiError as e:
            logging.error(f"Failed to download file '{dropbox_path}': {e}")
            raise

    def upload_file(self, local_path, dropbox_path):
        """Uploads a local file to Dropbox using chunked uploading for efficiency."""
        settings = get_settings()
        chunk_size = settings.DROPBOX_UPLOAD_CHUNK_SIZE

        file_size = local_path.stat().st_size
        if file_size < chunk_size:
            # If file is smaller than chunk size, use a single upload
            with open(local_path, "rb") as f:
                try:
                    logging.info(f"Uploading {local_path} to {dropbox_path} (single upload)...")
                    self.dbx.files_upload(
                        f.read(), dropbox_path, mode=WriteMode("overwrite")
                    )
                except ApiError as e:
                    logging.error(f"Failed to upload file to '{dropbox_path}': {e}")
                    raise
        else:
            # Use chunked upload for larger files
            with open(local_path, "rb") as f:
                try:
                    logging.info(f"Starting chunked upload for {local_path} to {dropbox_path}...")
                    upload_session_start_result = self.dbx.files_upload_session_start(f.read(chunk_size))
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=f.tell()
                    )
                    commit_info = CommitInfo(path=dropbox_path, mode=WriteMode("overwrite"))

                    while f.tell() < file_size:
                        next_chunk = f.read(chunk_size)
                        if (file_size - f.tell()) <= chunk_size:
                            # Last chunk
                            logging.info(f"Uploading final chunk for {dropbox_path}...")
                            self.dbx.files_upload_session_finish(next_chunk, cursor, commit_info)
                        else:
                            # Middle chunk
                            logging.info(f"Uploading chunk for {dropbox_path} (offset: {f.tell()})...")
                            self.dbx.files_upload_session_append_v2(next_chunk, cursor)
                            cursor.offset = f.tell()
                    logging.info(f"Chunked upload completed for {dropbox_path}.")
                except ApiError as e:
                    logging.error(f"Failed to upload file to '{dropbox_path}' using chunked upload: {e}")
                    raise

    def move_file(self, from_path, to_path):
        """Moves a file within Dropbox."""
        try:
            logging.info(f"Moving {from_path} to {to_path}...")
            self.dbx.files_move_v2(from_path, to_path)
        except ApiError as e:
            logging.error(f"Failed to move file from '{from_path}' to '{to_path}': {e}")
            raise

    def delete_file(self, path):
        """Deletes a file or folder in Dropbox."""
        try:
            logging.info(f"Deleting {path}...")
            self.dbx.files_delete_v2(path)
        except ApiError as e:
            logging.error(f"Failed to delete path '{path}': {e}")
            raise

    def create_folder_if_not_exists(self, path):
        """Creates a folder if it does not exist."""
        try:
            self.dbx.files_get_metadata(path)
        except ApiError as e:
            if e.error.is_path() and e.error.get_path().is_not_found():
                logging.info(f"Folder '{path}' not found. Creating...")
                self.dbx.files_create_folder_v2(path)
            else:
                raise

