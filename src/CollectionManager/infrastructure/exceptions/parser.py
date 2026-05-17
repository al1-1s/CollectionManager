from pathlib import Path
from typing import Any


class ParseError(Exception):
    """Custom exception for parsing errors."""

    def __init__(
        self,
        message: str,
        pos: int,
        context: str | None = None,
    ):
        super().__init__(message)
        self.pos = pos
        self.context = context


class MissingFieldError(Exception):
    """Custom exception for mapping errors."""

    def __init__(self, message: str, missing_field: str, raw_data: Any):
        super().__init__(message)
        self.missing_field = missing_field
        self.raw_data = raw_data


class BeatmapDecodeError(Exception):
    """Custom exception for `.osu` beatmap decoding errors."""

    def __init__(
        self,
        message: str,
        beatmap_path: str | Path,
        line_number: int | None = None,
        context: str | None = None,
    ):
        super().__init__(message)
        self.beatmap_path = Path(beatmap_path)
        self.line_number = line_number
        self.context = context
