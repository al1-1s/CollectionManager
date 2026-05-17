"""SQLModel ORM definitions for beatmaps and collections."""

from __future__ import annotations

from dataclasses import asdict
from typing import ClassVar, Iterable

from sqlmodel import Field, SQLModel

from src.CollectionManager.domain.model import Beatmap, Collection


class BeatmapRecord(SQLModel, table=True):
	"""Persisted beatmap row keyed by md5 hash."""

	__tablename__: ClassVar[str] = "beatmaps"

	md5_hash: str = Field(primary_key=True, index=True)
	artist: str = Field(default="")
	artist_unicode: str = Field(default="")
	title: str = Field(default="")
	title_unicode: str = Field(default="")
	creator: str = Field(default="")
	difficulty: str = Field(default="")
	audio_file_name: str = Field(default="")
	osu_file_name: str = Field(default="")
	ar: float = Field(default=0.0)
	cs: float = Field(default=0.0)
	hp: float = Field(default=0.0)
	od: float = Field(default=0.0)
	total_time: int = Field(default=0)
	difficulty_id: int = Field(default=0)
	beatmap_id: int = Field(default=0)
	mode: int = Field(default=0)
	tags: str = Field(default="")
	source: str = Field(default="")
	no_mod_sr: float = Field(default=0.0)
	ranked_status: int = Field(default=0)
	last_modified: int = Field(default=0)
	preview_time: int = Field(default=0)
	folder_name: str = Field(default="")

	@classmethod
	def from_domain(cls, beatmap: Beatmap) -> "BeatmapRecord":
		return cls(**asdict(beatmap))

	def to_domain(self) -> Beatmap:
		return Beatmap(**self.model_dump())


class CollectionRecord(SQLModel, table=True):
	"""Persisted collection metadata."""

	__tablename__: ClassVar[str] = "collections"

	name: str = Field(primary_key=True, index=True)
	count: int = Field(default=0)

	@classmethod
	def from_domain(cls, value: Collection) -> "CollectionRecord":
		return cls(name=value.name, count=len(value.hashes))

	def to_domain(self, hashes: Iterable[str]) -> Collection:
		hash_list = list(hashes)
		return Collection(name=self.name, count=len(hash_list), hashes=hash_list)


class CollectionBeatmapRecord(SQLModel, table=True):
	"""Many-to-many relation between a collection and beatmap hashes."""

	__tablename__: ClassVar[str] = "collection_beatmaps"

	collection_name: str = Field(primary_key=True, index=True)
	beatmap_hash: str = Field(primary_key=True, index=True)
	position: int = Field(default=0, index=True)

	@classmethod
	def from_pair(cls, collection_name: str, beatmap_hash: str, position: int) -> "CollectionBeatmapRecord":
		return cls(collection_name=collection_name, beatmap_hash=beatmap_hash, position=position)