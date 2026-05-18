"""Search service for beatmap queries with parsing and filtering."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from typing import Any

from src.CollectionManager.domain.exceptions import ServiceOperationError
from src.CollectionManager.domain.model import Beatmap, Collection
from src.CollectionManager.infrastructure.storage.repositories import BeatmapRepository, CollectionRepository


@dataclass
class ParsedQuery:
    """Result of parsing a search query."""
    filters: dict[str, Any]
    keyword: str


class QueryParser:
    """Parse osu-style search queries into structured filters and keywords."""

    # Comparison operators (ordered by length to match longest first)
    OPERATORS = [":=", ">=", "<=", "!=", "=", ":", ">", "<"]
    TOKEN_PATTERN = re.compile(r"^(?P<field>[A-Za-z_]\w*)(?P<op>:=|>=|<=|!=|=|:|>|<)(?P<value>.*)$")

    # Field aliases for normalization
    FIELD_ALIASES = {
        "star": "star",
        "stars": "star",
        "sr": "star",  # Common abbreviation
        "key": "keys",
        "keys": "keys",
    }

    # Supported filter fields
    SUPPORTED_FIELDS = {
        "artist",
        "creator",
        "title",
        "difficulty",
        "tags",
        "source",
        "ar",
        "cs",
        "od",
        "hp",
        "star",
        "stars",
        "length",
        "drain",
        "mode",
        "status",
        "played",
        "unplayed",
        "keys",
    }

    def _tokenize(self, query: str) -> list[str]:
        lexer = shlex.shlex(query, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = ""
        try:
            return list(lexer)
        except ValueError:
            return query.split()

    def _normalize_field(self, field: str) -> str:
        return self.FIELD_ALIASES.get(field.casefold(), field.casefold())

    def _parse_token(self, token: str) -> tuple[str, Any] | None:
        match = self.TOKEN_PATTERN.match(token)
        if match is None:
            return None

        field = self._normalize_field(match.group("field"))
        if field not in self.SUPPORTED_FIELDS:
            return None

        op = match.group("op")
        value = match.group("value")
        if op == ':=':
            op = ':'

        if field == "unplayed":
            # currently Beatmap doesn't track play status, so this is a placeholder for future functionality
            return field, True

        if op in (">=", "<=", ">", "<", "!="):
            return field, (op, value)
        return field, value

    def parse(self, query: str) -> ParsedQuery:
        """Parse a search query string.

        Supports:
        - Quoted values: artist="Toby Fox"
        - Unquoted values: artist=Toby (only first word)
        - Operators: =, :, >=, <=, >, <, !=
        - Special handling for keys: implicitly sets mode=mania and converts to cs filter
        - Bare words become keywords
        """

        filters: dict[str, Any] = {}
        keywords: list[str] = []

        for token in self._tokenize(query):
            token_lower = token.casefold()
            if token_lower == "unplayed":
                filters["unplayed"] = True
                continue

            parsed = self._parse_token(token)
            if parsed is None:
                keywords.append(token)

            else:
                field, value = parsed
                filters[field] = value

        if "keys" in filters:
            keys_cond = filters.pop("keys")
            filters["mode"] = "mania"
            filters["cs"] = keys_cond

        return ParsedQuery(
            filters=filters,
            keyword=" ".join(keywords),
        )


class SearchService:
    """High-level search service combining parsing and repository queries."""

    def __init__(self, beatmap_repo: BeatmapRepository, collection_repo: CollectionRepository) -> None:
        self._repo = beatmap_repo
        self._collection_repo = collection_repo
        self._parser = QueryParser()

    def search_beatmaps(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[Beatmap]:
        """Search beatmaps using a raw query string.

        The query is parsed into filters and keywords, then passed to the repository.
        """

        parsed = self._parser.parse(query)
        try:
            return self._repo.search(
                keyword=parsed.keyword,
                limit=limit,
                filters=parsed.filters if parsed.filters else None,
            )
        except Exception as exc:
            raise ServiceOperationError("Failed to search beatmaps.") from exc

    def search(self, query: str, limit: int | None = None) -> list[Beatmap]:
        """Alias for beatmap search."""

        return self.search_beatmaps(query, limit=limit)

    def search_collections(self, query: str, limit: int | None = None) -> list[Collection]:
        """Search collections by name using a case-insensitive substring match."""

        needle = query.strip().casefold()
        try:
            collections = self._collection_repo.list()
        except Exception as exc:
            raise ServiceOperationError("Failed to search collections.") from exc
        if needle:
            collections = [collection for collection in collections if needle in collection.name.casefold()]
        collections.sort(key=lambda collection: collection.name.casefold())
        if limit is not None:
            return collections[:limit]
        return collections
