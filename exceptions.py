# exceptions.py

class PermanentError(Exception):
    """An error that will not be fixed by a retry (e.g., a corrupted file)."""
    pass

class TransientError(Exception):
    """A temporary error (e.g., a network failure) that might resolve on a retry."""
    pass
