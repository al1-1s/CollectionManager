from pathlib import Path

class BeatmapInstallError(Exception):
    """Custom exception for beatmap installation errors."""
    def __init__(self, message: str, path: Path):
        super().__init__(message)
        self.path = path
        
class ExtractionError(Exception):
    """Custom exception for extraction errors."""
    def __init__(self, message: str, path: Path):
        super().__init__(message)
        self.path = path
