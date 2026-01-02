# storage/base.py
from abc import ABC, abstractmethod
from typing import List
from .dto import FileMetadata


class StorageClient(ABC):
    """
    Abstract base class for a cloud storage client.
    Defines the common interface that all specific storage clients
    (e.g., Dropbox, Google Drive) must implement.
    """

    @abstractmethod
    def list_files(self, folder_path: str) -> List[FileMetadata]:
        """
        Lists all files in a given folder.

        :param folder_path: The path or ID of the folder to list.
        :return: A list of standardized FileMetadata DTOs.
        """
        pass

    @abstractmethod
    def download_file(self, file_path: str, local_path: str):
        """
        Downloads a file from the storage.

        :param file_path: The path or ID of the file to download.
        :param local_path: The local path to save the file to.
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, folder_id: str, filename: str):
        """
        Uploads a file to a specific folder with a given filename.

        :param local_path: The local path of the file to upload.
        :param folder_id: The ID of the destination folder.
        :param filename: The name for the uploaded file.
        """
        pass

    @abstractmethod
    def delete_file(self, file_path: str):
        """
        Deletes a file from the storage.

        :param file_path: The path or ID of the file to delete.
        """
        pass

    @abstractmethod
    def move_file(self, file_id: str, new_folder_id: str):
        """
        Moves a file to a different folder.

        :param file_id: The ID or path of the file to move.
        :param new_folder_id: The ID of the destination folder.
        """
        pass

    @abstractmethod
    def verify_folder_exists(self, folder_path: str):
        """
        Verifies if a folder exists at the given path/ID.
        Raises an error if the folder does not exist or is inaccessible.

        :param folder_path: The path or ID of the folder to verify.
        """
        pass
