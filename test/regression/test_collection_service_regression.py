from sqlmodel import select

from src.CollectionManager.domain.exceptions import (
    ServiceConflictError,
    ServiceNotFoundError,
)
from src.CollectionManager.domain.model import Collection
from src.CollectionManager.infrastructure.storage.models import CollectionBeatmapRecord


def test_collection_crud_merge_and_search_flow(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps(
        [
            beatmap_factory("hash-a", title="Alpha Song"),
            beatmap_factory("hash-b", title="Beta Song"),
            beatmap_factory("hash-c", title="Gamma Song"),
        ]
    )

    created = service.create_collection("Alpha", ["hash-a"])
    assert created.hashes == ["hash-a"]

    imported = service.import_collections(
        [
            Collection(name="Beta", hashes=["hash-b"]),
            Collection(name="Gamma", hashes=["hash-c", "hash-b"]),
        ]
    )
    assert [collection.name for collection in imported] == ["Beta", "Gamma"]

    renamed = service.rename_collection("Alpha", "Alpha Renamed")
    assert renamed.name == "Alpha Renamed"

    updated = service.add_beatmaps_to_collection("Alpha Renamed", ["hash-b", "hash-a", "hash-c"])
    assert updated.hashes == ["hash-a", "hash-b", "hash-c"]

    merged = service.merge_collections(["Alpha Renamed", "Gamma", "Alpha Renamed"], "Merged")
    assert merged.hashes == ["hash-a", "hash-b", "hash-c"]
    assert service.get_collection("Gamma").hashes == ["hash-c", "hash-b"]

    service.delete_collection("Beta")
    collections = service.get_all_collections()
    assert [collection.name for collection in collections] == ["Alpha Renamed", "Gamma", "Merged"]
    assert [collection.name for collection in container.search_service.search_collections("renamed")] == ["Alpha Renamed"]


def test_import_collections_rejects_duplicates_atomically(container) -> None:
    service = container.collection_service
    service.create_collection("Existing", [])

    try:
        service.import_collections(
            [
                Collection(name="Batch", hashes=[]),
                Collection(name="Batch", hashes=[]),
            ]
        )
    except ServiceConflictError as exc:
        assert str(exc) == "Collection 'Batch' already exists."
    else:
        raise AssertionError("Expected duplicate names within the import batch to be rejected")

    assert [collection.name for collection in service.get_all_collections()] == ["Existing"]

    try:
        service.import_collections([Collection(name="Existing", hashes=[]), Collection(name="New One", hashes=[])])
    except ServiceConflictError as exc:
        assert str(exc) == "Collection 'Existing' already exists."
    else:
        raise AssertionError("Expected duplicate names against existing collections to be rejected")

    assert [collection.name for collection in service.get_all_collections()] == ["Existing"]


def test_remove_reindexes_positions_and_updates_count(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps(
        [
            beatmap_factory("hash-a"),
            beatmap_factory("hash-b"),
            beatmap_factory("hash-c"),
            beatmap_factory("hash-d"),
        ]
    )
    service.create_collection("Ordered", ["hash-a", "hash-b", "hash-c", "hash-d"])

    updated = service.remove_beatmaps("Ordered", ["hash-b", "hash-d"])
    assert updated.hashes == ["hash-a", "hash-c"]
    assert updated.count == 2

    with container.db.collection_session() as session:
        rows = session.exec(
            select(CollectionBeatmapRecord)
            .where(CollectionBeatmapRecord.collection_name == "Ordered")
            .order_by(CollectionBeatmapRecord.position)
        ).all()

    assert [(row.beatmap_hash, row.position) for row in rows] == [("hash-a", 0), ("hash-c", 1)]


def test_get_beatmaps_preserves_missing_hashes_in_collection(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b")])
    service.create_collection("With Missing", ["hash-a", "hash-b"])

    service.delete_beatmap("hash-b")

    collection = service.get_collection("With Missing")
    found, missing = service.get_beatmaps("With Missing")
    assert collection.hashes == ["hash-a", "hash-b"]
    assert [beatmap.md5_hash for beatmap in found] == ["hash-a"]
    assert missing == ["hash-b"]


def test_add_and_remove_validate_missing_entities(container, beatmap_factory) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a")])
    service.create_collection("Target", [])

    try:
        service.remove_beatmaps("Target", ["missing-hash"])
    except ServiceNotFoundError as exc:
        assert str(exc) == "Beatmap with hash 'missing-hash' does not exist."
    else:
        raise AssertionError("Expected a missing beatmap hash to be rejected")

    try:
        service.remove_beatmaps("Missing Collection", ["hash-a"])
    except ServiceNotFoundError as exc:
        assert str(exc) == "Collection 'Missing Collection' does not exist."
    else:
        raise AssertionError("Expected a missing collection to be rejected")