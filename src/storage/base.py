# storage/base.py
from abc import ABC, abstractmethod
from typing import List
from .dto import FileMetadata


class StorageClient(ABC):
    """
    Abstract base class for a cloud storage client.
    Defines the common interface that all specific storage clients
    (e.g., Dropbox, Google Drive) must implement.
    Implementations should translate provider SDK failures into domain
    exceptions from src.exceptions instead of leaking raw SDK exceptions.
    """

    @abstractmethod
    def list_files(self, folder_id: str) -> List[FileMetadata]:
        """
        Lists all files in a given folder.

        :param folder_id: The ID or path of the folder to list.
        :return: A list of FileMetadata objects.
        """
        pass

    @abstractmethod
    def download_file(self, file_id: str, local_path: str):
        """
        Downloads a file from the storage.

        :param file_id: The ID or path of the file to download.
        :param local_path: The local path to save the file to.
        """
        pass

    @abstractmethod
    def upload_file(self, local_path: str, folder_id: str, filename: str):
        """
        Uploads a file to the storage.

        :param local_path: The local path of the file to upload.
        :param folder_id: The ID of the destination folder.
        :param filename: The name of the file in the destination.
        """
        pass

    @abstractmethod
    def file_exists(self, folder_id: str, filename: str) -> bool:
        """
        Checks whether a file with the given name exists in a folder.

        :param folder_id: The ID or path of the folder to inspect.
        :param filename: The file name to look for.
        :return: True if the file exists, otherwise False.
        """
        pass

    @abstractmethod
    def delete_file(self, file_id: str):
        """
        Deletes a file from the storage.

        :param file_id: The ID or path of the file to delete.
        """
        pass

    @abstractmethod
    def move_file(self, file_id: str, to_folder_id: str):
        """
        Moves a file to a different folder.

        :param file_id: The original ID or path of the file.
        :param to_folder_id: The destination folder ID or path.
        """
        pass

    @abstractmethod
    def verify_folder_exists(self, folder_id: str):
        """
        Verifies if a folder exists.
        Raises an error if the folder does not exist or is inaccessible.

        :param folder_id: The path or ID of the folder to verify.
        """
        pass
