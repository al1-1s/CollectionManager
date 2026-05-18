from pathlib import Path
from loguru import logger

from src.CollectionManager.infrastructure.exceptions.fs import BeatmapInstallError

class BeatmapInstaller:
    def __init__(self, songs_dir: Path):
        self.songs_dir = songs_dir
        self.songs_dir.mkdir(parents=True, exist_ok=True)

    def install(self, source_folder_path: Path) -> None:
        if not source_folder_path.is_dir():
            raise BeatmapInstallError(f"Source path {source_folder_path} is not a directory.", source_folder_path)
        dest_folder = self.songs_dir / source_folder_path.name
        try:
            import shutil
            shutil.copytree(source_folder_path, dest_folder, dirs_exist_ok=True)
        except Exception as e:
            raise BeatmapInstallError(
                f"Failed to install beatmap from {source_folder_path} to {dest_folder}: {e}",
                source_folder_path,
            ) from e
        