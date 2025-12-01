# dbox.py
import dropbox
from dropbox.files import WriteMode
from dropbox.exceptions import ApiError
import logging


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
        """Returns a list of files in the specified Dropbox directory."""
        try:
            logging.info(f"Listing files in Dropbox path: '{path}'")
            return self.dbx.files_list_folder(path).entries
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
        """Uploads a local file to Dropbox."""
        with open(local_path, "rb") as f:
            try:
                logging.info(f"Uploading {local_path} to {dropbox_path}...")
                self.dbx.files_upload(
                    f.read(), dropbox_path, mode=WriteMode("overwrite")
                )
            except ApiError as e:
                logging.error(f"Failed to upload file to '{dropbox_path}': {e}")
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
