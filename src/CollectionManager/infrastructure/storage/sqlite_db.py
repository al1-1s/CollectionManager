"""SQLite connection helpers for the storage layer.

This module owns engine/session creation only. Repositories use these helpers
to read and write ORM models.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .models import BeatmapRecord, CollectionBeatmapRecord, CollectionRecord


@dataclass(frozen=True)
class SqlitePaths:
	beatmap_db: Path
	collection_db: Path


class SqliteDB:
	"""Provide SQLite engines and sessions for each logical database."""

	def __init__(self, paths: SqlitePaths | None = None, echo: bool = False, create_schema: bool = True) -> None:
		base_dir = Path.cwd() / "data"
		self._paths = paths or SqlitePaths(
			beatmap_db=base_dir / "beatmaps.db",
			collection_db=base_dir / "collections.db",
		)

		self._echo = echo
		self._create_schema_on_init = create_schema
		for path in self._paths.__dict__.values():
			path.parent.mkdir(parents=True, exist_ok=True)

		self._create_engines()
		if self._create_schema_on_init:
			self.create_schema()

	@property
	def paths(self) -> SqlitePaths:
		"""Return the configured SQLite file paths."""

		return self._paths

	def _create_engines(self) -> None:
		self._beatmap_engine = create_engine(f"sqlite:///{self._paths.beatmap_db}", echo=self._echo)
		self._collection_engine = create_engine(f"sqlite:///{self._paths.collection_db}", echo=self._echo)

	def create_schema(self) -> None:
		"""Create all known tables in their matching SQLite databases."""

		SQLModel.metadata.create_all(self._beatmap_engine, tables=[BeatmapRecord.__table__])
		SQLModel.metadata.create_all(
			self._collection_engine,
			tables=[CollectionRecord.__table__, CollectionBeatmapRecord.__table__],
		)

	@contextmanager
	def beatmap_session(self) -> Iterator[Session]:
		with Session(self._beatmap_engine) as session:
			yield session

	@contextmanager
	def collection_session(self) -> Iterator[Session]:
		with Session(self._collection_engine) as session:
			yield session

	def reset(self) -> None:
		"""Delete existing database files and recreate empty schemas."""

		self.dispose()
		for path in self._paths.__dict__.values():
			if path.exists():
				path.unlink()
			path.parent.mkdir(parents=True, exist_ok=True)
		self._create_engines()
		self.create_schema()

	def has_cached_beatmaps(self) -> bool:
		"""Return True when a persisted beatmap database already contains data."""

		beatmap_db = self._paths.beatmap_db
		if not beatmap_db.exists():
			return False

		try:
			with sqlite3.connect(f"{beatmap_db.resolve().as_uri()}?mode=ro", uri=True) as connection:
				row = connection.execute("SELECT COUNT(*) FROM beatmaps").fetchone()
				return bool(row and row[0])
		except sqlite3.Error:
			return False

	def dispose(self) -> None:
		"""Dispose all SQLite engines owned by this database wrapper."""

		self._beatmap_engine.dispose()
		self._collection_engine.dispose()