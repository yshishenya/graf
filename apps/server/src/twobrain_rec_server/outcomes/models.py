from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class OutcomeTranscriptSegment:
    segment_id: UUID
    sequence: int
    start_seconds: Decimal
    end_seconds: Decimal
    speaker_label: str
    source_role: str
    text: str
    speaker_key: str = ""
    provider_speaker_key: str | None = None
    attribution_state: str = "unknown"
    result_state: str = "accepted"


@dataclass(frozen=True, slots=True)
class OutcomeSourceReference:
    transcript_segment_id: UUID | None = None
    sequence: int | None = None
    start_seconds: float | None = None
    end_seconds: float | None = None
    speaker_label: str | None = None
    source_role: str | None = None
    evidence_kind: str = "segment"

    def as_json(self) -> dict[str, object]:
        return {
            "transcript_segment_id": str(self.transcript_segment_id)
            if self.transcript_segment_id is not None
            else None,
            "sequence": self.sequence,
            "start_seconds": self.start_seconds,
            "end_seconds": self.end_seconds,
            "speaker_label": self.speaker_label,
            "source_role": self.source_role,
            "evidence_kind": self.evidence_kind,
        }


@dataclass(frozen=True, slots=True)
class GeneratedOutcomeItem:
    category: str
    sequence: int
    text: str | None
    truth_label: str
    source_refs: list[OutcomeSourceReference] = field(default_factory=list)
    state: str = "available"
    owner_text: str | None = None
    due_date_text: str | None = None

    def as_store_item(self) -> dict[str, object]:
        return {
            "category": self.category,
            "sequence": self.sequence,
            "state": self.state,
            "text": self.text,
            "owner_text": self.owner_text,
            "due_date_text": self.due_date_text,
            "truth_label": self.truth_label,
            "source_refs_json": [ref.as_json() for ref in self.source_refs],
        }


@dataclass(frozen=True, slots=True)
class GeneratedOutcomePayload:
    category_states: dict[str, str]
    items_by_category: dict[str, list[GeneratedOutcomeItem]]

    @property
    def items(self) -> list[GeneratedOutcomeItem]:
        rows: list[GeneratedOutcomeItem] = []
        for category_items in self.items_by_category.values():
            rows.extend(category_items)
        return rows
