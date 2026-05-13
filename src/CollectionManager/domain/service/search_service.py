"""Search service for beatmap queries with parsing and filtering."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.CollectionManager.infrastructure.storage.repositories import BeatmapRepository
from src.CollectionManager.domain.model import Beatmap


@dataclass
class ParsedQuery:
    """Result of parsing a search query."""
    filters: dict[str, Any]
    keyword: str


class QueryParser:
    """Parse osu-style search queries into structured filters and keywords."""

    # Comparison operators (ordered by length to match longest first)
    OPERATORS = [">=", "<=", "!=", "=", ":", ">", "<"]

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

        # Step 1: Extract quoted values and replace with placeholders
        quoted_map: dict[str, tuple[str, str]] = {}
        placeholder_idx = 0

        def replace_quoted(match):
            nonlocal placeholder_idx
            field_part = match.group(1)
            quoted_val = match.group(2)
            placeholder = f"__QUOTED_{placeholder_idx}__"
            quoted_map[placeholder] = (field_part, quoted_val)
            placeholder_idx += 1
            return placeholder

        # Match: field="value" or field:="value" etc
        query = re.sub(
            r'([\w]+)(?:=|:)?="([^"]*)"',
            replace_quoted,
            query,
        )

        # Step 2: Split remaining query into tokens
        tokens = query.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Check if token is a quoted placeholder
            if token.startswith("__QUOTED_"):
                if token in quoted_map:
                    field_raw, value = quoted_map[token]
                    field_norm = self.FIELD_ALIASES.get(field_raw.lower(), field_raw.lower())
                    if field_norm in self.SUPPORTED_FIELDS:
                        filters[field_norm] = value
                i += 1
                continue

            # Check for unplayed as a standalone token (no operator)
            if token.lower() == "unplayed":
                filters["unplayed"] = True
                i += 1
                continue

            # Check if token matches field[op]value pattern
            matched = False
            for op in self.OPERATORS:
                if op in token:
                    # Split on the first occurrence of operator
                    idx = token.find(op)
                    field_raw = token[:idx]
                    value = token[idx + len(op) :]

                    field_norm = self.FIELD_ALIASES.get(field_raw.lower(), field_raw.lower())

                    # Handle unplayed special case (no value needed)
                    if field_norm == "unplayed":
                        filters[field_norm] = True
                        matched = True
                        break

                    if field_norm in self.SUPPORTED_FIELDS:
                        # Store as (op, value) if operator is comparison; otherwise just value
                        if op in (">=", "<=", ">", "<", "!="):
                            filters[field_norm] = (op, value)
                        else:
                            # For = and :, just store the value
                            filters[field_norm] = value
                        matched = True
                        break

            if not matched:
                # Not a structured filter, treat as keyword
                keywords.append(token)

            i += 1

        # Step 3: Handle keys special case
        if "keys" in filters:
            keys_cond = filters.pop("keys")
            # Implicitly set mode to mania
            filters["mode"] = "mania"
            # Convert keys filter to cs filter
            filters["cs"] = keys_cond

        return ParsedQuery(
            filters=filters,
            keyword=" ".join(keywords),
        )


class SearchService:
    """High-level search service combining parsing and repository queries."""

    def __init__(self, beatmap_repo: BeatmapRepository) -> None:
        self._repo = beatmap_repo
        self._parser = QueryParser()

    def search(
        self,
        query: str,
        limit: int | None = None,
    ) -> list[Beatmap]:
        """Search beatmaps using a raw query string.

        The query is parsed into filters and keywords, then passed to the repository.
        """

        parsed = self._parser.parse(query)
        return self._repo.search(
            keyword=parsed.keyword,
            limit=limit,
            filters=parsed.filters if parsed.filters else None,
        )
