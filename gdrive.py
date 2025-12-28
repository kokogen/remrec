# gdrive.py
import logging
import json
import io
import os

from storage.base import StorageClient
from typing import List, Any
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from exceptions import PermanentError

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
            if 'client_id' in credentials_data and 'client_secret' in credentials_data:
                creds.client_id = credentials_data['client_id']
                creds.client_secret = credentials_data['client_secret']
            else:
                logging.warning("client_id or client_secret not found in GDRIVE_CREDENTIALS_JSON. Using existing from token_json if available.")


            self.service = build("drive", "v3", credentials=creds)
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

        self.folder_ids_cache[current_path] = folder_id
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

    def verify_folder_exists(self, folder_path: str):
        """
        Verifies if a folder with a given ID exists and is actually a folder.
        The `folder_path` parameter is treated as a folder ID for Google Drive.
        
        Raises:
            PermanentError: If the ID does not exist, or if the item is not a folder.
        """
        try:
            file = self.service.files().get(fileId=folder_path, fields='id, mimeType').execute()
            if file.get('mimeType') == 'application/vnd.google-apps.folder':
                logging.info(f"Google Drive folder with ID '{folder_path}' exists and is a folder.")
                return folder_path
            else:
                raise PermanentError(f"Google Drive ID '{folder_path}' exists but is not a folder.")
        except HttpError as e:
            if e.resp.status == 404:
                raise PermanentError(f"Google Drive folder with ID '{folder_path}' not found. Please check your configuration.")
            else:
                logging.error(f"Failed to verify Google Drive folder ID '{folder_path}': {e}")
                raise PermanentError(f"API error while verifying folder ID '{folder_path}': {e}")

    def create_folder_if_not_exists(self, folder_path: str):
        pass