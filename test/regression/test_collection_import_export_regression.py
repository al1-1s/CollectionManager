from pathlib import Path

import pytest

from src.CollectionManager.app import bootstrap
from src.CollectionManager.domain.exceptions import DataImportError
from src.CollectionManager.domain.model import Collection
from src.CollectionManager.infrastructure.osu.collection_db_parser import parse_collection_db_stream
from src.CollectionManager.infrastructure.osu.collection_db_writer import CollectionDbWriter


def _parse_collection_db(path: Path):
    with path.open("rb") as handle:
        return parse_collection_db_stream(handle)


def test_export_and_reimport_single_and_multiple_collections(container, beatmap_factory, temp_workspace: Path) -> None:
    service = container.collection_service
    service.add_beatmaps(
        [
            beatmap_factory("hash-a"),
            beatmap_factory("hash-b"),
            beatmap_factory("hash-c"),
        ]
    )
    service.create_collection("Solo", ["hash-a"])
    service.create_collection("Team", ["hash-b", "hash-c"])

    export_path = temp_workspace / "exports" / "collections.db"
    service.export_collections(["Solo", "Team"], export_path)

    parsed = _parse_collection_db(export_path)
    assert parsed.version == 20251020
    assert parsed.collection_count == 2
    assert [(item.name, list(item.map_hashes)) for item in parsed.collections] == [
        ("Solo", ["hash-a"]),
        ("Team", ["hash-b", "hash-c"]),
    ]

    container.db.reset()
    imported_count = bootstrap.import_collection_db(container, export_path)
    assert imported_count == 2
    assert [(collection.name, collection.hashes) for collection in service.get_all_collections()] == [
        ("Solo", ["hash-a"]),
        ("Team", ["hash-b", "hash-c"]),
    ]


def test_export_preserves_empty_and_missing_hash_collections(container, beatmap_factory, temp_workspace: Path) -> None:
    service = container.collection_service
    service.add_beatmaps([beatmap_factory("hash-a"), beatmap_factory("hash-b")])
    service.create_collection("Empty", [])
    service.create_collection("Missing Aware", ["hash-a", "hash-b"])
    service.delete_beatmap("hash-b")

    export_path = temp_workspace / "exports" / "edge-cases.db"
    service.export_collections(["Empty", "Missing Aware"], export_path)

    parsed = _parse_collection_db(export_path)
    assert [(item.name, list(item.map_hashes)) for item in parsed.collections] == [
        ("Empty", []),
        ("Missing Aware", ["hash-a", "hash-b"]),
    ]

    container.db.reset()
    imported_count = bootstrap.import_collection_db(container, export_path)
    assert imported_count == 2
    assert service.get_collection("Empty").hashes == []
    assert service.get_collection("Missing Aware").hashes == ["hash-a", "hash-b"]


def test_import_collection_db_rejects_duplicate_names_without_partial_write(container, temp_workspace: Path) -> None:
    service = container.collection_service
    service.create_collection("Existing", [])
    export_path = temp_workspace / "imports" / "duplicate.db"
    CollectionDbWriter().write(
        [
            Collection(name="Existing", hashes=["hash-a"]),
            Collection(name="Fresh", hashes=["hash-b"]),
        ],
        export_path,
    )

    with pytest.raises(DataImportError) as exc_info:
        bootstrap.import_collection_db(container, export_path)

    assert exc_info.value.source_path == export_path
    assert [collection.name for collection in service.get_all_collections()] == ["Existing"]
