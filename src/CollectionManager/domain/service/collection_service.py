from collections.abc import Iterable, Sequence
from pathlib import Path

from loguru import logger

from src.CollectionManager.infrastructure import CollectionDbWriter
from src.CollectionManager.infrastructure.storage import BeatmapRepository, CollectionRepository

from ..model import Beatmap, Collection


class CollectionService:
    def __init__(self, collection_repository: CollectionRepository, beatmap_repository: BeatmapRepository):
        self.collection_repository = collection_repository
        self.beatmap_repository = beatmap_repository

    def _require_collection(self, name: str) -> Collection:
        collection = self.collection_repository.get(name)
        if collection is None:
            raise ValueError(f"Collection '{name}' does not exist.")
        return collection

    def _require_beatmaps(self, beatmap_hashes: Sequence[str]) -> None:
        _, missing_hashes = self.beatmap_repository.get_many(beatmap_hashes)
        if missing_hashes:
            raise ValueError(f"Beatmap with hash '{missing_hashes[0]}' does not exist.")

    def create_collection(self, name: str, beatmap_hashes: list[str]) -> Collection:
        if self.collection_repository.exists(name):
            raise ValueError(f"Collection {name} already exists.")
        collection = Collection(name=name, hashes=list(beatmap_hashes), count=len(beatmap_hashes))
        return self.collection_repository.create(collection)

    def delete_collection(self, name: str) -> None:
        """Delete a collection and its beatmap associations."""

        if not self.collection_repository.exists(name):
            raise ValueError(f"Collection {name} does not exist.")
        self.collection_repository.delete(name)

    def delete_beatmap(self, beatmap_hash: str) -> None:
        """Delete a beatmap from the beatmap repository."""

        if self.beatmap_repository.get(beatmap_hash) is None:
            raise ValueError(f"Beatmap with hash '{beatmap_hash}' does not exist.")
        self.beatmap_repository.delete(beatmap_hash)

    def rename_collection(self, old_name: str, new_name: str) -> Collection | None:
        """Rename a collection and update all associated beatmap relations."""

        if old_name == new_name:
            raise ValueError("New collection name must be different from the old name.")
        if not self.collection_repository.exists(old_name):
            raise ValueError(f"Collection '{old_name}' does not exist.")
        if self.collection_repository.exists(new_name):
            raise ValueError(f"Collection '{new_name}' already exists.")
        renamed = self.collection_repository.rename(old_name, new_name)
        if renamed is None:
            raise ValueError(f"Collection '{old_name}' does not exist.")
        return renamed

    def get_collection(self, name: str) -> Collection:
        """Retrieve a collection by name, including its beatmap hashes."""

        collection = self.collection_repository.get(name)
        if collection is None:
            raise ValueError(f"Collection '{name}' does not exist.")
        return collection

    def get_all_collections(self) -> list[Collection]:
        """Retrieve all collections."""

        return self.collection_repository.list()

    def get_beatmaps(self, name: str) -> tuple[list[Beatmap], list[str]]:
        """Retrieve all beatmaps associated with a collection. Returns a tuple of (found_beatmaps, missing_hashes)."""

        collection = self.get_collection(name)
        return self.beatmap_repository.get_many(collection.hashes)

    def add_beatmaps_to_collection(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
        """Add beatmaps to a collection. Return None if the collection does not exist."""

        self._require_collection(name)
        self._require_beatmaps(beatmap_hashes)
        updated = self.collection_repository.add_beatmaps(name, beatmap_hashes)
        if updated is None:
            raise ValueError(f"Collection '{name}' does not exist.")
        return updated

    def add_beatmaps(self, beatmaps: Iterable[Beatmap]) -> list[Beatmap]:
        """Add beatmaps to the beatmap repository."""

        return self.beatmap_repository.save_many(beatmaps)

    def remove_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
        """Remove beatmaps from a collection. Return the updated collection, or raise ValueError if the collection does not exist."""

        self._require_collection(name)
        self._require_beatmaps(beatmap_hashes)
        updated = self.collection_repository.remove_beatmaps(name, beatmap_hashes)
        if updated is None:
            raise ValueError(f"Collection '{name}' does not exist.")
        return updated

    def merge_collections(self, source_names: Sequence[str], new_name: str) -> Collection:
        """Merge multiple collections into a new collection with the given name. The source collections will not be modified or deleted."""

        if self.collection_repository.exists(new_name):
            raise ValueError(f"Collection '{new_name}' already exists.")

        unique_sources = list(dict.fromkeys(source_names))
        merged_hashes: list[str] = []
        seen_hashes: set[str] = set()

        for source_name in unique_sources:
            source_collection = self._require_collection(source_name)
            for beatmap_hash in source_collection.hashes:
                if beatmap_hash in seen_hashes:
                    continue
                seen_hashes.add(beatmap_hash)
                merged_hashes.append(beatmap_hash)

        merged_collection = Collection(name=new_name, count=len(merged_hashes), hashes=merged_hashes)
        return self.collection_repository.create(merged_collection)

    def is_beatmap_in_collection(self, collection_name: str, beatmap_hash: str) -> bool:
        """Check if a beatmap hash is part of a collection."""

        if not self.collection_repository.exists(collection_name):
            raise ValueError(f"Collection '{collection_name}' does not exist.")
        return self.collection_repository.is_beatmap_in_collection(collection_name, beatmap_hash)

    def export_collections(self, collection_names: list[str], output_path: str | Path) -> None:
        """Export selected collections to a new collection.db file.

        Args:
            collection_names: List of collection names to export
            output_path: Path where the collection.db file will be saved

        Returns:
            None
        """

        output_path = Path(output_path)
        collections = [self._require_collection(name) for name in collection_names]

        try:
            writer = CollectionDbWriter()
            writer.write(collections, output_path)
        except Exception as exc:
            logger.exception(f"Failed to export collections to {output_path}")
            raise RuntimeError(f"Failed to export collections: {exc}") from exc
        else:
            logger.info(f"Successfully exported {len(collections)} collections to {output_path}")
        