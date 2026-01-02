# src/storage/dto.py
from pydantic import BaseModel
from typing import Optional


class FileMetadata(BaseModel):
    """
    A standardized Data Transfer Object for file metadata to abstract away
    provider-specific file representations.
    """

    id: str
    name: str
    path: str
    folder_id: Optional[str] = None
