"""Service-layer exception hierarchy."""

from __future__ import annotations

from pathlib import Path


class ServiceError(Exception):
	"""Base exception for service-layer failures."""


class ServiceValidationError(ServiceError):
	"""Raised when service-level validation fails."""


class ServiceConflictError(ServiceError):
	"""Raised when a requested change conflicts with existing data."""


class ServiceNotFoundError(ServiceError):
	"""Raised when a requested domain object does not exist."""


class ServiceDataError(ServiceError):
	"""Raised when lower-layer data or filesystem issues are expected and actionable."""


class ServiceOperationError(ServiceError):
	"""Raised when an unexpected lower-layer failure reaches the service boundary."""


class CollectionAlreadyExistsError(ServiceConflictError):
	"""Raised when a collection name is already in use."""

	def __init__(self, collection_name: str):
		super().__init__(f"Collection '{collection_name}' already exists.")
		self.collection_name = collection_name


class CollectionServiceNotFoundError(ServiceNotFoundError):
	"""Raised when a collection requested through the service layer is missing."""

	def __init__(self, collection_name: str):
		super().__init__(f"Collection '{collection_name}' does not exist.")
		self.collection_name = collection_name


class BeatmapServiceNotFoundError(ServiceNotFoundError):
	"""Raised when a beatmap requested through the service layer is missing."""

	def __init__(self, md5_hash: str):
		super().__init__(f"Beatmap with hash '{md5_hash}' does not exist.")
		self.md5_hash = md5_hash


class CollectionExportError(ServiceDataError):
	"""Raised when exporting collections fails for an expected data or IO reason."""

	def __init__(self, output_path: str | Path, detail: str):
		path = Path(output_path)
		super().__init__(f"Failed to export collections to '{path}': {detail}")
		self.output_path = path


class DataImportError(ServiceDataError):
	"""Raised when bootstrap import/load input is missing or malformed."""

	def __init__(self, source_path: str | Path, detail: str):
		path = Path(source_path)
		super().__init__(f"Failed to import data from '{path}': {detail}")
		self.source_path = path


class CachedBeatmapDatabaseNotFoundError(ServiceDataError):
	"""Raised when startup requests cached beatmaps but no cache exists."""

	def __init__(self, database_path: str | Path):
		path = Path(database_path)
		super().__init__(f"No cached beatmap database found at '{path}'.")
		self.database_path = path