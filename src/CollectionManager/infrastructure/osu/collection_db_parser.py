from .data_types import String, Int
from construct import Struct, this, Array

from src.CollectionManager.infrastructure.exceptions.parser import ParseError

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

def parse_collection_db(data: bytes):
    from io import BytesIO
    import binascii

    stream = BytesIO(data)
    try:
        result = collection.parse_stream(stream)
        return result
    except Exception as e:
        pos = stream.tell()
        start = max(0, pos - 64)
        end = min(len(data), pos + 64)
        snippet = data[start:end]
        context = binascii.hexlify(snippet).decode()
        raise ParseError(
            f"Failed to parse collection.db at position {pos}. Context: {context}",
            pos,
            context=context,
        ) from e