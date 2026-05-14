from dataclasses import dataclass, field

from src.CollectionManager.domain.service import CollectionService, SearchService
from src.CollectionManager.infrastructure.storage import BeatmapRepository, CollectionRepository, SqliteDB


@dataclass(slots=True)
class Container:
    """Application dependency container.

    The container owns the shared database handle and builds repositories and
    services exactly once so bootstrap code can hand a single object to the UI
    layer later.
    """

    db: SqliteDB = field(default_factory=SqliteDB)
    beatmap_repository: BeatmapRepository = field(init=False)
    collection_repository: CollectionRepository = field(init=False)
    collection_service: CollectionService = field(init=False)
    search_service: SearchService = field(init=False)

    def __post_init__(self) -> None:
        self.beatmap_repository = BeatmapRepository(self.db)
        self.collection_repository = CollectionRepository(self.db)
        self.collection_service = CollectionService(self.collection_repository, self.beatmap_repository)
        self.search_service = SearchService(self.beatmap_repository, self.collection_repository)

    def close(self) -> None:
        """Release database engine resources."""

        self.db.dispose()