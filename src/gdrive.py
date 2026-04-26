# gdrive.py
import logging
import json
import io

from .storage.base import StorageClient
from .storage.dto import FileMetadata  # Custom DTO
from typing import List
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from .exceptions import (
    StorageAuthError,
    StorageNotFoundError,
    StoragePermanentError,
    StorageTransientError,
)


def _raise_storage_error(action: str, error: HttpError):
    status = getattr(error.resp, "status", None)
    if status == 404:
        raise StorageNotFoundError(
            f"Google Drive resource not found during {action}"
        ) from error
    if status in {401, 403}:
        raise StorageAuthError(
            f"Google Drive authentication or authorization failed during {action}"
        ) from error
    if status in {408, 409, 429} or (status is not None and status >= 500):
        raise StorageTransientError(
            f"Google Drive transient status {status} during {action}"
        ) from error
    raise StoragePermanentError(
        f"Google Drive permanent status {status} during {action}: {error}"
    ) from error


class GoogleDriveClient(StorageClient):
    """
    Client for interacting with the Google Drive API, implementing the StorageClient interface.
    """

    def __init__(self, credentials_json: str, token_json: str):
        try:
            token_info = json.loads(token_json)

            # The credentials_json can come from a file or environment variable.
            # It should contain the client_id, client_secret, and redirect_uris.
            credentials_data = json.loads(credentials_json)

            creds = Credentials.from_authorized_user_info(info=token_info)

            # Ensure that the client_id and client_secret from credentials_json are used
            # This is important if creds was generated without these initially or if they need to be updated
            if "client_id" in credentials_data and "client_secret" in credentials_data:
                creds.client_id = credentials_data["client_id"]
                creds.client_secret = credentials_data["client_secret"]
            else:
                logging.warning(
                    "client_id or client_secret not found in GDRIVE_CREDENTIALS_JSON. Using existing from token_json if available."
                )

            self.service = build("drive", "v3", credentials=creds)
            self.folder_ids_cache = {}  # Initialize cache
            logging.info("Google Drive client initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Google Drive client. Error: {e}")
            raise

    def _find_file_id_by_name(self, filename: str, folder_id: str) -> str | None:
        """
        Finds a file's ID by its name in a specific folder.
        """
        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            response = (
                self.service.files().list(q=query, fields="files(id, name)").execute()
            )
            files = response.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as e:
            logging.error(f"Error finding file '{filename}': {e}")
            _raise_storage_error("find file by name", e)

    def list_files(self, folder_id: str) -> List[FileMetadata]:
        """
        Lists all files in a given Google Drive folder ID.
        """
        self.verify_folder_exists(folder_id)
        try:
            logging.info(f"Listing files in Google Drive folder ID: '{folder_id}'")
            response = (
                self.service.files()
                .list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    fields="files(id, name)",
                )
                .execute()
            )
            files = response.get("files", [])
            # Convert the raw API response to a list of FileMetadata DTOs
            return [
                FileMetadata(
                    id=item["id"],
                    name=item["name"],
                    path=item["id"],  # For GDrive, ID is the most reliable path
                    folder_id=folder_id,
                )
                for item in files
            ]
        except HttpError as e:
            logging.error(
                f"Failed to list files in Google Drive folder ID '{folder_id}': {e}"
            )
            _raise_storage_error("list files", e)

    def download_file(self, file_id: str, local_path: str):
        """
        Downloads a file from Google Drive to the local filesystem using its file ID.
        """
        try:
            logging.info(f"Downloading file with ID '{file_id}' to {local_path}...")
            request = self.service.files().get_media(fileId=file_id)
            with io.FileIO(str(local_path), "wb") as fh:
                downloader = MediaIoBaseDownload(fh, request)
                done = False
                while not done:
                    status, done = downloader.next_chunk()
        except HttpError as e:
            logging.error(f"Failed to download file with ID '{file_id}': {e}")
            _raise_storage_error("download file", e)

    def upload_file(self, local_path: str, folder_id: str, filename: str):
        """
        Uploads a local file to a specified folder in Google Drive.
        If a file with the same name exists, it updates the file content.
        Otherwise, it creates a new file.
        """
        try:
            # We assume folder_id is a valid ID and exists, as verified in main_workflow.
            existing_file_id = self._find_file_id_by_name(filename, folder_id)
            media = MediaFileUpload(str(local_path), resumable=True)

            if existing_file_id:
                # File exists, so update it
                logging.info(
                    f"File '{filename}' already exists with ID {existing_file_id}. Updating content..."
                )
                self.service.files().update(
                    fileId=existing_file_id, media_body=media
                ).execute()
                logging.info(
                    f"Successfully updated {filename} in folder ID: {folder_id}."
                )
            else:
                # File does not exist, so create it
                file_metadata = {"name": filename, "parents": [folder_id]}
                logging.info(
                    f"Uploading new file {local_path} to folder ID {folder_id} with name {filename}..."
                )
                self.service.files().create(
                    body=file_metadata, media_body=media, fields="id"
                ).execute()
                logging.info(
                    f"Successfully uploaded {filename} to folder ID: {folder_id}."
                )

        except HttpError as e:
            logging.error(
                f"Failed to upload/update file to folder ID '{folder_id}': {e}"
            )
            _raise_storage_error("upload file", e)

    def delete_file(self, file_id: str):
        """
        Deletes a file from Google Drive by its file ID.
        """
        try:
            logging.info(f"Deleting file with ID '{file_id}'...")
            self.service.files().delete(fileId=file_id).execute()
        except HttpError as e:
            if e.resp.status == 404:
                logging.warning(
                    f"File with ID '{file_id}' not found. Nothing to delete."
                )
                return
            else:
                logging.error(f"Failed to delete file with ID '{file_id}': {e}")
                _raise_storage_error("delete file", e)

    def move_file(self, file_id: str, to_folder_id: str):
        """
        Moves a file to a different folder in Google Drive.
        """
        try:
            logging.info(f"Moving file ID '{file_id}' to folder ID '{to_folder_id}'...")
            # Retrieve the existing parents to remove them
            file = (
                self.service.files()
                .get(fileId=file_id, fields="parents, name")
                .execute()
            )
            previous_parents = ",".join(file.get("parents"))
            current_filename = file.get("name")

            # Move the file by updating its parents
            self.service.files().update(
                fileId=file_id,
                addParents=to_folder_id,
                removeParents=previous_parents,
                body={"name": current_filename},  # Keep the original filename
                fields="id, parents",
            ).execute()
            logging.info(
                f"Successfully moved file ID '{file_id}' to folder ID '{to_folder_id}'."
            )
        except HttpError as e:
            logging.error(
                f"Failed to move file ID '{file_id}' to folder '{to_folder_id}': {e}"
            )
            _raise_storage_error("move file", e)

    def verify_folder_exists(self, folder_id: str):
        """
        Verifies if a folder with a given ID exists and is actually a folder.

        Raises:
            StoragePermanentError: If the ID does not exist, or if the item is not a folder.
        """
        try:
            file = (
                self.service.files()
                .get(fileId=folder_id, fields="id, mimeType")
                .execute()
            )
            if file.get("mimeType") == "application/vnd.google-apps.folder":
                logging.info(
                    f"Google Drive folder with ID '{folder_id}' exists and is a folder."
                )
                return
            else:
                raise StoragePermanentError(
                    f"Google Drive ID '{folder_id}' exists but is not a folder."
                )
        except HttpError as e:
            if e.resp.status == 404:
                raise StorageNotFoundError(
                    f"Google Drive folder with ID '{folder_id}' not found. Please check your configuration."
                ) from e
            else:
                logging.error(
                    f"Failed to verify Google Drive folder ID '{folder_id}': {e}"
                )
                _raise_storage_error("verify folder", e)
