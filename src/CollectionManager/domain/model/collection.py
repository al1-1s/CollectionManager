from dataclasses import dataclass

@dataclass(slots=True)
class Collection:
    name: str
    count: int
    hashes: list[str]