from collections.abc import Iterable, Sequence
from pathlib import Path

from loguru import logger

from src.CollectionManager.domain.exceptions import (
    ServiceConflictError,
    ServiceDataError,
    ServiceNotFoundError,
    ServiceOperationError,
    ServiceValidationError,
)
from src.CollectionManager.infrastructure import CollectionDbWriter
from src.CollectionManager.infrastructure.exceptions.repository import RepositoryNotFoundError
from src.CollectionManager.infrastructure.storage import BeatmapRepository, CollectionRepository

from ..model import Beatmap, Collection


class CollectionService:
    def __init__(self, collection_repository: CollectionRepository, beatmap_repository: BeatmapRepository):
        self.collection_repository = collection_repository
        self.beatmap_repository = beatmap_repository

    @staticmethod
    def _log_info(message: str) -> None:
        logger.info(message)

    @staticmethod
    def _log_expected_failure(message: str, exc: Exception) -> None:
        logger.warning(f"{message}: {exc}")

    @staticmethod
    def _log_unexpected_failure(message: str) -> None:
        logger.exception(message)

    def _require_collection(self, name: str) -> Collection:
        try:
            return self.collection_repository.get(name)
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to load collection '{name}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to load collection '{name}'.")
            raise ServiceOperationError(f"Failed to load collection '{name}'.") from exc

    def _require_beatmaps(self, beatmap_hashes: Sequence[str]) -> None:
        try:
            _, missing_hashes = self.beatmap_repository.get_many(beatmap_hashes)
        except Exception as exc:
            self._log_unexpected_failure("Failed to validate beatmap hashes.")
            raise ServiceOperationError("Failed to validate beatmap hashes.") from exc
        if missing_hashes:
            error = ServiceNotFoundError(f"Beatmap with hash '{missing_hashes[0]}' does not exist.")
            self._log_expected_failure("Failed to validate beatmap hashes", error)
            raise error

    def create_collection(self, name: str, beatmap_hashes: list[str]) -> Collection:
        try:
            if self.collection_repository.exists(name):
                error = ServiceConflictError(f"Collection '{name}' already exists.")
                self._log_expected_failure(f"Failed to create collection '{name}'", error)
                raise error
            collection = Collection(name=name, hashes=list(beatmap_hashes))
            created_collection = self.collection_repository.create(collection)
            self._log_info(f"Created collection '{name}' with {len(created_collection.hashes)} beatmaps.")
            return created_collection
        except ServiceConflictError:
            raise
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to create collection '{name}'.")
            raise ServiceOperationError(f"Failed to create collection '{name}'.") from exc

    def import_collections(self, collections: Sequence[Collection]) -> list[Collection]:
        """Create multiple collections efficiently while preserving duplicate-name checks."""

        results = list(collections)
        if not results:
            return []

        seen_names: set[str] = set()
        for collection in results:
            if collection.name in seen_names:
                error = ServiceConflictError(f"Collection '{collection.name}' already exists.")
                self._log_expected_failure("Failed to import collections", error)
                raise error
            seen_names.add(collection.name)

        try:
            existing_names = self.collection_repository.existing_names([collection.name for collection in results])
            if existing_names:
                error = ServiceConflictError(f"Collection '{sorted(existing_names)[0]}' already exists.")
                self._log_expected_failure("Failed to import collections", error)
                raise error
            return self.collection_repository.create_many(results)
        except ServiceConflictError:
            raise
        except Exception as exc:
            self._log_unexpected_failure("Failed to import collections.")
            raise ServiceOperationError("Failed to import collections.") from exc

    def delete_collection(self, name: str) -> None:
        """Delete a collection and its beatmap associations."""

        try:
            self.collection_repository.delete(name)
            self._log_info(f"Deleted collection '{name}'.")
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to delete collection '{name}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to delete collection '{name}'.")
            raise ServiceOperationError(f"Failed to delete collection '{name}'.") from exc

    def delete_beatmap(self, beatmap_hash: str) -> None:
        """Delete a beatmap from the beatmap repository."""

        try:
            self.beatmap_repository.delete(beatmap_hash)
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to delete beatmap '{beatmap_hash}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to delete beatmap '{beatmap_hash}'.")
            raise ServiceOperationError(f"Failed to delete beatmap '{beatmap_hash}'.") from exc

    def rename_collection(self, old_name: str, new_name: str) -> Collection:
        """Rename a collection and update all associated beatmap relations."""

        if old_name == new_name:
            error = ServiceValidationError("New collection name must be different from the old name.")
            self._log_expected_failure("Failed to rename collection", error)
            raise error
        try:
            if self.collection_repository.exists(new_name):
                error = ServiceConflictError(f"Collection '{new_name}' already exists.")
                self._log_expected_failure(f"Failed to rename collection '{old_name}'", error)
                raise error
            renamed_collection = self.collection_repository.rename(old_name, new_name)
            self._log_info(f"Renamed collection '{old_name}' to '{new_name}'.")
            return renamed_collection
        except ServiceConflictError:
            raise
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to rename collection '{old_name}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to rename collection '{old_name}'.")
            raise ServiceOperationError(f"Failed to rename collection '{old_name}'.") from exc

    def get_collection(self, name: str) -> Collection:
        return self._require_collection(name)

    def get_all_collections(self) -> list[Collection]:
        """Retrieve all collections."""

        try:
            return self.collection_repository.list()
        except Exception as exc:
            self._log_unexpected_failure("Failed to load collections.")
            raise ServiceOperationError("Failed to load collections.") from exc

    def get_beatmaps(self, name: str) -> tuple[list[Beatmap], list[str]]:
        """Retrieve all beatmaps associated with a collection. Returns a tuple of (found_beatmaps, missing_hashes)."""

        collection = self.get_collection(name)
        try:
            return self.beatmap_repository.get_many(collection.hashes)
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to load beatmaps for collection '{name}'.")
            raise ServiceOperationError(f"Failed to load beatmaps for collection '{name}'.") from exc

    def add_beatmaps_to_collection(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
        """Add beatmaps to a collection."""

        self._require_collection(name)
        # self._require_beatmaps(beatmap_hashes) # Missing hashes is allowed
        try:
            updated_collection = self.collection_repository.add_beatmaps(name, beatmap_hashes)
            self._log_info(f"Added {len(beatmap_hashes)} beatmaps to collection '{name}'.")
            return updated_collection
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to add beatmaps to collection '{name}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to add beatmaps to collection '{name}'.")
            raise ServiceOperationError(f"Failed to add beatmaps to collection '{name}'.") from exc

    def add_beatmaps(self, beatmaps: Iterable[Beatmap]) -> list[Beatmap]:
        """Add beatmaps to the beatmap repository."""

        try:
            return self.beatmap_repository.save_many(beatmaps)
        except Exception as exc:
            self._log_unexpected_failure("Failed to save beatmaps.")
            raise ServiceOperationError("Failed to save beatmaps.") from exc

    def remove_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
        """Remove beatmaps from a collection and return the updated collection."""

        self._require_collection(name)
        self._require_beatmaps(beatmap_hashes)
        try:
            updated_collection = self.collection_repository.remove_beatmaps(name, beatmap_hashes)
            self._log_info(f"Removed {len(beatmap_hashes)} beatmaps from collection '{name}'.")
            return updated_collection
        except RepositoryNotFoundError as exc:
            error = ServiceNotFoundError(str(exc))
            self._log_expected_failure(f"Failed to remove beatmaps from collection '{name}'", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to remove beatmaps from collection '{name}'.")
            raise ServiceOperationError(f"Failed to remove beatmaps from collection '{name}'.") from exc

    def merge_collections(self, source_names: Sequence[str], new_name: str) -> Collection:
        """Merge multiple collections into a new collection with the given name. The source collections will not be modified or deleted."""

        try:
            if self.collection_repository.exists(new_name):
                error = ServiceConflictError(f"Collection '{new_name}' already exists.")
                self._log_expected_failure(f"Failed to merge collections into '{new_name}'", error)
                raise error
        except ServiceConflictError:
            raise
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to prepare merge into collection '{new_name}'.")
            raise ServiceOperationError(f"Failed to prepare merge into collection '{new_name}'.") from exc

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

        merged_collection = Collection(name=new_name, hashes=merged_hashes)
        try:
            created_collection = self.collection_repository.create(merged_collection)
            self._log_info(
                f"Merged {len(unique_sources)} collections into '{new_name}' with {len(created_collection.hashes)} beatmaps."
            )
            return created_collection
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to create merged collection '{new_name}'.")
            raise ServiceOperationError(f"Failed to create merged collection '{new_name}'.") from exc

    def is_beatmap_in_collection(self, collection_name: str, beatmap_hash: str) -> bool:
        """Check if a beatmap hash is part of a collection."""

        self._require_collection(collection_name)
        try:
            return self.collection_repository.is_beatmap_in_collection(collection_name, beatmap_hash)
        except Exception as exc:
            self._log_unexpected_failure(
                f"Failed to check whether beatmap '{beatmap_hash}' is in collection '{collection_name}'."
            )
            raise ServiceOperationError(
                f"Failed to check whether beatmap '{beatmap_hash}' is in collection '{collection_name}'."
            ) from exc

    def export_collections(self, collection_names: list[str], output_path: str | Path) -> None:
        """Export selected collections to a collection.db file."""

        output_path = Path(output_path)
        collections = [self._require_collection(name) for name in collection_names]

        try:
            writer = CollectionDbWriter()
            writer.write(collections, output_path)
        except OSError as exc:
            error = ServiceDataError(f"Failed to export collections to '{output_path}': {exc}")
            self._log_expected_failure(f"Failed to export collections to {output_path}", error)
            raise error from exc
        except Exception as exc:
            self._log_unexpected_failure(f"Failed to export collections to {output_path}.")
            raise ServiceOperationError("Failed to export collections.") from exc
        else:
            self._log_info(f"Exported {len(collections)} collections to {output_path}.")
        
