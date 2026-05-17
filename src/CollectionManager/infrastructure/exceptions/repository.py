class RepositoryError(Exception):
    """Base exception for persistence-layer failures."""


class CollectionNotFoundError(RepositoryError):
    """Raised when a collection lookup targets a missing record."""

    def __init__(self, message: str, collection_name: str):
        super().__init__(message)
        self.collection_name = collection_name


class BeatmapNotFoundError(RepositoryError):
    """Raised when a beatmap lookup targets a missing record."""

    def __init__(self, message: str, md5_hash: str):
        super().__init__(message)
        self.md5_hash = md5_hash