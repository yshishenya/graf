from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, BaseModel, ConfigDict, Field


def _nonblank(value: str) -> str:
    if not value.strip():
        raise ValueError("text must not be blank")
    return value


ProtocolText = Annotated[str, AfterValidator(_nonblank)]
PROTOCOL_VERSION = "graf-meeting-protocol-v1"


class ProtocolObject(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ProtocolRef(ProtocolObject):
    sequence: int = Field(ge=0)
    quote: ProtocolText | None


class ProtocolNote(ProtocolObject):
    text: ProtocolText
    source_refs: list[ProtocolRef]


class ProtocolStatement(ProtocolNote):
    source_refs: list[ProtocolRef] = Field(min_length=1)


class ProtocolTopic(ProtocolObject):
    title: ProtocolText
    context: list[ProtocolStatement]
    discussion: list[ProtocolStatement]
    proposals: list[ProtocolStatement]
    outcome: list[ProtocolStatement]


class ProtocolTask(ProtocolObject):
    task: ProtocolText
    owner_text: ProtocolText | None
    due_date_text: ProtocolText | None
    source_refs: list[ProtocolRef] = Field(min_length=1)


class MeetingProtocol(ProtocolObject):
    schema_version: Literal["graf-meeting-protocol-v1"]
    title: ProtocolText
    date_and_time: ProtocolText | None
    input_type: ProtocolText
    meeting_type: ProtocolText
    participants: list[ProtocolText]
    executive_summary: list[ProtocolStatement]
    objectives: list[ProtocolStatement]
    topics: list[ProtocolTopic]
    decisions: list[ProtocolStatement]
    action_items: list[ProtocolTask]
    open_questions: list[ProtocolStatement]
    next_steps: list[ProtocolStatement]
    notes: list[ProtocolNote]


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
