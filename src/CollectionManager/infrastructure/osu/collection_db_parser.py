from .data_types import String, Int
from construct import Struct, this, Array
from loguru import logger

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
    except:
        pos = stream.tell()
        start = max(0, pos - 64)
        end = min(len(data), pos + 64)
        snippet = data[start:end]
        logger.error(f"Parse error at offset {pos} (0x{pos:X})")
        logger.error(f"Context bytes [{start}:{end}] (hex):")
        logger.error(binascii.hexlify(snippet).decode())
        raise