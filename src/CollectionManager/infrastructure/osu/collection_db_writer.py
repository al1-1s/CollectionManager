from loguru import logger
from pathlib import Path

from src.CollectionManager.domain.model import Collection
from .collection_db_parser import collection

class CollectionDbWriter:

    def write(self, collections: list[Collection], output_path: Path) -> None:
        """Serialize a list of Collection objects into the osu! collection.db format.
        """
        raw = {
            "version": 20251020,
            "collection_count": len(collections),

            "collections": [
                {
                    "name": c.name,
                    "map_count": c.count,
                    "map_hashes": c.hashes,
                }
                for c in collections
            ]
        }
        data = collection.build(raw)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)