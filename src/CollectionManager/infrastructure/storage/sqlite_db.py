"""SQLite connection helpers for the storage layer.

This module owns engine/session creation only. Repositories use these helpers
to read and write ORM models.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from .models import BeatmapRecord, CollectionBeatmapRecord, CollectionRecord


@dataclass(frozen=True)
class SqlitePaths:
	beatmap_db: Path
	collection_meta_db: Path
	collection_relation_db: Path


class SqliteDB:
	"""Provide SQLite engines and sessions for each logical database."""

	def __init__(self, paths: SqlitePaths | None = None, echo: bool = False) -> None:
		base_dir = Path.cwd() / "data"
		self._paths = paths or SqlitePaths(
			beatmap_db=base_dir / "beatmaps.db",
			collection_meta_db=base_dir / "collections.db",
			collection_relation_db=base_dir / "collection_beatmaps.db",
		)

		self._echo = echo
		for path in self._paths.__dict__.values():
			path.parent.mkdir(parents=True, exist_ok=True)

		self._create_engines()
		self.create_schema()

	def _create_engines(self) -> None:
		self._beatmap_engine = create_engine(f"sqlite:///{self._paths.beatmap_db}", echo=self._echo)
		self._collection_meta_engine = create_engine(f"sqlite:///{self._paths.collection_meta_db}", echo=self._echo)
		self._collection_relation_engine = create_engine(
			f"sqlite:///{self._paths.collection_relation_db}",
			echo=self._echo,
		)

	def create_schema(self) -> None:
		"""Create all known tables in their matching SQLite databases."""

		SQLModel.metadata.create_all(self._beatmap_engine, tables=[BeatmapRecord.__table__])
		SQLModel.metadata.create_all(self._collection_meta_engine, tables=[CollectionRecord.__table__])
		SQLModel.metadata.create_all(
			self._collection_relation_engine,
			tables=[CollectionBeatmapRecord.__table__],
		)

	@contextmanager
	def beatmap_session(self) -> Iterator[Session]:
		with Session(self._beatmap_engine) as session:
			yield session

	@contextmanager
	def collection_meta_session(self) -> Iterator[Session]:
		with Session(self._collection_meta_engine) as session:
			yield session

	@contextmanager
	def collection_relation_session(self) -> Iterator[Session]:
		with Session(self._collection_relation_engine) as session:
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

	def dispose(self) -> None:
		"""Dispose all SQLite engines owned by this database wrapper."""

		self._beatmap_engine.dispose()
		self._collection_meta_engine.dispose()
		self._collection_relation_engine.dispose()