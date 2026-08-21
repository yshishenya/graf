from __future__ import annotations

import hashlib
import unicodedata
from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Literal, Protocol
from uuid import UUID

UNKNOWN_SPEAKER_LABEL = "Спикер не определён"
UNKNOWN_PROVIDER_KEYS = frozenset({"", "UNKNOWN", "UNIDENTIFIED", "UNASSIGNED"})
TINY_UNKNOWN_SECONDS = Decimal("0.050")

AttributionState = Literal["confirmed", "unknown", "mixed", "uncertain"]
SpeakerResultState = Literal["accepted", "degraded_provider_result"]
TextConservationStatus = Literal["matched", "mismatched", "not_applicable"]


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
    reason_codes: tuple[str, ...]
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


def _normalized_text(values: Iterable[str]) -> str:
    return " ".join(unicodedata.normalize("NFKC", " ".join(values)).split())


def _provider_key(row: object) -> str:
    return str(getattr(row, "speaker_label", "") or "").strip()


def _is_unknown(key: str) -> bool:
    return key.upper() in UNKNOWN_PROVIDER_KEYS


def stable_speaker_key(processing_result_id: UUID, provider_speaker_key: str) -> str:
    digest = hashlib.sha256(provider_speaker_key.encode("utf-8")).hexdigest()[:24]
    return f"provider:{processing_result_id.hex}:{digest}"


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
    transcripts = tuple(
        sorted(transcript_rows, key=lambda row: (row.sequence, _decimal(row.start_seconds)))
    )
    providers_by_sequence = tuple(
        sorted(provider_rows, key=lambda row: (row.sequence, _decimal(row.start_seconds)))
    )
    providers = tuple(
        sorted(
            providers_by_sequence,
            key=lambda row: (_decimal(row.start_seconds), _decimal(row.end_seconds), row.sequence),
        )
    )
    names = speaker_names or {}
    versions = provider_versions or {}
    reasons: set[str] = set()

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
    if any(
        _decimal(current.start_seconds) < _decimal(previous.start_seconds)
        for previous, current in zip(providers_by_sequence, providers_by_sequence[1:], strict=False)
    ):
        reasons.add("impossible_provider_chronology")

    transcript_texts = {
        _normalized_text((row.text,)) for row in transcripts if _normalized_text((row.text,))
    }
    provider_text_counts = Counter(
        _normalized_text((row.text,)) for row in providers if _normalized_text((row.text,))
    )
    duplicated_full_texts = {
        text
        for text, count in provider_text_counts.items()
        if count > 1 and text in transcript_texts
    }
    duplicate_text_count = sum(provider_text_counts[text] for text in duplicated_full_texts)
    if duplicate_text_count:
        reasons.add("duplicated_full_text")

    transcript_by_role = {
        role: _normalized_text(
            row.text for row in transcripts if row.source_role == role and row.text.strip()
        )
        for role in {row.source_role for row in transcripts}
    }
    provider_by_role = {
        role: _normalized_text(
            row.text for row in providers if row.source_role == role and row.text.strip()
        )
        for role in {row.source_role for row in providers}
    }
    transcript_text = _normalized_text(transcript_by_role.values())
    if not transcript_text:
        conservation: TextConservationStatus = "not_applicable"
    elif transcript_by_role == provider_by_role:
        conservation = "matched"
    else:
        conservation = "mismatched"
        reasons.add("text_conservation_mismatch")

    unknown_durations: dict[str, Decimal] = defaultdict(Decimal)
    for provider in providers:
        key = _provider_key(provider)
        if _is_unknown(key):
            unknown_durations[key.upper()] += max(
                Decimal("0"),
                _decimal(provider.end_seconds) - _decimal(provider.start_seconds),
            )
    unknown_tiny_count = sum(
        1 for duration in unknown_durations.values() if duration <= TINY_UNKNOWN_SECONDS
    )
    if unknown_tiny_count:
        reasons.add("unknown_tiny_identity")

    multi_label_conflict_count = 0
    for transcript in transcripts:
        labels = {
            _provider_key(provider)
            for provider in providers
            if min(_decimal(transcript.end_seconds), _decimal(provider.end_seconds))
            > max(_decimal(transcript.start_seconds), _decimal(provider.start_seconds))
        }
        if len(labels) > 1:
            multi_label_conflict_count += 1

    degraded = bool(reasons) or not providers
    if not providers:
        reasons.add("provider_turns_unavailable")
    result_state: SpeakerResultState = "degraded_provider_result" if degraded else "accepted"

    diagnostics = SpeakerTurnDiagnostics(
        result_state=result_state,
        defect_origin="provider" if degraded else None,
        reason_codes=tuple(sorted(reasons)),
        raw_turn_count=len(providers),
        accepted_turn_count=0 if degraded else sum(bool(row.text.strip()) for row in providers),
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

    if degraded:
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
    overlap_ids: set[str] = set()
    for index, row in enumerate(providers):
        row_id = _source_id(row)
        if any(
            min(_decimal(row.end_seconds), _decimal(other.end_seconds))
            > max(_decimal(row.start_seconds), _decimal(other.start_seconds))
            for other in providers[:index]
        ):
            overlap_ids.add(row_id)
            overlap_ids.update(
                _source_id(other)
                for other in providers[:index]
                if min(_decimal(row.end_seconds), _decimal(other.end_seconds))
                > max(_decimal(row.start_seconds), _decimal(other.start_seconds))
            )

    accepted_turns: list[CanonicalSpeakerTurn] = []
    confirmed_keys: list[str] = []
    for row in providers:
        if not row.text.strip():
            continue
        provider_key = _provider_key(row)
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
            speaker_label = names.get(speaker_key, canonical_label)
            attribution_state = "confirmed"
            if speaker_key not in confirmed_keys:
                confirmed_keys.append(speaker_key)
        accepted_turns.append(
            CanonicalSpeakerTurn(
                turn_id=_turn_id(processing_result_id, _source_id(row)),
                source_segment_id=_source_id(row),
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
                overlap=_source_id(row) in overlap_ids,
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
