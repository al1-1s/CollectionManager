"""Map raw parser data to domain objects."""

from __future__ import annotations

from typing import Any

from src.CollectionManager.domain.model import Beatmap, Collection
from loguru import logger


def _get(raw: Any, key: str, default: Any = None) -> Any:
    if isinstance(raw, dict):
        return raw.get(key, default)
    return getattr(raw, key, default)


def map_beatmap(raw: Any) -> Beatmap:
    """Convert a parsed osu!.db beatmap entry into a domain Beatmap."""

    mode = int(_get(raw, "mode", -1))
    match mode:
        case 0:
            pair = _get(raw, "pair_std", []) or []
        case 1:
            pair = _get(raw, "pair_taiko", []) or []
        case 2:
            pair = _get(raw, "pair_catch", []) or []
        case 3:
            pair = _get(raw, "pair_mania", []) or []
        case _:
            raise ValueError(f"Unknown mode: {mode}")
    if not pair:
        logger.warning(f"No star rating pair found for beatmap with mode {mode} and hash {_get(raw, 'md5_hash', 'unknown')}")
        pair = [(0, 0.0)]
    no_mod_sr = pair[0][1]

    return Beatmap(
        artist=_get(raw, "artist", ""),
        artist_unicode=_get(raw, "artist_unicode", ""),
        title=_get(raw, "title", ""),
        title_unicode=_get(raw, "title_unicode", ""),
        creator=_get(raw, "creator", ""),
        difficulty=_get(raw, "difficulty", ""),
        audio_file_name=_get(raw, "audio_file_name", ""),
        md5_hash=_get(raw, "md5_hash", ""),
        osu_file_name=_get(raw, "osu_file_name", ""),
        ranked_status=int(_get(raw, "ranked_status", 0)),
        hit_circle_count=int(_get(raw, "hit_circle_count", 0)),
        slider_count=int(_get(raw, "slider_count", 0)),
        spinner_count=int(_get(raw, "spinner_count", 0)),
        last_modified=int(_get(raw, "last_modified", 0)),
        ar=float(_get(raw, "ar", 0.0)),
        cs=float(_get(raw, "cs", 0.0)),
        hp=float(_get(raw, "hp", 0.0)),
        od=float(_get(raw, "od", 0.0)),
        drain_time=int(_get(raw, "drain_time", 0)),
        total_time=int(_get(raw, "total_time", 0)),
        difficulty_id=int(_get(raw, "difficulty_id", 0)),
        beatmap_id=int(_get(raw, "beatmap_id", 0)),
        thread_id=int(_get(raw, "thread_id", 0)),
        mode=int(_get(raw, "mode", 0)),
        tags=_get(raw, "tags", ""),
        source=_get(raw, "source", ""),
        no_mod_sr=float(no_mod_sr),
        preview_time=int(_get(raw, "preview_time", 0)),
        is_unplayed=bool(_get(raw, "is_unplayed", False)),
        last_played=int(_get(raw, "last_played", 0)),
        is_osz2=bool(_get(raw, "is_osz2", False)),
        folder_name=_get(raw, "folder_name", ""),
        last_checked=int(_get(raw, "last_checked", 0)),
    )


def map_collection(raw: Any) -> Collection:
    """Convert a parsed collection.db entry into a domain Collection."""

    hashes = list(_get(raw, "map_hashes", []) or [])
    return Collection(
        name=_get(raw, "name", ""),
        count=int(_get(raw, "map_count", len(hashes))),
        hashes=hashes,
    )
