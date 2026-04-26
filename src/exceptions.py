# exceptions.py


class PermanentError(Exception):
    """An error that will not be fixed by a retry (e.g., a corrupted file)."""

    pass


class TransientError(Exception):
    """A temporary error (e.g., a network failure) that might resolve on a retry."""

    pass


class StorageError(Exception):
    """Base class for storage provider errors."""

    pass


class StorageTransientError(StorageError, TransientError):
    """A temporary storage provider error that should be retried."""

    pass


class StoragePermanentError(StorageError, PermanentError):
    """A permanent storage provider error that should not be retried."""

    pass


class StorageAuthError(StoragePermanentError):
    """Storage authentication or authorization failed."""

    pass


class StorageNotFoundError(StoragePermanentError):
    """A required storage file or folder was not found."""

    pass


class RecognitionError(Exception):
    """Base class for recognition provider errors."""

    pass


class RecognitionTransientError(RecognitionError, TransientError):
    """A temporary recognition provider error that should be retried."""

    pass


class RecognitionPermanentError(RecognitionError, PermanentError):
    """A permanent recognition provider error that should not be retried."""

    pass


class RecognitionAuthError(RecognitionPermanentError):
    """Recognition authentication or authorization failed."""

    pass
