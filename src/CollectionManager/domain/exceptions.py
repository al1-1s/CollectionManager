"""Service-layer exception hierarchy."""

from __future__ import annotations


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
