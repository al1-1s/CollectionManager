"""Repository for collection metadata and collection-beatmap relations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import delete, func, insert, update
from sqlmodel import select

from src.CollectionManager.domain.model import Collection
from src.CollectionManager.infrastructure.exceptions.repository import CollectionNotFoundError

from ..models import CollectionBeatmapRecord, CollectionRecord
from ..sqlite_db import SqliteDB


class CollectionRepository:
	"""Persist collections in two SQLite databases.

	Metadata lives in one database and the many-to-many mapping lives in
	another database, as requested.
	"""

	def __init__(self, db: SqliteDB) -> None:
		self._db = db

	def _load_collections(self, meta_records: Sequence[CollectionRecord]) -> list[Collection]:
		if not meta_records:
			return []

		names = [record.name for record in meta_records]
		with self._db.collection_session() as session:
			relation_records = session.exec(
				select(CollectionBeatmapRecord)
				.where(cast(Any, CollectionBeatmapRecord.collection_name).in_(names))
				.order_by(
					cast(Any, CollectionBeatmapRecord.collection_name),
					cast(Any, CollectionBeatmapRecord.position),
				)
			).all()

		hashes_by_name: dict[str, list[str]] = {}
		for relation_record in relation_records:
			hashes_by_name.setdefault(relation_record.collection_name, []).append(relation_record.beatmap_hash)

		return [meta_record.to_domain(hashes_by_name.get(meta_record.name, [])) for meta_record in meta_records]

	def create(self, value: Collection) -> Collection:
		"""Create a collection and store its initial hash ordering."""
		with self._db.collection_session() as session:
			session.merge(CollectionRecord.from_domain(value))
			for record in session.exec(
				select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == value.name)
			).all():
				session.delete(record)
			for position, beatmap_hash in enumerate(value.hashes):
				session.add(
					CollectionBeatmapRecord.from_pair(value.name, beatmap_hash, position)
				)
			session.commit()
		return value

	def create_many(self, values: Sequence[Collection]) -> list[Collection]:
		"""Create multiple collections and all of their relations in one transaction."""
		results = list(values)
		if not results:
			return []

		meta_rows = [{"name": value.name} for value in results]
		relation_rows = [
			{
				"collection_name": value.name,
				"beatmap_hash": beatmap_hash,
				"position": position,
			}
			for value in results
			for position, beatmap_hash in enumerate(value.hashes)
		]
		meta_table = cast(Any, CollectionRecord).__table__
		relation_table = cast(Any, CollectionBeatmapRecord).__table__

		with self._db.collection_session() as session:
			session.execute(insert(meta_table), meta_rows)
			if relation_rows:
				session.execute(insert(relation_table), relation_rows)
			session.commit()
		return results

	def delete(self, name: str) -> None:
		"""Delete a collection and all its beatmap associations."""
		with self._db.collection_session() as session:
			meta_record = session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)
			session.exec(
				delete(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
			)
			session.delete(meta_record)
			session.commit()

	def get(self, name: str) -> Collection:
		"""Retrieve a collection by name, including its beatmap hashes."""
		with self._db.collection_session() as session:
			meta_record = session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			relation_records = session.exec(
				select(CollectionBeatmapRecord)
				.where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
				.order_by(cast(Any, CollectionBeatmapRecord.position))
			).all()
			hashes = [record.beatmap_hash for record in relation_records]
			return meta_record.to_domain(hashes)

	def list(self) -> list[Collection]:
		"""List all collections."""
		with self._db.collection_session() as session:
			meta_records = session.exec(select(CollectionRecord)).all()
		return self._load_collections(meta_records)

	def search(self, query: str, limit: int | None = None) -> list[Collection]:
		"""Search collections by name using a case-insensitive substring match."""

		needle = query.strip().lower()
		statement = select(CollectionRecord).order_by(func.lower(cast(Any, CollectionRecord.name)))
		if needle:
			statement = statement.where(func.lower(cast(Any, CollectionRecord.name)).contains(needle))
		if limit is not None:
			statement = statement.limit(limit)

		with self._db.collection_session() as session:
			meta_records = session.exec(statement).all()
		return self._load_collections(meta_records)

	def count(self) -> int:
		"""Return the number of stored collections."""

		with self._db.collection_session() as session:
			return int(session.exec(select(func.count()).select_from(CollectionRecord)).one())

	def add_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
		"""Add beatmaps to a collection."""
		if not beatmap_hashes:
			return self.get(name)

		with self._db.collection_session() as session:
			meta_record = session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			existing = [
				record
				for record in session.exec(
					select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
				).all()
			]
			existing.sort(key=lambda record: record.position)
			known_hashes = {record.beatmap_hash for record in existing}
			ordered_hashes = [record.beatmap_hash for record in existing]
			position = len(existing)
			for beatmap_hash in beatmap_hashes:
				if beatmap_hash in known_hashes:
					continue
				session.add(CollectionBeatmapRecord.from_pair(name, beatmap_hash, position))
				known_hashes.add(beatmap_hash)
				ordered_hashes.append(beatmap_hash)
				position += 1
			session.commit()
			return meta_record.to_domain(ordered_hashes)

	def remove_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
		"""Remove beatmaps from a collection and return the updated collection."""
		if not beatmap_hashes:
			return self.get(name)

		with self._db.collection_session() as session:
			meta_record = session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			for record in session.exec(
				select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
			).all():
				if record.beatmap_hash in beatmap_hashes:
					session.delete(record)
			session.flush()

			remaining = [
				record
				for record in session.exec(
					select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
				).all()
			]
			remaining.sort(key=lambda record: record.position)
			for position, record in enumerate(remaining):
				record.position = position
				session.add(record)
			session.commit()
			return meta_record.to_domain([record.beatmap_hash for record in remaining])

	def exists(self, name: str) -> bool:
		"""Check if a collection with the given name exists."""
		with self._db.collection_session() as session:
			return session.get(CollectionRecord, name) is not None

	def existing_names(self, names: Sequence[str]) -> set[str]:
		"""Return the subset of collection names that already exist."""
		unique_names = list(dict.fromkeys(name for name in names if name))
		if not unique_names:
			return set()

		with self._db.collection_session() as session:
			rows = session.exec(
				select(CollectionRecord.name).where(cast(Any, CollectionRecord.name).in_(unique_names))
			).all()
			return set(rows)

	def rename(self, old_name: str, new_name: str) -> Collection:
		"""Rename a collection and return the updated value."""
		with self._db.collection_session() as session:
			old_record = session.get(CollectionRecord, old_name)
			if old_record is None:
				raise CollectionNotFoundError(f"Collection '{old_name}' does not exist.", old_name)

			old_record.name = new_name
			session.add(old_record)
			session.exec(
				update(CollectionBeatmapRecord)
				.where(cast(Any, CollectionBeatmapRecord.collection_name) == old_name)
				.values(collection_name=new_name)
			)
			session.commit()

			relation_records = session.exec(
				select(CollectionBeatmapRecord)
				.where(cast(Any, CollectionBeatmapRecord.collection_name) == new_name)
				.order_by(cast(Any, CollectionBeatmapRecord.position))
			).all()
			return old_record.to_domain([record.beatmap_hash for record in relation_records])

	def is_beatmap_in_collection(self, collection_name: str, beatmap_hash: str) -> bool:
		"""Check if a beatmap hash is part of a collection."""
		with self._db.collection_session() as session:
			record = session.exec(
				select(CollectionBeatmapRecord).where(
					cast(Any, CollectionBeatmapRecord.collection_name) == collection_name,
					cast(Any, CollectionBeatmapRecord.beatmap_hash) == beatmap_hash
				)
			).first()
			return record is not None