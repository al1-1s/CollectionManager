"""Repository for collection metadata and collection-beatmap relations."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, cast

from sqlalchemy import func
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

	def create(self, value: Collection) -> Collection:
		"""Create a collection and store its initial hash ordering."""
		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			meta_session.merge(CollectionRecord.from_domain(value))
			for record in relation_session.exec(
				select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == value.name)
			).all():
				relation_session.delete(record)
			for position, beatmap_hash in enumerate(value.hashes):
				relation_session.add(
					CollectionBeatmapRecord.from_pair(value.name, beatmap_hash, position)
				)
			meta_session.commit()
			relation_session.commit()
		return value

	def delete(self, name: str) -> None:
		"""Delete a collection and all its beatmap associations."""
		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			meta_record = meta_session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)
			meta_session.delete(meta_record)
			for record in relation_session.exec(
				select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
			).all():
				relation_session.delete(record)
			meta_session.commit()
			relation_session.commit()

	def get(self, name: str) -> Collection:
		"""Retrieve a collection by name, including its beatmap hashes."""
		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			meta_record = meta_session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			relation_records = relation_session.exec(
				select(CollectionBeatmapRecord)
				.where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
				.order_by(cast(Any, CollectionBeatmapRecord.position))
			).all()
			relation_records = sorted(relation_records, key=lambda record: record.position)
			hashes = [record.beatmap_hash for record in relation_records]
			return meta_record.to_domain(hashes)

	def list(self) -> list[Collection]:
		"""List all collections."""
		with self._db.collection_meta_session() as meta_session:
			meta_records = meta_session.exec(select(CollectionRecord)).all()

		if not meta_records:
			return []

		with self._db.collection_relation_session() as relation_session:
			relation_records = relation_session.exec(
				select(CollectionBeatmapRecord).where(
					cast(Any, CollectionBeatmapRecord.collection_name).in_([record.name for record in meta_records])
				)
			).all()

		hashes_by_name: dict[str, list[tuple[int, str]]] = {}
		for relation_record in relation_records:
			hashes_by_name.setdefault(relation_record.collection_name, []).append(
				(relation_record.position, relation_record.beatmap_hash)
			)

		collections: list[Collection] = []
		for meta_record in meta_records:
			ordered_hashes = [
				hash_value
				for _, hash_value in sorted(hashes_by_name.get(meta_record.name, []), key=lambda item: item[0])
			]
			collections.append(meta_record.to_domain(ordered_hashes))
		return collections

	def count(self) -> int:
		"""Return the number of stored collections."""

		with self._db.collection_meta_session() as meta_session:
			return int(meta_session.exec(select(func.count()).select_from(CollectionRecord)).one())

	def add_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
		"""Add beatmaps to a collection."""
		if not beatmap_hashes:
			return self.get(name)

		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			meta_record = meta_session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			existing = [
				record
				for record in relation_session.exec(
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
				relation_session.add(CollectionBeatmapRecord.from_pair(name, beatmap_hash, position))
				known_hashes.add(beatmap_hash)
				ordered_hashes.append(beatmap_hash)
				position += 1
			meta_record.count = len(ordered_hashes)
			meta_session.add(meta_record)
			meta_session.commit()
			relation_session.commit()
			return meta_record.to_domain(ordered_hashes)

	def remove_beatmaps(self, name: str, beatmap_hashes: Sequence[str]) -> Collection:
		"""Remove beatmaps from a collection and return the updated collection."""
		if not beatmap_hashes:
			return self.get(name)

		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			meta_record = meta_session.get(CollectionRecord, name)
			if meta_record is None:
				raise CollectionNotFoundError(f"Collection '{name}' does not exist.", name)

			for record in relation_session.exec(
				select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
			).all():
				if record.beatmap_hash in beatmap_hashes:
					relation_session.delete(record)
			relation_session.commit()

			remaining = [
				record
				for record in relation_session.exec(
					select(CollectionBeatmapRecord).where(cast(Any, CollectionBeatmapRecord.collection_name) == name)
				).all()
			]
			remaining.sort(key=lambda record: record.position)
			for position, record in enumerate(remaining):
				record.position = position
				relation_session.add(record)
			meta_record.count = len(remaining)
			meta_session.add(meta_record)
			meta_session.commit()
			relation_session.commit()
			return meta_record.to_domain([record.beatmap_hash for record in remaining])

	def exists(self, name: str) -> bool:
		"""Check if a collection with the given name exists."""
		with self._db.collection_meta_session() as meta_session:
			return meta_session.get(CollectionRecord, name) is not None

	def rename(self, old_name: str, new_name: str) -> Collection:
		"""Rename a collection and return the updated value."""
		with self._db.collection_meta_session() as meta_session, self._db.collection_relation_session() as relation_session:
			old_record = meta_session.get(CollectionRecord, old_name)
			if old_record is None:
				raise CollectionNotFoundError(f"Collection '{old_name}' does not exist.", old_name)

			# Update metadata
			old_record.name = new_name
			meta_session.add(old_record)
			meta_session.commit()

			# Update all relation records
			for record in relation_session.exec(select(CollectionBeatmapRecord)).all():
				if record.collection_name == old_name:
					record.collection_name = new_name
					relation_session.add(record)
			relation_session.commit()

			return self.get(new_name)

	def is_beatmap_in_collection(self, collection_name: str, beatmap_hash: str) -> bool:
		"""Check if a beatmap hash is part of a collection."""
		with self._db.collection_relation_session() as relation_session:
			record = relation_session.exec(
				select(CollectionBeatmapRecord).where(
					cast(Any, CollectionBeatmapRecord.collection_name) == collection_name,
					cast(Any, CollectionBeatmapRecord.beatmap_hash) == beatmap_hash
				)
			).first()
			return record is not None