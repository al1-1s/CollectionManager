"""Viewmodels that mediate between Qt windows and domain services."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from dataclasses import dataclass, field
from collections.abc import Sequence

from src.CollectionManager.domain.model import Beatmap, Collection
from src.CollectionManager.domain.service import CollectionService, SearchService

from .i18n import tr


@dataclass(slots=True)
class CollectionSummary:
    name: str
    count: int


@dataclass(slots=True)
class BeatmapRow:
    md5_hash: str
    display_name: str
    status: str
    artist: str = ""
    title: str = ""
    difficulty: str = ""
    creator: str = ""
    beatmap_id: int | None = None
    last_updated: int = 0
    stars: float = 0.0
    ar: float = 0.0
    cs: float = 0.0
    od: float = 0.0
    hp: float = 0.0
    beatmap: Beatmap | None = None

    @property
    def is_available(self) -> bool:
        return self.status == "available"

    @property
    def last_updated_display(self) -> str:
        if self.last_updated <= 0:
            return "-"

        try:
            if self.last_updated >= 10**17:
                updated_at = datetime(1, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=self.last_updated / 10)
            elif self.last_updated >= 10**12:
                updated_at = datetime.fromtimestamp(self.last_updated / 1000, tz=timezone.utc)
            else:
                updated_at = datetime.fromtimestamp(self.last_updated, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return "-"
        return updated_at.astimezone().strftime("%Y-%m-%d %H:%M")


@dataclass(slots=True)
class CollectionChoice:
    name: str
    count: int
    checked: bool = False


def beatmap_to_row(beatmap: Beatmap) -> BeatmapRow:
    return BeatmapRow(
        md5_hash=beatmap.md5_hash,
        display_name=beatmap.get_name(),
        status="available",
        artist=beatmap.artist,
        title=beatmap.title,
        difficulty=beatmap.difficulty,
        creator=beatmap.creator,
        beatmap_id=beatmap.beatmap_id,
        last_updated=beatmap.last_modified,
        stars=beatmap.no_mod_sr,
        ar=beatmap.ar,
        cs=beatmap.cs,
        od=beatmap.od,
        hp=beatmap.hp,
        beatmap=beatmap,
    )


def missing_beatmap_row(md5_hash: str) -> BeatmapRow:
    return BeatmapRow(
        md5_hash=md5_hash,
        display_name=f"unknown - {md5_hash}",
        status="missing",
    )


def _text_key(value: str) -> tuple[int, str]:
    normalized = value.casefold().strip()
    return (0 if normalized else 1, normalized)


def sort_beatmap_rows(rows: Sequence[BeatmapRow], sort_by: str) -> list[BeatmapRow]:
    key = sort_by.strip().casefold()
    if key == "artist":
        return sorted(rows, key=lambda row: (_text_key(row.artist), _text_key(row.title), row.md5_hash))
    if key == "last_updated":
        return sorted(rows, key=lambda row: (-row.last_updated, _text_key(row.title), row.md5_hash))
    if key == "difficulty":
        return sorted(rows, key=lambda row: (-row.stars, _text_key(row.difficulty), row.md5_hash))
    if key == "creator":
        return sorted(rows, key=lambda row: (_text_key(row.creator), _text_key(row.title), row.md5_hash))
    return sorted(rows, key=lambda row: (_text_key(row.title), _text_key(row.artist), row.md5_hash))


def filter_beatmap_rows(rows: Sequence[BeatmapRow], query: str) -> list[BeatmapRow]:
    terms = [term for term in query.casefold().split() if term]
    if not terms:
        return list(rows)

    filtered: list[BeatmapRow] = []
    for row in rows:
        haystack = " ".join(
            [
                row.display_name,
                row.artist,
                row.title,
                row.difficulty,
                row.creator,
                row.md5_hash,
                row.last_updated_display,
            ]
        ).casefold()
        if all(term in haystack for term in terms):
            filtered.append(row)
    return filtered


def filter_beatmapset_rows(rows: Sequence[BeatmapRow], beatmap_id: int | None) -> list[BeatmapRow]:
    if beatmap_id is None:
        return list(rows)
    return [row for row in rows if row.beatmap_id == beatmap_id]


def collection_to_summary(collection: Collection) -> CollectionSummary:
    return CollectionSummary(name=collection.name, count=collection.count)


class MainWindowViewModel:
    """State holder for the main window."""

    def __init__(self, collection_service: CollectionService) -> None:
        self._collection_service = collection_service
        self._collections: list[CollectionSummary] = []
        self._beatmap_rows: list[BeatmapRow] = []
        self._current_collection_name: str | None = None
        self._current_detail: BeatmapRow | None = None

    @property
    def collections(self) -> list[CollectionSummary]:
        return list(self._collections)

    @property
    def beatmap_rows(self) -> list[BeatmapRow]:
        return list(self._beatmap_rows)

    @property
    def current_collection_name(self) -> str | None:
        return self._current_collection_name

    @property
    def current_detail(self) -> BeatmapRow | None:
        return self._current_detail

    def reload_collections(self, select_name: str | None = None) -> None:
        collections = self._collection_service.get_all_collections()
        self._collections = [collection_to_summary(collection) for collection in collections]
        self._collections.sort(key=lambda collection: collection.name.casefold())
        available_names = [collection.name for collection in self._collections]

        target_name = select_name
        if target_name not in available_names:
            if self._current_collection_name in available_names:
                target_name = self._current_collection_name
            else:
                target_name = available_names[0] if available_names else None

        self._current_collection_name = target_name
        if target_name is None:
            self._beatmap_rows = []
            self._current_detail = None
            return

        self.load_collection(target_name)

    def load_collection(self, name: str) -> None:
        collection = self._collection_service.get_collection(name)
        if collection is None:
            self._current_collection_name = None
            self._beatmap_rows = []
            self._current_detail = None
            return

        found_beatmaps, _missing_hashes = self._collection_service.get_beatmaps(name)
        found_by_hash = {beatmap.md5_hash: beatmap for beatmap in found_beatmaps}
        rows: list[BeatmapRow] = []
        for md5_hash in collection.hashes:
            beatmap = found_by_hash.get(md5_hash)
            if beatmap is None:
                rows.append(missing_beatmap_row(md5_hash))
            else:
                rows.append(beatmap_to_row(beatmap))

        self._current_collection_name = name
        self._beatmap_rows = rows
        self._current_detail = rows[0] if rows else None

    def select_collection(self, name: str) -> None:
        self.load_collection(name)

    def select_beatmap(self, md5_hash: str | None) -> None:
        if md5_hash is None:
            self._current_detail = None
            return

        for row in self._beatmap_rows:
            if row.md5_hash == md5_hash:
                self._current_detail = row
                return
        self._current_detail = None

    def create_collection(self, name: str) -> None:
        collection_name = name.strip()
        if not collection_name:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        self._collection_service.create_collection(collection_name, [])
        self.reload_collections(collection_name)

    def rename_collection(self, old_name: str, new_name: str) -> None:
        collection_name = new_name.strip()
        if not collection_name:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        result = self._collection_service.rename_collection(old_name, collection_name)
        if result is None:
            raise ValueError(tr("main.dialog.prompt.select_one_collection"))
        self.reload_collections(collection_name)

    def delete_collections(self, names: Sequence[str]) -> None:
        target_names = [name for name in dict.fromkeys(names) if name.strip()]
        if not target_names:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        for name in target_names:
            self._collection_service.delete_collection(name)
        self.reload_collections()

    def merge_collections(self, source_names: Sequence[str], new_name: str) -> None:
        target_name = new_name.strip()
        if not target_name:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        result = self._collection_service.merge_collections(source_names, target_name)
        if result is None:
            raise ValueError(tr("main.dialog.prompt.select_two_collections"))
        self.reload_collections(target_name)

    def export_collections(self, names: Sequence[str], output_path: str) -> None:
        target_names = [name for name in dict.fromkeys(names) if name.strip()]
        if not target_names:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        self._collection_service.export_collections(list(target_names), output_path)

    def remove_beatmaps_from_current_collection(self, hashes: Sequence[str]) -> None:
        collection_name = self._current_collection_name
        if collection_name is None:
            raise ValueError(tr("main.dialog.prompt.select_one_collection_for_remove"))

        target_hashes = [md5_hash for md5_hash in dict.fromkeys(hashes) if md5_hash.strip()]
        if not target_hashes:
            raise ValueError(tr("main.dialog.prompt.select_beatmaps"))

        result = self._collection_service.remove_beatmaps(collection_name, target_hashes)
        if result is None:
            raise ValueError(tr("main.dialog.prompt.select_one_collection_for_remove"))
        self.reload_collections(collection_name)


class BeatmapListViewModel:
    """State holder for the beatmap list window."""

    def __init__(self, search_service: SearchService, collection_service: CollectionService) -> None:
        self._search_service = search_service
        self._collection_service = collection_service
        self._results: list[BeatmapRow] = []
        self._selected_hashes: list[str] = []
        self._current_detail: BeatmapRow | None = None
        self._current_query: str = ""

    @property
    def results(self) -> list[BeatmapRow]:
        return list(self._results)

    @property
    def selected_hashes(self) -> list[str]:
        return list(self._selected_hashes)

    @property
    def current_detail(self) -> BeatmapRow | None:
        return self._current_detail

    @property
    def current_query(self) -> str:
        return self._current_query

    def search(self, query: str, limit: int | None = None) -> None:
        self._current_query = query
        beatmaps = self._search_service.search(query, limit=limit)
        self._results = [beatmap_to_row(beatmap) for beatmap in beatmaps]
        self._selected_hashes = [self._results[0].md5_hash] if self._results else []
        self._current_detail = self._results[0] if self._results else None

    def select_hashes(self, hashes: Sequence[str]) -> None:
        target_hashes = [md5_hash for md5_hash in dict.fromkeys(hashes)]
        self._selected_hashes = target_hashes
        if not target_hashes:
            self._current_detail = None
            return

        for row in self._results:
            if row.md5_hash == target_hashes[0]:
                self._current_detail = row
                return
        self._current_detail = None

    def add_selected_to_collections(self, collection_names: Sequence[str]) -> None:
        selected_hashes = self._selected_hashes or ([self._current_detail.md5_hash] if self._current_detail else [])
        target_names = [name for name in dict.fromkeys(collection_names) if name.strip()]
        if not selected_hashes:
            raise ValueError(tr("main.dialog.prompt.select_beatmaps"))
        if not target_names:
            raise ValueError(tr("main.dialog.prompt.select_collection_before_action"))

        for collection_name in target_names:
            self._collection_service.add_beatmaps_to_collection(collection_name, selected_hashes)


class CollectionPickerViewModel:
    """State holder for the collection picker dialog."""

    def __init__(self, collection_service: CollectionService) -> None:
        self._collection_service = collection_service
        self._target_hashes: list[str] = []
        self._choices: list[CollectionChoice] = []

    @property
    def target_hashes(self) -> list[str]:
        return list(self._target_hashes)

    @property
    def choices(self) -> list[CollectionChoice]:
        return list(self._choices)

    @property
    def has_multiple_targets(self) -> bool:
        return len(self._target_hashes) > 1

    def load(self, target_hashes: Sequence[str]) -> None:
        self._target_hashes = [md5_hash for md5_hash in dict.fromkeys(target_hashes) if md5_hash.strip()]
        self._choices = []
        collections = self._collection_service.get_all_collections()
        for collection in collections:
            checked = False
            if len(self._target_hashes) == 1:
                checked = self._collection_service.is_beatmap_in_collection(collection.name, self._target_hashes[0])
            self._choices.append(CollectionChoice(name=collection.name, count=collection.count, checked=checked))

    def set_checked(self, collection_name: str, checked: bool) -> None:
        for choice in self._choices:
            if choice.name == collection_name:
                choice.checked = checked
                return

    def checked_names(self) -> list[str]:
        return [choice.name for choice in self._choices if choice.checked]

    def apply_selection(self, collection_names: Sequence[str]) -> list[str]:
        target_names = [name for name in dict.fromkeys(collection_names) if name.strip()]
        if not target_names or not self._target_hashes:
            return []

        updated: list[str] = []
        for collection_name in target_names:
            result = self._collection_service.add_beatmaps_to_collection(collection_name, self._target_hashes)
            if result is not None:
                updated.append(collection_name)
        return updated
