class RepositoryError(Exception):
    """Base exception for persistence-layer failures."""


class RepositoryNotFoundError(RepositoryError):
    """Raised when a repository lookup targets a missing record."""