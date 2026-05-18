"""Import service for handling .osz imports"""

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

    def import_osz(self, osz_path: str | Path) -> None:
        osz_path = Path(osz_path) if isinstance(osz_path, str) else osz_path
        bms = []
        try:
            extracted_folder = self.extractor.extract(osz_path)
        except Exception as e:
            raise ServiceOperationError(f"Failed to extract .osz file {osz_path}: {e}", osz_path) from e
        try:
            self.installer.install(extracted_folder)
        except Exception as e:
            raise ServiceOperationError(f"Failed to install beatmaps from {extracted_folder} to {self.songs_path}: {e}", extracted_folder) from e
        for item in extracted_folder.iterdir():
            if item.is_file() and item.suffix == ".osu":
                try:
                    beatmap = self.decoder.decode(item)
                    bms.append(beatmap)
                except Exception as e:
                    raise ServiceOperationError(f"Failed to decode beatmap from {item}: {e}", item) from e
        self.beatmap_repo.save_many(bms)
    
    def cleanup(self) -> None:
        """Clean up any temporary files created during import."""
        self.extractor.cleanup()
            
        