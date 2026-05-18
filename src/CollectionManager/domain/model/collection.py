from dataclasses import dataclass


@dataclass(slots=True)
class Collection:
    name: str
    hashes: list[str]

    @property
    def count(self) -> int:
        return len(self.hashes)