"""UI-layer exception hierarchy."""

from __future__ import annotations

from loguru import logger

from src.CollectionManager.domain.exceptions import ServiceError


class ViewModelError(Exception):
	"""Base exception for expected UI/viewmodel failures."""


class ViewModelValidationError(ViewModelError):
	"""Raised when viewmodel-level validation fails before calling services."""


def resolve_ui_error_message(exc: Exception, unexpected_message: str, *, log_context: str) -> str:
	"""Map UI-facing exceptions to a user-visible message and log unexpected failures."""

	if isinstance(exc, (ServiceError, ViewModelError)):
		return str(exc)
	logger.exception(log_context)
	return unexpected_message