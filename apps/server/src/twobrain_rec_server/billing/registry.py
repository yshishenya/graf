"""Strict operator-provided YooKassa CSV profile; only safe metadata leaves parsing."""
from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import re
import stat
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

PROFILE = "yookassa-ru-csv-v1"
KINDS = ("payments", "refunds")
MAX_FILES = 64
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TOTAL_BYTES = 64 * 1024 * 1024
PART_ROWS = 10_000
CSV_FIELD_CHARS = 131_072
COLUMNS = {
    "payments": ("Идентификатор платежа", "Сумма платежа", "Валюта платежа", "Время платежа", "Тип платежа"),
    "refunds": ("Идентификатор возврата", "Идентификатор платежа", "Сумма возврата", "Валюта возврата", "Время возврата"),
}
LABELS = {"payments": ("ПЛАТЕЖЕЙ", "платежей", "принятых платежей"),
          "refunds": ("ВОЗВРАТОВ", "возвратов", "возвратов")}
IDENTITY = r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}"
MONEY = r"(?:0|[1-9][0-9]{0,15})\.[0-9]{2}"
COUNT = r"(?:0|[1-9][0-9]{0,5})"
EXTRA_FOOTERS = ("Сумма принятых платежей за вычетом комиссии и НДС",
                 "Сумма комиссии без НДС за принятые платежи",
                 "Сумма НДС с комиссии за принятые платежи")
# Every validation rule is pinned by this versioned description and its fingerprint.
CONFIG = {
    "profile": PROFILE, "schema_version": 1, "validation_revision": 2,
    "encoding": "strict utf-8-sig", "delimiter": ";", "language": "ru",
    "columns": COLUMNS, "labels": LABELS, "identity": IDENTITY, "money": MONEY, "count": COUNT,
    "date": "ISO filename/header; dd.MM.yyyy HH:mm:ss provider Europe/Moscow operation day",
    "framing": "title contract(shop), date, trimmed unique headers, exact row width, only empty CSV rows skipped, gross/count footer, matching contract",
    "footer": "total and any present payment-type gross/count equal rows; duplicate/unknown footer rejected",
    "ignored_footer_labels": EXTRA_FOOTERS,
    "ignored_footer_format": "payments only; optional type; exact two decimals with dot/comma and RUB; no duplicate labels",
    "multipart": "unique 1..N, exactly one last, nonlast=10000, last=1..10000; no single+parts",
    "empty": "present single zero-row/zero-footer file plus expected-empty kind; absence is missing",
    "filename": "yoomoney-kind-shop-YYYY-MM-DD[-part-N[-last]].csv; shop numeric 1..32; N=1..64",
    "duplicates": "unique operation across all parts per kind; multiple refunds per payment allowed",
    "max_files": MAX_FILES, "max_file_bytes": MAX_FILE_BYTES, "max_total_bytes": MAX_TOTAL_BYTES,
    "part_rows": PART_ROWS, "max_header_chars": 128, "max_columns": 128,
    "max_contract_chars": 128, "max_type_chars": 32,
    "max_csv_field_chars": CSV_FIELD_CHARS,
    "file_type": "regular only; nonblocking open; fstat before bounded read",
}


def canonical_hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


CONFIG_FINGERPRINT = canonical_hash(CONFIG)


class RegistryInputError(ValueError):
    """Only fixed codes, never input text, escape this boundary."""


@dataclass(frozen=True, slots=True)
class ParsedRegistry:
    kind: str
    index: int
    last: bool
    multipart: bool
    expected_empty: bool
    sha256: str
    row_count: int
    identities: frozenset[str] = field(repr=False)

    def metadata(self) -> dict:
        return {name: getattr(self, name) for name in
                ("kind", "index", "last", "multipart", "expected_empty", "sha256", "row_count")}


@dataclass(frozen=True, slots=True)
class RegistryBundle:
    parts: tuple[dict, ...]
    gaps: tuple[tuple[str, int, str], ...]
    input_digest: str

    @property
    def files_complete(self) -> bool:
        return not self.gaps


def _money(value: str) -> int:
    if not re.fullmatch(MONEY, value):
        raise RegistryInputError("invalid_money")
    whole, fraction = value.split(".")
    return int(whole) * 100 + int(fraction)


def parse_registry(content: bytes, *, filename: str, kind: str, shop_id: str,
                   report_date: date, expected_empty: bool = False) -> ParsedRegistry:
    if csv.field_size_limit() != CSV_FIELD_CHARS:
        raise RegistryInputError("csv_configuration_mismatch")
    if kind not in KINDS or not re.fullmatch(r"[0-9]{1,32}", shop_id):
        raise RegistryInputError("invalid_scope")
    match = re.fullmatch(rf"yoomoney-{kind}-{shop_id}-{report_date.isoformat()}(?:-part-([1-9][0-9]?)(-last)?)?\.csv", filename)
    if match is None:
        raise RegistryInputError("invalid_filename")
    multipart = match[1] is not None
    index = int(match[1] or 1)
    last = not multipart or bool(match[2])
    if index > MAX_FILES or len(content) > MAX_FILE_BYTES:
        raise RegistryInputError("input_limit")
    try:
        rows = iter(csv.reader(io.StringIO(content.decode("utf-8-sig"), newline=""), delimiter=";", strict=True))
        rows = (row for row in rows if row)
        title, day, header = next(rows), next(rows), next(rows)
        upper, label, gross_label = LABELS[kind]
        if len(title) != 1 or len(day) != 1:
            raise RegistryInputError("invalid_framing")
        title_match = re.fullmatch(rf"РЕЕСТР {upper} ПО ДОГОВОРУ ([^\x00-\x1f;]{{1,128}}) \({shop_id}\)", title[0])
        if title_match is None or day[0] != f"Дата {label}: {report_date.isoformat()}":
            raise RegistryInputError("scope_mismatch")
        header = [name.strip() for name in header]
        if (len(header) > 128 or len(set(header)) != len(header)
                or any(not name.strip() or len(name) > 128 for name in header)
                or not set(COLUMNS[kind]).issubset(header)):
            raise RegistryInputError("invalid_columns")
        positions = [header.index(column) for column in COLUMNS[kind]]
        identities: set[str] = set()
        total = 0
        type_counts: Counter[str] = Counter()
        type_gross: Counter[str] = Counter()
        footer: dict[str, int] = {}
        ignored_footer: set[str] = set()
        in_footer = False
        ended = False
        for row in rows:
            line = row[0]
            is_footer = len(row) == 1 and line.startswith(("Сумма ", "Число ", "По договору "))
            if in_footer or is_footer:
                in_footer = True
                if len(row) != 1 or ended:
                    raise RegistryInputError("invalid_footer")
                if line.startswith("По договору "):
                    if line != f"По договору {title_match[1]}":
                        raise RegistryInputError("scope_mismatch")
                    ended = True
                    continue
                found = re.fullmatch(rf"(Сумма {gross_label}(?: типа [A-Za-z0-9_-]{{1,32}})?): ({MONEY}) RUB", line)
                number = re.fullmatch(rf"(Число {label}(?: типа [A-Za-z0-9_-]{{1,32}})?): ({COUNT})", line)
                if found or number:
                    key, value = (found or number).groups()
                    if " типа " in key and kind != "payments":
                        raise RegistryInputError("invalid_footer")
                    if key in footer:
                        raise RegistryInputError("duplicate_footer")
                    footer[key] = _money(value) if found else int(value)
                else:
                    extra = re.fullmatch(rf"({'|'.join(map(re.escape, EXTRA_FOOTERS))})( типа [A-Za-z0-9_-]{{1,32}})?: ((?:0|[1-9][0-9]{{0,15}})[.,][0-9]{{2}}) RUB", line)
                    if kind != "payments" or extra is None:
                        raise RegistryInputError("invalid_footer")
                    key = extra[1] + (extra[2] or "")
                    if key in ignored_footer:
                        raise RegistryInputError("duplicate_footer")
                    ignored_footer.add(key)
                continue
            if len(row) != len(header):
                raise RegistryInputError("invalid_row_width")
            values = [row[p] for p in positions]
            identity = values[0]
            identity_values = values[:1] if kind == "payments" else values[:2]
            if any(not re.fullmatch(IDENTITY, value) for value in identity_values):
                raise RegistryInputError("invalid_identity")
            if identity in identities:
                raise RegistryInputError("duplicate_identity")
            amount, currency, timestamp = values[1:4] if kind == "payments" else values[2:5]
            minor = _money(amount)
            if minor <= 0 or currency != "RUB":
                raise RegistryInputError("invalid_currency_or_amount")
            if not re.fullmatch(r"[0-9]{2}\.[0-9]{2}\.[0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2}", timestamp):
                raise RegistryInputError("invalid_provider_time")
            try:
                provider_time = datetime.strptime(timestamp, "%d.%m.%Y %H:%M:%S")
            except ValueError:
                raise RegistryInputError("invalid_provider_time") from None
            if provider_time.date() != report_date:
                raise RegistryInputError("provider_day_mismatch")
            if kind == "payments":
                payment_type = values[4]
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,32}", payment_type):
                    raise RegistryInputError("invalid_payment_type")
                type_counts[payment_type] += 1
                type_gross[payment_type] += minor
            identities.add(identity)
            total += minor
            if len(identities) > PART_ROWS:
                raise RegistryInputError("row_limit")
        count = len(identities)
        required = {f"Сумма {gross_label}": total, f"Число {label}": count}
        if any(footer.get(key) != value for key, value in required.items()):
            raise RegistryInputError("footer_mismatch")
        for key, value in footer.items():
            if " типа " in key:
                payment_type = key.split(" типа ")[1]
                expected = type_gross[payment_type] if key.startswith("Сумма ") else type_counts[payment_type]
                if value != expected:
                    raise RegistryInputError("footer_type_mismatch")
        if (expected_empty != (count == 0)) or (multipart and count == 0):
            raise RegistryInputError("empty_mismatch")
        if multipart and not last and count != PART_ROWS:
            raise RegistryInputError("nonlast_row_count")
    except (UnicodeError, csv.Error, StopIteration):
        raise RegistryInputError("invalid_csv") from None
    return ParsedRegistry(kind, index, last, multipart, expected_empty,
                          hashlib.sha256(content).hexdigest(), count, frozenset(identities))


def registry_bundle(parts: tuple[ParsedRegistry, ...], *, environment: str, shop_id: str,
                    report_date: date, expected_empty: frozenset[str]) -> RegistryBundle:
    if environment not in {"test", "production"} or not re.fullmatch(r"[0-9]{1,32}", shop_id) or not expected_empty.issubset(KINDS):
        raise RegistryInputError("invalid_scope")
    if len(parts) > MAX_FILES:
        raise RegistryInputError("input_limit")
    gaps: list[tuple[str, int, str]] = []
    ordered = sorted(parts, key=lambda p: (p.kind, p.index))
    for kind in KINDS:
        selected = [p for p in ordered if p.kind == kind]
        if not selected:
            gaps.append((kind, 0, "missing_kind"))
            continue
        if any(p.expected_empty != (kind in expected_empty) for p in selected):
            raise RegistryInputError("empty_mismatch")
        if len({p.index for p in selected}) != len(selected) or (len(selected) > 1 and any(not p.multipart for p in selected)):
            raise RegistryInputError("duplicate_part")
        identities: set[str] = set()
        for part in selected:
            if identities.intersection(part.identities):
                raise RegistryInputError("duplicate_identity")
            identities.update(part.identities)
        lasts = [p.index for p in selected if p.last]
        if len(lasts) > 1 or (lasts and selected[-1].index > lasts[0]):
            raise RegistryInputError("extra_part")
        if not lasts:
            gaps.append((kind, 0, "missing_last"))
        final_index = lasts[0] if lasts else selected[-1].index
        observed = {p.index for p in selected}
        for index in range(1, final_index + 1):
            if index not in observed:
                gaps.append((kind, index, "missing_part"))
    metadata = tuple(p.metadata() for p in ordered)
    digest = canonical_hash({"scope": [environment, shop_id, report_date.isoformat()],
                             "config": CONFIG_FINGERPRINT, "expected_empty": sorted(expected_empty),
                             "parts": [{k: p[k] for k in ("kind", "index", "last", "expected_empty", "sha256")} for p in metadata]})
    return RegistryBundle(metadata, tuple(gaps), digest)


def read_registry_files(paths: dict[str, list[Path]], *, environment: str, shop_id: str,
                        report_date: date, expected_empty: frozenset[str]) -> RegistryBundle:
    """Caller must pass the database identity guard before touching any path."""
    if sum(len(values) for values in paths.values()) > MAX_FILES:
        raise RegistryInputError("input_limit")
    parts = []
    total_bytes = 0
    for kind in KINDS:
        for path in paths.get(kind, []):
            try:
                with os.fdopen(os.open(path, os.O_RDONLY | os.O_NONBLOCK), "rb") as source:
                    if not stat.S_ISREG(os.fstat(source.fileno()).st_mode):
                        raise RegistryInputError("input_unreadable")
                    content = source.read(min(MAX_FILE_BYTES, MAX_TOTAL_BYTES - total_bytes) + 1)
            except OSError:
                raise RegistryInputError("input_unreadable") from None
            total_bytes += len(content)
            if len(content) > MAX_FILE_BYTES or total_bytes > MAX_TOTAL_BYTES:
                raise RegistryInputError("input_limit")
            parts.append(parse_registry(content, filename=path.name, kind=kind, shop_id=shop_id,
                                        report_date=report_date, expected_empty=kind in expected_empty))
    return registry_bundle(tuple(parts), environment=environment, shop_id=shop_id,
                           report_date=report_date, expected_empty=expected_empty)
