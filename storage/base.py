# storage/base.py
from abc import ABC, abstractmethod
from typing import List, Any


class StorageClient(ABC):
    """
    Abstract base class for a cloud storage client.
    Defines the common interface that all specific storage clients
    (e.g., Dropbox, Google Drive) must implement.
    """

    @abstractmethod
    def list_files(self, folder_path: str) -> List[Any]:
        """
        Lists all files in a given folder.

        :param folder_path: The path or ID of the folder to list.
        :return: A list of file metadata objects.
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
    def upload_file(self, local_path: str, remote_path: str):
        """
        Uploads a file to the storage.

        :param local_path: The local path of the file to upload.
        :param remote_path: The destination path or ID in the storage.
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
    def move_file(self, from_path: str, to_path: str):
        """
        Moves or renames a file within the storage.

        :param from_path: The original path or ID of the file.
        :param to_path: The new path or ID of the file.
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
