"""Import service for handling .osz imports"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from src.CollectionManager.domain.exceptions import ServiceOperationError
from src.CollectionManager.infrastructure.fs import BeatmapInstaller, OszExtractor
from src.CollectionManager.infrastructure.osu import BeatmapDecoder
from src.CollectionManager.infrastructure.storage import BeatmapRepository

class ImportService:
    """Service for importing .osz files."""
    
    def __init__(self, beatmap_repo: BeatmapRepository, osu_path: str | Path, tmp_path: Path = Path("tmp_import")) -> None:
        self.beatmap_repo = beatmap_repo
        self.songs_path = Path(osu_path) / "Songs"
        self.extractor = OszExtractor(tmp_path)
        self.installer = BeatmapInstaller(self.songs_path)
        self.decoder = BeatmapDecoder()

    def _extract_and_decode(self, osz_path: Path) -> tuple[Path, list]:
        beatmaps = []
        try:
            extracted_folder = self.extractor.extract(osz_path)
        except Exception as e:
            raise ServiceOperationError(f"Failed to extract .osz file {osz_path}: {e}") from e

        for item in extracted_folder.iterdir():
            if item.is_file() and item.suffix == ".osu":
                try:
                    beatmap = self.decoder.decode(item)
                    beatmaps.append(beatmap)
                except Exception as e:
                    raise ServiceOperationError(f"Failed to decode beatmap from {item}: {e}") from e

        return extracted_folder, beatmaps

    def import_osz(self, osz_path: str | Path) -> int:
        osz_path = Path(osz_path) if isinstance(osz_path, str) else osz_path
        return self.import_osz_many([osz_path])

    def import_osz_many(self, osz_paths: Sequence[str | Path]) -> int:
        beatmaps = []
        for raw_path in osz_paths:
            osz_path = Path(raw_path) if isinstance(raw_path, str) else raw_path
            extracted_folder, decoded_beatmaps = self._extract_and_decode(osz_path)
            beatmaps.extend(decoded_beatmaps)
            try:
                self.installer.install(extracted_folder)
            except Exception as e:
                raise ServiceOperationError(f"Failed to install beatmaps from {extracted_folder} to {self.songs_path}: {e}") from e

        if beatmaps:
            self.beatmap_repo.save_many(beatmaps)
        return len(beatmaps)
    
    def cleanup(self) -> None:
        """Clean up any temporary files created during import."""
        self.extractor.cleanup()
            
        