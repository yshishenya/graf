from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass
from datetime import date

_SAFE_META = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
REGISTRY_KINDS = frozenset(("payments", "refunds"))


class RegistryInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RegistrySummary:
    registry_kind: str
    environment: str
    row_count: int
    content_sha256: str
    header_sha256: str
    shop_id: str | None = None
    report_date: str | None = None
    schema_version: str | None = None
    language: str | None = None
    config_version: str | None = None
    part_name: str | None = None
    expected_empty: bool = False


@dataclass(frozen=True, slots=True)
class RegistryCompleteness:
    registry_kind: str
    required_parts: tuple[str, ...]
    observed_parts: tuple[str, ...]
    expected_empty_parts: tuple[str, ...]
    missing_parts: tuple[str, ...]
    duplicate_parts: tuple[str, ...]
    completeness_sha256: str

    @property
    def complete(self) -> bool:
        return not self.missing_parts and not self.duplicate_parts


@dataclass(frozen=True, slots=True)
class RegistryGap:
    registry_kind: str
    environment: str
    report_date: str
    reason: str
    owner: str
    evidence_sha256: str
    state: str = "detected"
    severity: str = "high"


@dataclass(frozen=True, slots=True)
class RegistryPart:
    """One operator-provided report part; content is consumed, never returned."""

    part_name: str
    content: str
    expected_empty: bool = False


@dataclass(frozen=True, slots=True)
class RegistryImport:
    """Metadata-only result of importing one payments or refunds report set."""

    summaries: tuple[RegistrySummary, ...]
    completeness: RegistryCompleteness
    gaps: tuple[RegistryGap, ...]


def summarize_registry_csv(
    content: str,
    *,
    registry_kind: str,
    environment: str,
    required_columns: tuple[str, ...],
    shop_id: str | None = None,
    report_date: str | None = None,
    schema_version: str | None = None,
    language: str | None = None,
    config_version: str | None = None,
    part_name: str | None = None,
    expected_empty: bool = False,
) -> RegistrySummary:
    """Validate an official CSV shape and retain only stable metadata."""
    if not registry_kind or not environment or not content:
        raise RegistryInputError("registry metadata or content is missing")
    if registry_kind not in REGISTRY_KINDS:
        raise RegistryInputError("registry kind must be payments or refunds")
    _validate_meta("environment", environment)
    for name, value in (
        ("shop_id", shop_id),
        ("schema_version", schema_version),
        ("language", language),
        ("config_version", config_version),
        ("part_name", part_name),
    ):
        if value is not None:
            _validate_meta(name, value)
    if report_date is not None:
        try:
            date.fromisoformat(report_date)
        except ValueError as exc:
            raise RegistryInputError("registry report date is invalid") from exc
    try:
        reader = csv.reader(io.StringIO(content, newline=""), strict=True)
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
        shop_id=shop_id,
        report_date=report_date,
        schema_version=schema_version,
        language=language,
        config_version=config_version,
        part_name=part_name,
        expected_empty=expected_empty,
    )


def import_registry_reports(
    parts: tuple[RegistryPart, ...],
    *,
    registry_kind: str,
    environment: str,
    required_parts: tuple[str, ...],
    required_columns: tuple[str, ...],
    report_date: str,
    owner: str,
    shop_id: str | None = None,
    schema_version: str | None = None,
    language: str | None = None,
    config_version: str | None = None,
) -> RegistryImport:
    """Validate a complete official report set and emit safe reconciliation evidence.

    The caller may provide multipart payments *or* refunds reports, but never a
    combined set. CSV bytes are parsed only long enough to calculate row and
    content/header hashes; the returned object contains no report rows.
    """
    if not parts:
        raise RegistryInputError("registry report parts are missing")
    summaries: list[RegistrySummary] = []
    for part in parts:
        if not isinstance(part, RegistryPart):
            raise RegistryInputError("registry report part is invalid")
        _validate_meta("part_name", part.part_name)
        summary = summarize_registry_csv(
            part.content,
            registry_kind=registry_kind,
            environment=environment,
            required_columns=required_columns,
            shop_id=shop_id,
            report_date=report_date,
            schema_version=schema_version,
            language=language,
            config_version=config_version,
            part_name=part.part_name,
            expected_empty=part.expected_empty,
        )
        if part.expected_empty and summary.row_count:
            raise RegistryInputError("expected-empty registry part contains rows")
        summaries.append(summary)

    completeness = assess_registry_completeness(
        registry_kind=registry_kind,
        required_parts=required_parts,
        observed_parts=tuple(summary.part_name for summary in summaries if summary.part_name is not None),
        expected_empty_parts=tuple(
            summary.part_name
            for summary in summaries
            if summary.expected_empty and summary.part_name is not None
        ),
    )
    gaps: list[RegistryGap] = []
    if completeness.missing_parts:
        gaps.append(
            build_registry_gap(
                registry_kind=registry_kind,
                environment=environment,
                report_date=report_date,
                reason="missing_part",
                owner=owner,
                evidence_sha256=completeness.completeness_sha256,
            )
        )
    if completeness.duplicate_parts:
        gaps.append(
            build_registry_gap(
                registry_kind=registry_kind,
                environment=environment,
                report_date=report_date,
                reason="duplicate_part",
                owner=owner,
                evidence_sha256=completeness.completeness_sha256,
            )
        )
    return RegistryImport(tuple(summaries), completeness, tuple(gaps))


def registry_parts_complete(*, required_parts: tuple[str, ...], observed_parts: set[str]) -> bool:
    if not required_parts or any(not part for part in required_parts):
        raise RegistryInputError("registry part names are invalid")
    return set(required_parts).issubset(observed_parts)


def assess_registry_completeness(
    *,
    registry_kind: str,
    required_parts: tuple[str, ...],
    observed_parts: tuple[str, ...] | set[str],
    expected_empty_parts: tuple[str, ...] = (),
) -> RegistryCompleteness:
    """Return deterministic completeness evidence without retaining report rows."""
    if registry_kind not in REGISTRY_KINDS:
        raise RegistryInputError("registry kind must be payments or refunds")
    if (
        not required_parts
        or len(set(required_parts)) != len(required_parts)
        or any(not _SAFE_META.fullmatch(part) for part in required_parts)
        or any(not _SAFE_META.fullmatch(part) for part in observed_parts)
        or any(not _SAFE_META.fullmatch(part) for part in expected_empty_parts)
    ):
        raise RegistryInputError("registry part names are invalid")
    observed = tuple(sorted(observed_parts))
    expected_empty = tuple(sorted(expected_empty_parts))
    duplicates = tuple(sorted({part for part in observed if observed.count(part) > 1}))
    missing = tuple(sorted(set(required_parts) - set(observed) - set(expected_empty)))
    if set(expected_empty) - set(required_parts):
        raise RegistryInputError("expected-empty part is not declared")
    canonical = "\n".join(
        (
            registry_kind,
            "required=" + ",".join(sorted(required_parts)),
            "observed=" + ",".join(observed),
            "expected_empty=" + ",".join(expected_empty),
            "missing=" + ",".join(missing),
            "duplicates=" + ",".join(duplicates),
        )
    ).encode("utf-8")
    return RegistryCompleteness(
        registry_kind=registry_kind,
        required_parts=tuple(sorted(required_parts)),
        observed_parts=observed,
        expected_empty_parts=expected_empty,
        missing_parts=missing,
        duplicate_parts=duplicates,
        completeness_sha256=hashlib.sha256(canonical).hexdigest(),
    )


def build_registry_gap(
    *,
    registry_kind: str,
    environment: str,
    report_date: str,
    reason: str,
    owner: str,
    evidence_sha256: str,
    severity: str = "high",
) -> RegistryGap:
    """Create owned metadata-only gap evidence; provider data never enters it."""
    if registry_kind not in REGISTRY_KINDS:
        raise RegistryInputError("registry kind must be payments or refunds")
    _validate_meta("environment", environment)
    _validate_meta("owner", owner)
    try:
        date.fromisoformat(report_date)
    except ValueError as exc:
        raise RegistryInputError("registry report date is invalid") from exc
    if not re.fullmatch(r"[a-z][a-z0-9_.:-]{0,159}", reason):
        raise RegistryInputError("registry gap reason is invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", evidence_sha256):
        raise RegistryInputError("registry evidence hash is invalid")
    if severity not in {"low", "medium", "high", "critical"}:
        raise RegistryInputError("registry gap severity is invalid")
    return RegistryGap(
        registry_kind=registry_kind,
        environment=environment,
        report_date=report_date,
        reason=reason.strip(),
        owner=owner,
        evidence_sha256=evidence_sha256,
        severity=severity,
    )


def _validate_meta(name: str, value: str) -> None:
    if not _SAFE_META.fullmatch(value):
        raise RegistryInputError(f"registry {name} is invalid")
