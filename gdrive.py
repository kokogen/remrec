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


class GoogleDriveClient(StorageClient):
    """
    Client for interacting with the Google Drive API, implementing the StorageClient interface.
    """

    def __init__(self):
        settings = get_settings()
        creds = None
        try:
            # The user-provided credentials JSON is parsed
            creds_json = json.loads(settings.GDRIVE_CREDENTIALS_JSON)
            # The user-provided token JSON is parsed
            token_json = json.loads(settings.GDRIVE_TOKEN_JSON)

            creds = Credentials.from_authorized_user_info(token_json, creds_json.get("installed").get("scopes"))

            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    # If the credentials have expired, they can be refreshed.
                    # This will be handled automatically by the google-auth library.
                    logging.info("Google Drive credentials expired, attempting to refresh...")
                else:
                    # If there's no refresh token or credentials are bad, authentication will fail.
                    raise ConnectionError("Failed to authenticate with Google Drive. Please re-run the authentication script.")
            
            self.service: Resource = build('drive', 'v3', credentials=creds)
            logging.info("Google Drive client initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize Google Drive client. Error: {e}")
            raise

    def list_files(self, folder_id: str) -> List[Any]:
        """
        Lists all files in a given Google Drive folder.
        :param folder_id: The ID of the folder to list.
        :return: A list of file metadata objects.
        """
        try:
            logging.info(f"Listing files in Google Drive folder ID: '{folder_id}'")
            files = []
            page_token = None
            while True:
                response = self.service.files().list(
                    q=f"'{folder_id}' in parents and trashed=false",
                    spaces='drive',
                    fields='nextPageToken, files(id, name)',
                    pageToken=page_token
                ).execute()
                files.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            return files
        except Exception as e:
            logging.error(f"Failed to list files in Google Drive folder '{folder_id}': {e}")
            return []

    def download_file(self, file_id: str, local_path: str):
        """
        Downloads a file from Google Drive to the local filesystem.
        :param file_id: The ID of the file to download.
        :param local_path: The local path to save the file to.
        """
        try:
            logging.info(f"Downloading Google Drive file ID {file_id} to {local_path}...")
            request = self.service.files().get_media(fileId=file_id)
            fh = io.FileIO(local_path, 'wb')
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while done is False:
                status, done = downloader.next_chunk()
                logging.info(f"Download {int(status.progress() * 100)}%.")
        except Exception as e:
            logging.error(f"Failed to download file ID '{file_id}': {e}")
            raise

    def upload_file(self, local_path: str, parent_folder_id: str):
        """
        Uploads a local file to a specified folder in Google Drive.
        :param local_path: The local path of the file to upload.
        :param parent_folder_id: The ID of the parent folder in Google Drive.
        """
        try:
            file_metadata = {
                'name': os.path.basename(local_path),
                'parents': [parent_folder_id]
            }
            media = MediaFileUpload(local_path, resumable=True)
            logging.info(f"Uploading {local_path} to Google Drive folder ID {parent_folder_id}...")
            file = self.service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logging.info(f"File ID: {file.get('id')} uploaded.")
        except Exception as e:
            logging.error(f"Failed to upload file to Google Drive: {e}")
            raise

    def delete_file(self, file_id: str):
        """
        Deletes a file from Google Drive.
        :param file_id: The ID of the file to delete.
        """
        try:
            logging.info(f"Deleting Google Drive file ID {file_id}...")
            self.service.files().delete(fileId=file_id).execute()
            logging.info(f"File ID: {file_id} deleted.")
        except Exception as e:
            logging.error(f"Failed to delete file ID '{file_id}': {e}")
            raise

    def move_file(self, from_path: str, to_path: str):
        """
        Moves a file to a different folder in Google Drive.
        :param from_path: The ID of the file to move.
        :param to_path: The ID of the new parent folder.
        """
        file_id = from_path
        new_parent_id = to_path
        try:
            logging.info(f"Moving Google Drive file ID {file_id} to folder {new_parent_id}...")
            # Retrieve the existing parents to remove the old one
            file = self.service.files().get(fileId=file_id, fields='parents').execute()
            previous_parents = ",".join(file.get('parents'))
            # Move the file by updating its parents
            self.service.files().update(
                fileId=file_id,
                addParents=new_parent_id,
                removeParents=previous_parents,
                fields='id, parents'
            ).execute()
            logging.info(f"File ID: {file_id} moved.")
        except Exception as e:
            logging.error(f"Failed to move file ID '{file_id}': {e}")
            raise

    def create_folder_if_not_exists(self, folder_name: str) -> str:
        """
        Creates a folder in Google Drive if it does not already exist.
        Searches for a folder by name and creates it if not found.
        Returns the ID of the existing or newly created folder.
        
        Note: This is a simplified implementation. Google Drive allows multiple
        folders with the same name. A more robust implementation would manage
        folders by their unique IDs.
        
        :param folder_name: The name of the folder to create.
        :return: The ID of the folder.
        """
        try:
            # Search for the folder
            response = self.service.files().list(
                q=f"name='{folder_name}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                spaces='drive',
                fields='files(id, name)'
            ).execute()
            
            folders = response.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                logging.info(f"Folder '{folder_name}' already exists with ID: {folder_id}")
                return folder_id
            else:
                # Create the folder
                logging.info(f"Folder '{folder_name}' not found. Creating...")
                file_metadata = {
                    'name': folder_name,
                    'mimeType': 'application/vnd.google-apps.folder'
                }
                folder = self.service.files().create(body=file_metadata, fields='id').execute()
                folder_id = folder.get('id')
                logging.info(f"Folder '{folder_name}' created with ID: {folder_id}")
                return folder_id
        except Exception as e:
            logging.error(f"Failed to create or find folder '{folder_name}': {e}")
            raise