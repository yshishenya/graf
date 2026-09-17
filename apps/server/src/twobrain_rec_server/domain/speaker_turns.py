from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

UNKNOWN_SPEAKER_LABEL = "Спикер не определён"
UNKNOWN_PROVIDER_KEYS = frozenset({"", "UNKNOWN", "UNIDENTIFIED", "UNASSIGNED"})
TINY_UNKNOWN_SECONDS = Decimal("0.050")
SOURCE_ROLE_ORDER = {"mic": 0, "incoming": 1, "mixed": 2}
LEGACY_PROVIDER_KEY_RE = re.compile(r"SPEAKER_[0-9]+\Z", re.IGNORECASE)

AttributionState = Literal["confirmed", "unknown", "mixed", "uncertain"]
SpeakerResultState = Literal["accepted", "degraded_provider_result"]
TextConservationStatus = Literal["matched", "mismatched", "not_applicable"]
SpeakerReasonCode = Literal[
    "duplicated_full_text",
    "impossible_provider_chronology",
    "invalid_provider_timing",
    "invalid_transcript_timing",
    "provider_turns_unavailable",
    "text_conservation_mismatch",
    "transcript_evidence_unavailable",
    "unknown_tiny_identity",
]
SPEAKER_REASON_CODES = frozenset(
    {
        "duplicated_full_text",
        "impossible_provider_chronology",
        "invalid_provider_timing",
        "invalid_transcript_timing",
        "provider_turns_unavailable",
        "text_conservation_mismatch",
        "transcript_evidence_unavailable",
        "unknown_tiny_identity",
    }
)
UNSAFE_PROVIDER_REASON_CODES = frozenset(
    {
        "duplicated_full_text",
        "impossible_provider_chronology",
        "invalid_provider_timing",
        "invalid_transcript_timing",
        "text_conservation_mismatch",
    }
)


class SegmentLike(Protocol):
    id: object
    sequence: int
    start_seconds: object
    end_seconds: object
    text: str
    source_role: str


@dataclass(frozen=True, slots=True)
class SpeakerTurnDiagnostics:
    result_state: SpeakerResultState
    defect_origin: Literal["provider", "graf"] | None
    reason_codes: tuple[SpeakerReasonCode, ...]
    raw_turn_count: int
    accepted_turn_count: int
    multi_label_conflict_count: int
    unknown_tiny_count: int
    duplicate_text_count: int
    text_conservation_status: TextConservationStatus
    source_result_hash: str | None = None
    provider_job_id: str | None = None
    provider_result_version: str | None = None
    provider_build_version: str | None = None
    provider_model_version: str | None = None
    alignment_version: str | None = None

    def as_audit_metadata(self) -> dict[str, object]:
        values = {
            "attribution_result_state": self.result_state,
            "defect_origin": self.defect_origin,
            "reason_codes": list(self.reason_codes),
            "raw_turn_count": self.raw_turn_count,
            "accepted_turn_count": self.accepted_turn_count,
            "multi_label_conflict_count": self.multi_label_conflict_count,
            "unknown_tiny_count": self.unknown_tiny_count,
            "duplicate_text_count": self.duplicate_text_count,
            "text_conservation_status": self.text_conservation_status,
            "source_result_hash": self.source_result_hash,
            "provider_job_id": self.provider_job_id,
            "provider_result_version": self.provider_result_version,
            "provider_build_version": self.provider_build_version,
            "provider_model_version": self.provider_model_version,
            "alignment_version": self.alignment_version,
        }
        return {key: value for key, value in values.items() if value is not None}


@dataclass(frozen=True, slots=True)
class CanonicalSpeakerTurn:
    turn_id: str
    source_segment_id: str
    sequence: int
    start_seconds: Decimal
    end_seconds: Decimal
    text: str
    source_role: str
    provider_speaker_key: str | None
    speaker_key: str
    canonical_label: str
    speaker_label: str
    attribution_state: AttributionState
    result_state: SpeakerResultState
    overlap: bool


@dataclass(frozen=True, slots=True)
class CanonicalSpeakerModel:
    turns: tuple[CanonicalSpeakerTurn, ...]
    diagnostics: SpeakerTurnDiagnostics
    confirmed_speaker_keys: tuple[str, ...]
    talk_time_denominator_seconds: Decimal
    talk_time_label: str = "Доля распознанной речи"

    @property
    def result_state(self) -> SpeakerResultState:
        return self.diagnostics.result_state


def _decimal(value: object) -> Decimal:
    return value if isinstance(value, Decimal) else Decimal(str(value))


def _normalized_tokens(values: Iterable[str]) -> str:
    # Speaker alignment may omit punctuation and typographic symbols from the
    # same lexical transcript. Words, numbers, and their order stay exact.
    normalized = unicodedata.normalize("NFKC", " ".join(values)).casefold()
    tokens: list[str] = []
    word: list[str] = []

    def flush_word() -> None:
        if word:
            tokens.append("".join(word))
            word.clear()

    for char in normalized:
        category = unicodedata.category(char)
        if category[0] in {"L", "M", "N"}:
            word.append(char)
            continue
        flush_word()
    flush_word()
    return " ".join(tokens)


def _provider_key(row: object) -> str:
    value = getattr(row, "speaker_label", "")
    return "" if value is None else str(value)


def _chronological_key(row: SegmentLike) -> tuple[Decimal, Decimal, int, int, str, str, str]:
    source_role = str(row.source_role)
    return (
        _decimal(row.start_seconds),
        _decimal(row.end_seconds),
        row.sequence,
        SOURCE_ROLE_ORDER.get(source_role, len(SOURCE_ROLE_ORDER)),
        source_role,
        _provider_key(row),
        _source_id(row),
    )


def _sequence_key(row: SegmentLike) -> tuple[int, Decimal, Decimal, str, str]:
    return (
        row.sequence,
        _decimal(row.start_seconds),
        _decimal(row.end_seconds),
        _provider_key(row),
        _source_id(row),
    )


def _has_impossible_chronology(rows: Iterable[SegmentLike]) -> bool:
    ordered = sorted(rows, key=_sequence_key)
    return any(
        _decimal(current.start_seconds) < _decimal(previous.start_seconds)
        for previous, current in zip(ordered, ordered[1:], strict=False)
    )


def _text_by_role(
    rows: tuple[SegmentLike, ...], normalized_texts: tuple[str, ...]
) -> dict[str, str]:
    grouped: dict[str, list[str]] = defaultdict(list)
    for row, normalized_text in zip(rows, normalized_texts, strict=True):
        if normalized_text:
            grouped[str(row.source_role)].append(normalized_text)
    return {role: " ".join(texts) for role, texts in grouped.items()}


def _overlap_evidence(
    transcripts: tuple[SegmentLike, ...],
    providers: tuple[SegmentLike, ...],
    transcript_texts: tuple[str, ...],
    provider_texts: tuple[str, ...],
    provider_keys: tuple[str, ...],
    provider_ids: tuple[str, ...],
) -> tuple[int, set[str], set[str]]:
    events_by_role: dict[str, list[tuple[Decimal, int, int, int]]] = defaultdict(list)
    for side, rows in enumerate((transcripts, providers)):
        for index, row in enumerate(rows):
            start = _decimal(row.start_seconds)
            end = _decimal(row.end_seconds)
            if end <= start:
                continue
            events_by_role[str(row.source_role)].extend(
                ((start, 1, side, index), (end, 0, side, index))
            )

    labels_by_transcript = [set() for _ in transcripts]
    matching_provider_ids = [set() for _ in transcripts]
    overlapping_provider_ids: set[str] = set()

    def record_pair(transcript_index: int, provider_index: int) -> None:
        labels_by_transcript[transcript_index].add(provider_keys[provider_index])
        transcript_text = transcript_texts[transcript_index]
        if transcript_text and transcript_text == provider_texts[provider_index]:
            matching_provider_ids[transcript_index].add(provider_ids[provider_index])

    for events in events_by_role.values():
        active = (set(), set())
        for _, is_start, side, index in sorted(events):
            if not is_start:
                active[side].discard(index)
                continue
            if side == 0:
                for provider_index in active[1]:
                    record_pair(index, provider_index)
            else:
                for transcript_index in active[0]:
                    record_pair(transcript_index, index)
                if active[1]:
                    overlapping_provider_ids.add(provider_ids[index])
                    overlapping_provider_ids.add(provider_ids[next(iter(active[1]))])
            active[side].add(index)

    duplicate_provider_ids: set[str] = set()
    for matching_ids in matching_provider_ids:
        if len(matching_ids) > 1:
            duplicate_provider_ids.update(matching_ids)
    return (
        sum(len(labels) > 1 for labels in labels_by_transcript),
        duplicate_provider_ids,
        overlapping_provider_ids,
    )


def _is_unknown(key: str) -> bool:
    return key.strip().upper() in UNKNOWN_PROVIDER_KEYS


def legacy_speaker_name_key(provider_speaker_key: str | None) -> str | None:
    if provider_speaker_key is None or not LEGACY_PROVIDER_KEY_RE.fullmatch(provider_speaker_key):
        return None
    return provider_speaker_key.casefold()


def stable_speaker_key(processing_result_id: UUID, provider_speaker_key: str) -> str:
    digest = hashlib.sha256(provider_speaker_key.encode("utf-8")).hexdigest()[:24]
    return f"provider:{processing_result_id.hex}:{digest}"


def canonical_speech_available(result: object | None) -> bool:
    if result is None:
        return False
    if (
        getattr(result, "transcript_status", None) == "unavailable"
        and getattr(result, "failure_reason", None) == "no_recognizable_speech"
    ):
        return False
    return bool(
        (
            getattr(result, "transcript_status", None) == "available"
            and int(getattr(result, "segment_count", 0) or 0) > 0
        )
        or (
            getattr(result, "diarization_status", None) == "available"
            and int(getattr(result, "diarization_segment_count", 0) or 0) > 0
        )
    )


def _turn_id(processing_result_id: UUID, source_segment_id: str) -> str:
    digest = hashlib.sha256(f"{processing_result_id}:{source_segment_id}".encode()).hexdigest()[:24]
    return f"turn_{digest}"


def canonical_speaker_model(
    transcript_rows: Iterable[SegmentLike],
    provider_rows: Iterable[SegmentLike],
    *,
    processing_result_id: UUID,
    speaker_names: Mapping[str, str] | None = None,
    source_result_hash: str | None = None,
    provider_job_id: str | None = None,
    provider_versions: Mapping[str, str | int | None] | None = None,
) -> CanonicalSpeakerModel:
    transcripts = tuple(sorted(transcript_rows, key=_chronological_key))
    providers = tuple(sorted(provider_rows, key=_chronological_key))
    names = speaker_names or {}
    versions = provider_versions or {}
    reasons: set[SpeakerReasonCode] = set()

    invalid_provider_timing = any(
        _decimal(row.end_seconds) <= _decimal(row.start_seconds) for row in providers
    )
    invalid_transcript_timing = any(
        _decimal(row.end_seconds) <= _decimal(row.start_seconds) for row in transcripts
    )
    if invalid_provider_timing:
        reasons.add("invalid_provider_timing")
    if invalid_transcript_timing:
        reasons.add("invalid_transcript_timing")
    providers_by_role: dict[str, list[SegmentLike]] = defaultdict(list)
    for provider in providers:
        providers_by_role[str(provider.source_role)].append(provider)
    if any(_has_impossible_chronology(rows) for rows in providers_by_role.values()):
        reasons.add("impossible_provider_chronology")

    transcript_texts = tuple(_normalized_tokens((row.text,)) for row in transcripts)
    provider_texts = tuple(_normalized_tokens((row.text,)) for row in providers)
    provider_keys = tuple(_provider_key(row) for row in providers)
    provider_ids = tuple(_source_id(row) for row in providers)
    legacy_provider_keys: dict[str, set[str]] = defaultdict(set)
    for provider_key in provider_keys:
        legacy_key = legacy_speaker_name_key(provider_key)
        if legacy_key is not None:
            legacy_provider_keys[legacy_key].add(provider_key)
    multi_label_conflict_count, duplicate_provider_ids, overlap_ids = _overlap_evidence(
        transcripts,
        providers,
        transcript_texts,
        provider_texts,
        provider_keys,
        provider_ids,
    )
    duplicate_text_count = len(duplicate_provider_ids)
    if duplicate_text_count:
        reasons.add("duplicated_full_text")

    transcript_by_role = _text_by_role(transcripts, transcript_texts)
    provider_by_role = _text_by_role(providers, provider_texts)
    if not transcript_by_role:
        conservation: TextConservationStatus = "not_applicable"
        if providers:
            reasons.add("transcript_evidence_unavailable")
    elif transcript_by_role == provider_by_role:
        conservation = "matched"
    else:
        conservation = "mismatched"
        reasons.add("text_conservation_mismatch")

    unknown_durations: dict[str, Decimal] = defaultdict(Decimal)
    for provider, provider_key in zip(providers, provider_keys, strict=True):
        if _is_unknown(provider_key):
            unknown_durations[provider_key.strip().upper()] += max(
                Decimal("0"),
                _decimal(provider.end_seconds) - _decimal(provider.start_seconds),
            )
    unknown_tiny_count = sum(
        duration <= TINY_UNKNOWN_SECONDS for duration in unknown_durations.values()
    )
    if unknown_tiny_count:
        reasons.add("unknown_tiny_identity")

    usable_providers = any(row.text.strip() for row in providers)
    degraded = bool(reasons) or not usable_providers
    if not usable_providers:
        reasons.add("provider_turns_unavailable")
    result_state: SpeakerResultState = "degraded_provider_result" if degraded else "accepted"
    provider_rows_safe = usable_providers and not UNSAFE_PROVIDER_REASON_CODES.intersection(reasons)

    diagnostics = SpeakerTurnDiagnostics(
        result_state=result_state,
        defect_origin=(
            "graf"
            if reasons == {"transcript_evidence_unavailable"}
            else "provider"
            if degraded
            else None
        ),
        reason_codes=tuple(sorted(reasons)),
        raw_turn_count=len(providers),
        accepted_turn_count=(
            sum(bool(row.text.strip()) for row in providers) if provider_rows_safe else 0
        ),
        multi_label_conflict_count=multi_label_conflict_count,
        unknown_tiny_count=unknown_tiny_count,
        duplicate_text_count=duplicate_text_count,
        text_conservation_status=conservation,
        source_result_hash=source_result_hash,
        provider_job_id=provider_job_id,
        provider_result_version=_version(versions, "result_version"),
        provider_build_version=_version(versions, "build_version"),
        provider_model_version=_version(versions, "model_version"),
        alignment_version=_version(versions, "alignment_version"),
    )

    if not provider_rows_safe:
        turns = tuple(
            CanonicalSpeakerTurn(
                turn_id=_turn_id(processing_result_id, _source_id(row)),
                source_segment_id=_source_id(row),
                sequence=row.sequence,
                start_seconds=_decimal(row.start_seconds),
                end_seconds=_decimal(row.end_seconds),
                text=row.text,
                source_role=row.source_role,
                provider_speaker_key=None,
                speaker_key=f"uncertain:{processing_result_id.hex}",
                canonical_label="UNKNOWN",
                speaker_label=UNKNOWN_SPEAKER_LABEL,
                attribution_state="uncertain",
                result_state=result_state,
                overlap=False,
            )
            for row in transcripts
            if row.text.strip()
        )
        return CanonicalSpeakerModel(
            turns=turns,
            diagnostics=diagnostics,
            confirmed_speaker_keys=(),
            talk_time_denominator_seconds=sum(
                (max(Decimal("0"), turn.end_seconds - turn.start_seconds) for turn in turns),
                start=Decimal("0"),
            ),
        )

    labels: dict[str, str] = {}
    accepted_turns: list[CanonicalSpeakerTurn] = []
    confirmed_keys: list[str] = []
    for row, provider_key, row_id in zip(providers, provider_keys, provider_ids, strict=True):
        if not row.text.strip():
            continue
        unknown = _is_unknown(provider_key)
        if unknown:
            speaker_key = f"unknown:{processing_result_id.hex}"
            canonical_label = "UNKNOWN"
            speaker_label = UNKNOWN_SPEAKER_LABEL
            attribution_state: AttributionState = "unknown"
        else:
            speaker_key = stable_speaker_key(processing_result_id, provider_key)
            if provider_key not in labels:
                labels[provider_key] = f"SPEAKER_{len(labels):02d}"
            canonical_label = labels[provider_key]
            speaker_label = names.get(speaker_key)
            if speaker_label is None:
                legacy_key = legacy_speaker_name_key(provider_key)
                speaker_label = (
                    names.get(legacy_key, canonical_label)
                    if legacy_key is not None
                    and len(legacy_provider_keys.get(legacy_key, ())) == 1
                    else canonical_label
                )
            attribution_state = "confirmed"
            if speaker_key not in confirmed_keys:
                confirmed_keys.append(speaker_key)
        accepted_turns.append(
            CanonicalSpeakerTurn(
                turn_id=_turn_id(processing_result_id, row_id),
                source_segment_id=row_id,
                sequence=row.sequence,
                start_seconds=_decimal(row.start_seconds),
                end_seconds=_decimal(row.end_seconds),
                text=row.text,
                source_role=row.source_role,
                provider_speaker_key=provider_key,
                speaker_key=speaker_key,
                canonical_label=canonical_label,
                speaker_label=speaker_label,
                attribution_state=attribution_state,
                result_state=result_state,
                overlap=row_id in overlap_ids,
            )
        )
    denominator = sum(
        (turn.end_seconds - turn.start_seconds for turn in accepted_turns),
        start=Decimal("0"),
    )
    return CanonicalSpeakerModel(
        turns=tuple(accepted_turns),
        diagnostics=diagnostics,
        confirmed_speaker_keys=tuple(confirmed_keys),
        talk_time_denominator_seconds=denominator,
    )


def _version(values: Mapping[str, str | int | None], key: str) -> str | None:
    value = values.get(key)
    return str(value) if value is not None else None


def _source_id(row: object) -> str:
    value = getattr(row, "id", None)
    return str(value) if value is not None else f"segment:{row.sequence}"
