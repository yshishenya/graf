from __future__ import annotations

import csv
import hashlib
import io
from dataclasses import dataclass


class RegistryInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RegistrySummary:
    registry_kind: str
    environment: str
    row_count: int
    content_sha256: str
    header_sha256: str


def summarize_registry_csv(
    content: str,
    *,
    registry_kind: str,
    environment: str,
    required_columns: tuple[str, ...],
) -> RegistrySummary:
    """Validate an official CSV shape and retain only stable metadata."""
    if not registry_kind or not environment or not content:
        raise RegistryInputError("registry metadata or content is missing")
    try:
        reader = csv.reader(io.StringIO(content, newline=""))
        header = tuple(next(reader))
    except (csv.Error, StopIteration) as exc:
        raise RegistryInputError("registry header is invalid") from exc
    if not header or len(set(header)) != len(header) or any(not name.strip() for name in header):
        raise RegistryInputError("registry header is invalid")
    missing = set(required_columns).difference(header)
    if missing:
        raise RegistryInputError("registry required columns are missing")
    row_count = 0
    try:
        for row in reader:
            if not row or all(not value.strip() for value in row):
                continue
            if len(row) != len(header):
                raise RegistryInputError("registry row width is invalid")
            row_count += 1
    except csv.Error as exc:
        raise RegistryInputError("registry row is invalid") from exc
    normalized = content.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    header_bytes = "\x1f".join(header).encode("utf-8")
    return RegistrySummary(
        registry_kind=registry_kind,
        environment=environment,
        row_count=row_count,
        content_sha256=hashlib.sha256(normalized).hexdigest(),
        header_sha256=hashlib.sha256(header_bytes).hexdigest(),
    )


def registry_parts_complete(*, required_parts: tuple[str, ...], observed_parts: set[str]) -> bool:
    if not required_parts or any(not part for part in required_parts):
        raise RegistryInputError("registry part names are invalid")
    return set(required_parts).issubset(observed_parts)
