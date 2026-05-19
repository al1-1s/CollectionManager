from functools import lru_cache
from io import BytesIO
from typing import BinaryIO

from .data_types import String, Int
from construct import Struct, this, Array

from src.CollectionManager.infrastructure.exceptions.parser import ParseError

from ._rust_backend import (
    RustBackendParseError,
    parse_collection_db_bytes_rust,
    rust_backend_error_message,
    rust_backend_error_pos,
    to_namespace,
)

collectionEntry = Struct(
    "name" / String,
    "map_count" / Int, 
    "map_hashes" / Array(this.map_count, String)
)

collection = Struct(
    "version" / Int,
    "collection_count" / Int,
    "collections" / Array(this.collection_count, collectionEntry),
)


@lru_cache(maxsize=1)
def get_compiled_collection_db():
    return collection.compile()


def _legacy_parse_collection_db_bytes(data: bytes):
    return get_compiled_collection_db().parse_stream(BytesIO(data))


def _parse_collection_db_bytes(data: bytes):
    if parse_collection_db_bytes_rust is not None:
        return to_namespace(parse_collection_db_bytes_rust(data))
    return _legacy_parse_collection_db_bytes(data)


def _legacy_error_position(data: bytes) -> int:
    stream = BytesIO(data)
    try:
        get_compiled_collection_db().parse_stream(stream)
    except Exception:
        return stream.tell()
    return len(data)


def parse_collection_db_stream(stream: BinaryIO):
    data = stream.read()
    try:
        return _parse_collection_db_bytes(data)
    except Exception as exc:
        if RustBackendParseError is not None and isinstance(exc, RustBackendParseError):
            raise ValueError(rust_backend_error_message(exc)) from exc
        raise

def parse_collection_db(data: bytes):
    import binascii

    try:
        return _parse_collection_db_bytes(data)
    except Exception as e:
        pos = None
        if RustBackendParseError is not None and isinstance(e, RustBackendParseError):
            pos = rust_backend_error_pos(e)
        if pos is None:
            pos = _legacy_error_position(data)
        start = max(0, pos - 64)
        end = min(len(data), pos + 64)
        snippet = data[start:end]
        context = binascii.hexlify(snippet).decode()
        raise ParseError(
            f"Failed to parse collection.db at position {pos}. Context: {context}",
            pos,
            context=context,
        ) from e
