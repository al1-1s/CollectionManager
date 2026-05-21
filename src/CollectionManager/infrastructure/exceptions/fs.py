"""Infrastructure filesystem exception boundary."""

from __future__ import annotations

from pathlib import Path


class FileSystemError(Exception):
    """Raised when infrastructure filesystem operations fail."""

    def __init__(self, message: str, path: str | Path | None = None):
        super().__init__(message)
        self.path = Path(path) if path is not None else None
