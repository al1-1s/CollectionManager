"""Application bootstrap helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from loguru import logger

from src.CollectionManager.app.dependency import Container
from src.CollectionManager.app.logger import DEFAULT_LEVEL, init_logging
from src.CollectionManager.infrastructure.osu import collection as collection_structure
from src.CollectionManager.infrastructure.osu import map_beatmap, map_collection, osuDb
from src.CollectionManager.infrastructure.storage import BeatmapRepository, CollectionRepository, SqliteDB


@dataclass(slots=True)
class LoadSummary:
    """Summary of application data loaded from osu! files."""

    osu_dir: Path
    beatmaps_loaded: int = 0
    collections_loaded: int = 0
    imported_collection_db: bool = False


def summarize_current_data(container: Container, osu_dir: str | Path) -> LoadSummary:
    """Summarize the contents already present in the database without reimporting."""

    return LoadSummary(
        osu_dir=Path(osu_dir),
        beatmaps_loaded=container.beatmap_repository.count(),
        collections_loaded=container.collection_repository.count(),
        imported_collection_db=False,
    )


def _resolve_log_level(debug: bool | None = None) -> str:
    if debug is True:
        return "DEBUG"
    if debug is False:
        return "INFO"

    if os.getenv("DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}:
        return "DEBUG"

    return os.getenv("LOG_LEVEL", DEFAULT_LEVEL).upper()


def build_container(debug: bool | None = None, create_schema: bool = True) -> Container:
    """Initialize logging and build the shared dependency container."""

    init_logging(level=_resolve_log_level(debug))
    return Container(db=SqliteDB(create_schema=create_schema))


def init_service(debug: bool | None = None) -> tuple[CollectionRepository, BeatmapRepository]:
    """Initialize logging and return repositories used by tests and startup code."""

    container = build_container(debug=debug)
    logger.info("Initialized application container with repositories and services")
    return container.collection_repository, container.beatmap_repository


def init_app(debug: bool | None = None, create_schema: bool = True) -> Container:
    """Initialize the application container for the UI layer."""

    return build_container(debug=debug, create_schema=create_schema)


def _load_beatmaps(container: Container, osu_db_path: Path) -> int:
    with osu_db_path.open("rb") as handle:
        raw_osu = osuDb.parse_stream(handle)
    beatmaps = [map_beatmap(entry) for entry in raw_osu.beatmaps]
    container.collection_service.add_beatmaps(beatmaps)
    return len(beatmaps)


def _load_collections(container: Container, collection_db_path: Path) -> int:
    with collection_db_path.open("rb") as handle:
        raw_collection = collection_structure.parse_stream(handle)
    collections = [map_collection(entry) for entry in raw_collection.collections]
    for collection in collections:
        container.collection_service.create_collection(collection.name, collection.hashes)
    return len(collections)


def load_initial_data(container: Container, osu_dir: str | Path) -> LoadSummary:
    """Reset the storage layer and import beatmaps and collections from an osu! directory."""

    osu_dir_path = Path(osu_dir)
    osu_db_path = osu_dir_path / "osu!.db"
    collection_db_path = osu_dir_path / "collection.db"

    if not osu_db_path.exists():
        raise FileNotFoundError(f"Missing osu!.db: {osu_db_path}")

    container.db.reset()
    beatmap_count = _load_beatmaps(container, osu_db_path)
    collection_count = 0
    imported_collection_db = False

    if collection_db_path.exists():
        collection_count = _load_collections(container, collection_db_path)
        imported_collection_db = True
    else:
        logger.warning(f"collection.db was not found at {collection_db_path}")

    logger.info(f"Loaded {beatmap_count} beatmaps and {collection_count} collections from {osu_dir_path}")
    return LoadSummary(
        osu_dir=osu_dir_path,
        beatmaps_loaded=beatmap_count,
        collections_loaded=collection_count,
        imported_collection_db=imported_collection_db,
    )


def import_collection_db(container: Container, collection_db_path: str | Path) -> int:
    """Import collections from a standalone collection.db file into the current storage."""

    path = Path(collection_db_path)
    if not path.exists():
        raise FileNotFoundError(f"Missing collection.db: {path}")
    count = _load_collections(container, path)
    logger.info(f"Imported {count} collections from {path}")
    return count
