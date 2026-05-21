"""Infrastructure parser exception boundary."""

from __future__ import annotations

from pathlib import Path
from typing import Any


class ParseError(Exception):
    """Raised when infrastructure parsing, mapping, or decode operations fail."""

    def __init__(
        self,
        message: str,
        pos: int | None = None,
        *,
        context: str | None = None,
        path: str | Path | None = None,
        line_number: int | None = None,
        details: Any | None = None,
    ):
        super().__init__(message)
        self.pos = pos
        self.context = context
        self.path = Path(path) if path is not None else None
        self.line_number = line_number
        self.details = details
