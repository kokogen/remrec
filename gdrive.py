# gdrive.py
import logging
import json
import io
import os

from storage.base import StorageClient
from typing import List, Any
from config import get_settings
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build, Resource
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from googleapiclient.errors import HttpError
from exceptions import PermanentError


class GoogleDriveClient(StorageClient):
    """
    Client for interacting with the Google Drive API, implementing the StorageClient interface.
    """

    def __init__(self, credentials_json: str, token_json: str):
        try:
            creds_info = json.loads(credentials_json)
            token_info = json.loads(token_json)

            creds = Credentials.from_authorized_user_info(token_info)

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # The google-auth-library will automatically refresh the token
                    logging.info("Google Drive credentials expired, attempting to refresh...")
                else:
                    raise ConnectionError(
                        "Failed to authenticate with Google Drive. "
                        "Please re-run the authentication script."
                    )
            
            self.service: Resource = build('drive', 'v3', credentials=creds)
            self.folder_ids_cache = {}
            logging.info("Google Drive client initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Google Drive client. Error: {e}")
            raise

    def _get_folder_id_by_name(self, name: str, parent_id: str = "root") -> str | None:
        """
        Retrieves the ID of a folder by its name within a parent folder.
        """
        query = (
            f"name='{name}' and mimeType='application/vnd.google-apps.folder' and "
            f"'{parent_id}' in parents and trashed=false"
        )
        try:
            response = self.service.files().list(q=query, fields="files(id)").execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as e:
            logging.error(f"Failed to search for folder '{name}': {e}")
            return None

    def ensure_folder_path_exists(self, folder_path: str, parent_id: str = "root") -> str:
        """
        Recursively finds or creates a folder path and returns the final folder's ID.
        Caches folder IDs to avoid redundant lookups.
        """
        if folder_path in self.folder_ids_cache:
            return self.folder_ids_cache[folder_path]

        parts = folder_path.strip("/").split("/")
        current_parent_id = parent_id
        
        for i, part in enumerate(parts):
            current_path = "/".join(parts[:i+1])
            if current_path in self.folder_ids_cache:
                current_parent_id = self.folder_ids_cache[current_path]
                continue

            folder_id = self._get_folder_id_by_name(part, current_parent_id)
            if not folder_id:
                folder_metadata = {
                    "name": part,
                    "mimeType": "application/vnd.google-apps.folder",
                    "parents": [current_parent_id],
                }
                try:
                    folder = self.service.files().create(body=folder_metadata, fields="id").execute()
                    folder_id = folder.get("id")
                    logging.info(f"Created folder '{part}' with ID: {folder_id}")
                except HttpError as e:
                    logging.error(f"Failed to create folder '{part}': {e}")
                    raise PermanentError(f"Could not create folder '{part}' in Google Drive.")
            
            self.folder_ids_cache[current_path] = folder_id
            current_parent_id = folder_id

        self.folder_ids_cache[folder_path] = current_parent_id
        return current_parent_id

    def _find_file_id_by_name(self, filename: str, folder_id: str) -> str | None:
        """
        Finds a file's ID by its name in a specific folder.
        """
        try:
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            response = self.service.files().list(q=query, fields="files(id)").execute()
            files = response.get("files", [])
            return files[0]["id"] if files else None
        except HttpError as e:
            logging.error(f"Error finding file '{filename}': {e}")
            return None

    def list_files(self, folder_id: str) -> List[Any]:
        """
        Lists all files in a given Google Drive folder ID.
        """
        self.verify_folder_id_exists(folder_id)
        try:
            logging.info(f"Listing files in Google Drive folder ID: '{folder_id}'")
            response = self.service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name)"
            ).execute()
            return response.get("files", [])
        except Exception as e:
            logging.error(f"Failed to list files in Google Drive folder ID '{folder_id}': {e}")
            return []

    def download_file(self, file_path: str, local_path: str):
        """
        Downloads a file from Google Drive to the local filesystem.
        """
        folder_path, filename = os.path.split(file_path)
        folder_id = self.ensure_folder_path_exists(folder_path) # Ensure folder exists and get its ID
        file_id = self._find_file_id_by_name(filename, folder_id)

        if not file_id:
            raise FileNotFoundError(f"File '{filename}' not found in '{folder_path}'.")

        try:
            logging.info(f"Downloading {file_path} to {local_path}...")
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(str(local_path), "wb")
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
        except HttpError as e:
            logging.error(f"Failed to download file '{file_path}': {e}")
            raise

    def upload_file(self, local_path: str, remote_path: str):
        """
        Uploads a local file to a specified path in Google Drive.
        """
        folder_path, filename = os.path.split(remote_path)
        folder_id = self.ensure_folder_path_exists(folder_path) # Ensure folder exists and get its ID
        
        # Check if a file with the same name already exists to avoid duplicates
        existing_file_id = self._find_file_id_by_name(filename, folder_id)
        if existing_file_id:
            logging.info(f"File '{filename}' already exists. Deleting before upload.")
            self.delete_file(remote_path) # Use the path-based delete

        try:
            file_metadata = {"name": filename, "parents": [folder_id]}
            media = MediaFileUpload(str(local_path), resumable=True)
            
            logging.info(f"Uploading {local_path} to {remote_path}...")
            self.service.files().create(
                body=file_metadata, media_body=media, fields="id"
            ).execute()
        except HttpError as e:
            logging.error(f"Failed to upload file to '{remote_path}': {e}")
            raise

    def delete_file(self, file_path: str):
        """
        Deletes a file from Google Drive by its full path.
        """
        folder_path, filename = os.path.split(file_path)
        folder_id = self.ensure_folder_path_exists(folder_path) # Ensure folder exists and get its ID
        file_id = self._find_file_id_by_name(filename, folder_id)

        if not file_id:
            logging.warning(f"File '{filename}' not found in '{folder_path}'. Nothing to delete.")
            return

        try:
            logging.info(f"Deleting {file_path}...")
            self.service.files().delete(fileId=file_id).execute()
        except HttpError as e:
            logging.error(f"Failed to delete file '{file_path}': {e}")
            raise

    def move_file(self, from_path: str, to_path: str):
        """
        Moves a file to a different folder in Google Drive.
        """
        from_folder_path, from_filename = os.path.split(from_path)
        to_folder_path, to_filename = os.path.split(to_path)

        from_folder_id = self.ensure_folder_path_exists(from_folder_path)
        to_folder_id = self.ensure_folder_path_exists(to_folder_path)
        
        file_id = self._find_file_id_by_name(from_filename, from_folder_id)

        if not file_id:
            raise FileNotFoundError(f"Source file '{from_filename}' not found in '{from_folder_path}'.")

        try:
            logging.info(f"Moving {from_path} to {to_path}...")
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            
            self.service.files().update(
                fileId=file_id,
                addParents=to_folder_id,
                removeParents=previous_parents,
                body={"name": to_filename},
                fields="id, parents",
            ).execute()
        except HttpError as e:
            logging.error(f"Failed to move file from '{from_path}' to '{to_path}': {e}")
            raise

    def verify_folder_id_exists(self, folder_id: str) -> str:
        """
        Verifies that the provided folder_id exists and refers to an actual Google Drive folder.
        If the folder does not exist or is not a folder, a PermanentError is raised.

        :param folder_id: The ID of the Google Drive folder to verify.
        :return: The verified folder_id.
        :raises PermanentError: If the folder does not exist or is not a folder.
        """
        try:
            # Attempt to get metadata for the given folder_id
            file = self.service.files().get(fileId=folder_id, fields='id, name, mimeType').execute()

            if file and file.get('mimeType') == 'application/vnd.google-apps.folder':
                logging.info(f"Google Drive folder '{file.get('name')}' with ID '{folder_id}' verified.")
                return folder_id
            else:
                raise PermanentError(f"Google Drive ID '{folder_id}' exists but is not a folder.")
        except HttpError as e:
            if e.resp.status == 404:
                raise PermanentError(f"Google Drive folder with ID '{folder_id}' not found. Please check your configuration.")
            else:
                logging.error(f"Failed to verify Google Drive folder ID '{folder_id}': {e}")
                raise

    def create_folder_if_not_exists(self, folder_path: str):
        pass