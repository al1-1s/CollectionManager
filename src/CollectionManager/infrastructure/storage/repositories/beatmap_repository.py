"""Repository for beatmap persistence and queries."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict
from datetime import datetime, timezone

from sqlalchemy import and_, or_
from sqlalchemy import func
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import select
from typing import Any, cast

from src.CollectionManager.domain.model.beatmap import Beatmap
from src.CollectionManager.infrastructure.exceptions.repository import RepositoryNotFoundError

from ..models import BeatmapRecord
from ..sqlite_db import SqliteDB


class BeatmapRepository:
	"""Persist and query beatmaps by md5 hash."""

	def __init__(self, db: SqliteDB) -> None:
		self._db = db

	def save(self, beatmap: Beatmap) -> Beatmap:
		"""Insert or replace a single beatmap."""

		record = BeatmapRecord.from_domain(beatmap)
		with self._db.beatmap_session() as session:
			session.merge(record)
			session.commit()
		return beatmap

	def save_many(self, beatmaps: Iterable[Beatmap]) -> list[Beatmap]:
		"""Insert or replace multiple beatmaps."""
		results = list(beatmaps)
		if not results:
			return []

		rows = [asdict(beatmap) for beatmap in results]
		table = cast(Any, BeatmapRecord).__table__
		statement = sqlite_insert(table)
		update_columns = {
			column.name: getattr(statement.excluded, column.name)
			for column in table.columns
			if column.name != "md5_hash"
		}
		upsert = statement.on_conflict_do_update(
			index_elements=[table.c.md5_hash],
			set_=update_columns,
		)

		with self._db.beatmap_session() as session:
			session.execute(upsert, rows)
			session.commit()
		return results

	def get(self, md5_hash: str) -> Beatmap:
		"""Retrieve a beatmap by its md5 hash."""
		with self._db.beatmap_session() as session:
			record = session.get(BeatmapRecord, md5_hash)
			if record is None:
				raise RepositoryNotFoundError(f"Beatmap with hash '{md5_hash}' does not exist.")
			return record.to_domain()

	def count(self) -> int:
		"""Return the number of stored beatmaps."""

		with self._db.beatmap_session() as session:
			return int(session.exec(select(func.count()).select_from(BeatmapRecord)).one())

	def get_many(self, hashes: Sequence[str]) -> tuple[list[Beatmap], list[str]]:
		"""Retrieve multiple beatmaps by their md5 hashes.
		
		Returns a tuple of (found_beatmaps, missing_hashes).
		"""
		if not hashes:
			return [], []

		with self._db.beatmap_session() as session:
			records = session.exec(
				select(BeatmapRecord).where(cast(Any, BeatmapRecord.md5_hash).in_(hashes))
			).all()
			hash_set = set(hashes)
			record_by_hash = {record.md5_hash: record.to_domain() for record in records if record.md5_hash in hash_set}
			found = [record_by_hash[hash_value] for hash_value in hashes if hash_value in record_by_hash]
			missing = [hash_value for hash_value in hashes if hash_value not in record_by_hash]
			return found, missing

	def _match_text(self, field_value: str | None, needle: str) -> bool:
		"""Case-insensitive substring match. If field_value is None or empty, returns False."""
		if not field_value:
			return False
		return needle in field_value.casefold()

	def _compare(self, left: Any, op: str, right: Any) -> bool:
		"""Compare left and right using the given operator. Supported operators: =, !=, <, >, <=, >=, :, ==. Returns False if the operator is unknown or if any error occurs during comparison."""
		try:
			if op == "=" or op == ":" or op == "==":
				return left == right
			if op == "!=":
				return left != right
			if op == "<":
				return left < right
			if op == ">":
				return left > right
			if op == "<=":
				return left <= right
			if op == ">=":
				return left >= right
		except Exception:
			return False
		return False

	def _status_to_int(self, status: Any) -> int | None:
		"""Convert a ranked status string or integer to its corresponding integer code. Returns None if the input is None or if the status is unrecognized."""	
		if status is None:
			return None
		if isinstance(status, int):
			return status
		s = str(status).casefold()
		mapping = {
			"unknown": 0,
			"unsubmitted": 1,
			"pending": 2,
			"wip": 2,
			"graveyard": 2,
			"unused": 3,
			"ranked": 4,
			"approved": 5,
			"qualified": 6,
			"loved": 7,
			"r": 4,
			"a": 5,
			"p": 2,
			"n": 3,
			"u": 1,
			"l": 7,
		}
		return mapping.get(s)

	def _mode_to_int(self, mode: Any) -> int | None:
		"""Convert a game mode string or integer to its corresponding integer code. Returns None if the input is None or if the mode is unrecognized."""
		if mode is None:
			return None
		if isinstance(mode, int):
			return mode
		s = str(mode).casefold()
		mapping = {"osu": 0, "taiko": 1, "catch": 2, "mania": 3, "o": 0, "t": 1, "c": 2, "m": 3}
		return mapping.get(s)

	def search(
		self,
		keyword: str = "",
		limit: int | None = None,
		filters: dict | None = None,
	) -> list[Beatmap]:
		"""Search beatmaps.

		Supports structured `filters` mapping field -> value or (op, value).
		If `filters` is None, uses keyword substring search.
		Supported filter fields: artist, creator, title, difficulty, ar, cs, od, hp,
		star/stars (maps to no_mod_sr), length, drain, mode, status, played, unplayed.
		"""

		needle = keyword.strip().casefold() if keyword else ""

		with self._db.beatmap_session() as session:
			now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
			query = select(BeatmapRecord)

			for key, cond in (filters or {}).items():
				if isinstance(cond, tuple) and len(cond) == 2:
					op, val = cond
				else:
					op, val = "=", cond

				if key in ("artist", "creator", "title", "difficulty", "tags", "source"):
					field = cast(Any, getattr(BeatmapRecord, key))
					needle_value = str(val)
					if op in ("=", ":", "=="):
						query = query.where(field.ilike(f"%{needle_value}%"))
					elif op == "!=":
						query = query.where(~field.ilike(f"%{needle_value}%"))
					else:
						return []
				elif key in ("ar", "cs", "od", "hp", "star", "stars"):
					field = cast(Any, getattr(BeatmapRecord, "no_mod_sr" if key in ("star", "stars") else key))
					try:
						target = float(cast(Any, val))
					except Exception:
						return []
					if op in ("=", ":", "=="):
						query = query.where(field == target)
					elif op == "!=":
						query = query.where(field != target)
					elif op == "<":
						query = query.where(field < target)
					elif op == ">":
						query = query.where(field > target)
					elif op == "<=":
						query = query.where(field <= target)
					elif op == ">=":
						query = query.where(field >= target)
					else:
						return []
				elif key in ("length", "drain"):
					field = cast(Any, getattr(BeatmapRecord, "total_time" if key == "length" else "drain_time"))
					try:
						target = int(cast(Any, val))
					except Exception:
						return []
					if op in ("=", ":", "=="):
						query = query.where(field == target)
					elif op == "!=":
						query = query.where(field != target)
					elif op == "<":
						query = query.where(field < target)
					elif op == ">":
						query = query.where(field > target)
					elif op == "<=":
						query = query.where(field <= target)
					elif op == ">=":
						query = query.where(field >= target)
					else:
						return []
				elif key == "mode":
					mode_int = self._mode_to_int(val)
					if mode_int is None:
						return []
					if op in ("=", ":", "=="):
						query = query.where(cast(Any, BeatmapRecord.mode) == mode_int)
					elif op == "!=":
						query = query.where(cast(Any, BeatmapRecord.mode) != mode_int)
					else:
						return []
				elif key == "status":
					status_int = self._status_to_int(val)
					if status_int is None:
						return []
					if op in ("=", ":", "=="):
						query = query.where(cast(Any, BeatmapRecord.ranked_status) == status_int)
					elif op == "!=":
						query = query.where(cast(Any, BeatmapRecord.ranked_status) != status_int)
					else:
						return []
				elif key == "unplayed":
					if bool(val):
						query = query.where(cast(Any, BeatmapRecord.is_unplayed) == True)
				elif key == "played":
					try:
						target_days = float(cast(Any, val))
					except Exception:
						return []
					threshold_ms = int(now_ms - (target_days * 24 * 60 * 60 * 1000))
					if op in ("=", ":", "=="):
						query = query.where(cast(Any, BeatmapRecord.last_played) == threshold_ms)
					elif op == "!=":
						query = query.where(cast(Any, BeatmapRecord.last_played) != threshold_ms)
					elif op == "<":
						query = query.where(cast(Any, BeatmapRecord.last_played) > threshold_ms)
					elif op == "<=":
						query = query.where(cast(Any, BeatmapRecord.last_played) >= threshold_ms)
					elif op == ">":
						query = query.where(cast(Any, BeatmapRecord.last_played) < threshold_ms)
					elif op == ">=":
						query = query.where(cast(Any, BeatmapRecord.last_played) <= threshold_ms)
					else:
						return []

			if needle:
				keyword_terms = [term for term in needle.split() if term]
				keyword_clauses = []
				for term in keyword_terms:
					keyword_clauses.append(
						or_(
							cast(Any, BeatmapRecord.artist).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.artist_unicode).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.title).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.title_unicode).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.creator).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.difficulty).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.tags).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.source).ilike(f"%{term}%"),
							cast(Any, BeatmapRecord.md5_hash).ilike(f"%{term}%"),
						)
					)

				if keyword_clauses:
					query = query.where(and_(*keyword_clauses))

			if limit is not None:
				query = query.limit(limit)

			records = session.exec(query).all()
			return [record.to_domain() for record in records]

	def delete(self, md5_hash: str) -> None:
		"""Delete a beatmap by its md5 hash."""
		with self._db.beatmap_session() as session:
			record = session.get(BeatmapRecord, md5_hash)
			if record is None:
				raise RepositoryNotFoundError(f"Beatmap with hash '{md5_hash}' does not exist.")
			session.delete(record)
			session.commit()

	def exists(self, md5_hash: str) -> bool:
		"""Check if a beatmap with the given md5 hash exists."""
		with self._db.beatmap_session() as session:
			return session.get(BeatmapRecord, md5_hash) is not None