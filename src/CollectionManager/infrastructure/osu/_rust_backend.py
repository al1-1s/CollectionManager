from __future__ import annotations

import os
from types import SimpleNamespace
from typing import Any

_FORCE_PYTHON_PARSER = os.getenv("COLLECTION_MANAGER_USE_PYTHON_PARSER", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}

try:
    if _FORCE_PYTHON_PARSER:
        raise ImportError("Rust parser disabled by environment.")

    from collection_manager_rust_parser import (  # type: ignore[import-not-found]
        BackendParseError as RustBackendParseError,
        parse_collection_db_bytes as parse_collection_db_bytes_rust,
        parse_osu_db_bytes as parse_osu_db_bytes_rust,
    )
except ImportError:
    RustBackendParseError = None
    parse_collection_db_bytes_rust = None
    parse_osu_db_bytes_rust = None


def rust_backend_available() -> bool:
    return parse_osu_db_bytes_rust is not None and parse_collection_db_bytes_rust is not None


def to_namespace(value: Any) -> Any:
    if isinstance(value, dict):
        return SimpleNamespace(**{key: to_namespace(item) for key, item in value.items()})
    if isinstance(value, list):
        return [to_namespace(item) for item in value]
    if isinstance(value, tuple):
        return tuple(to_namespace(item) for item in value)
    return value


def rust_backend_error_message(exc: BaseException) -> str:
    args = getattr(exc, "args", ())
    if args and isinstance(args[0], str):
        return args[0]
    return str(exc)


def rust_backend_error_pos(exc: BaseException) -> int | None:
    args = getattr(exc, "args", ())
    if len(args) >= 2 and isinstance(args[1], int):
        return args[1]
    return None
