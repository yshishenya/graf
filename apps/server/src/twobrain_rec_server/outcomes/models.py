from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

PROTOCOL_SCHEMA_VERSION = "graf-meeting-protocol-v2"
PROTOCOL_LABELS = {
    "executive_summary": ("Ключевые итоги", "Executive Summary"),
    "objectives": ("Цели встречи", "Meeting objectives"),
    "topics": ("Ключевые обсуждения", "Key discussions"),
    "decisions": ("Принятые решения", "Decisions"),
    "action_items": ("Задачи", "Action items"),
    "open_questions": ("Открытые вопросы", "Open questions"),
    "next_steps": ("Следующие шаги", "Next steps"),
    "risks_and_constraints": ("Риски и ограничения", "Risks and constraints"),
    "notes": ("Примечания", "Notes"),
    "context": ("Контекст", "Context"), "discussion": ("Обсуждение", "Discussion"),
    "proposals_and_alternatives": ("Предложения и альтернативы", "Proposals and alternatives"),
    "outcome": ("Итог", "Outcome"),
}
MEETING_TYPE_LABELS = {
    "work": ("Рабочая", "Work"), "official": ("Официальная", "Official"),
    "customer": ("С клиентом", "Customer"), "hr": ("Кадровая", "HR"),
    "brainstorm": ("Обсуждение идей", "Brainstorm"),
    "retro_or_incident": ("Ретроспектива / разбор инцидента", "Retrospective / incident"),
    "interview": ("Интервью", "Interview"), "personal": ("Личная", "Personal"),
    "high_risk": ("Повышенной ответственности", "High-risk"),
    "mixed_or_unknown": ("Смешанная / не определено", "Mixed / unknown"),
}
SPEAKER_IDENTITY_NOTE = (
    "Имена спикеров указаны только в случаях их однозначной идентификации в расшифровке.",
    "Speaker names are shown only when unambiguously identified in the transcript.",
)
PROTOCOL_SECTIONS = (
    "executive_summary", "objectives", "topics", "decisions", "action_items",
    "open_questions", "next_steps", "risks_and_constraints", "notes",
)
TEMPLATE_PROTOCOL_SECTIONS = {
    "summary": ("executive_summary", "objectives"),
    "key_points": ("topics",),
    "decisions": ("decisions",),
    "action_items": ("action_items",),
    "followups": ("next_steps",),
    "risks": ("risks_and_constraints",),
    "questions": ("open_questions",),
    "evidence": ("notes",),
}
ProtocolSection = Literal[
    "executive_summary", "objectives", "topics", "decisions", "action_items",
    "open_questions", "next_steps", "risks_and_constraints", "notes",
]
StatementText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)]


class ProtocolObject(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)


class ProtocolSourceRef(ProtocolObject):
    sequence: Annotated[int, Field(ge=0)]
    quote: Annotated[str, Field(min_length=1, max_length=800)] | None


EvidenceRefs = Annotated[list[ProtocolSourceRef], Field(min_length=1, max_length=8)]
OptionalEvidenceRefs = Annotated[list[ProtocolSourceRef], Field(max_length=8)]


class ProtocolStatement(ProtocolObject):
    text: StatementText
    source_refs: EvidenceRefs


Statements = Annotated[list[ProtocolStatement], Field(max_length=500)]


class ProtocolDecision(ProtocolStatement):
    acceptance_source_refs: EvidenceRefs


class ProtocolAction(ProtocolObject):
    task: StatementText
    owner_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)] | None
    due_date_text: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)] | None
    task_source_refs: EvidenceRefs
    owner_source_refs: OptionalEvidenceRefs
    due_date_source_refs: OptionalEvidenceRefs

    @model_validator(mode="after")
    def check_field_evidence(self):
        if bool(self.owner_text) != bool(self.owner_source_refs):
            raise ValueError("protocol_owner_evidence_missing")
        if bool(self.due_date_text) != bool(self.due_date_source_refs):
            raise ValueError("protocol_deadline_evidence_missing")
        return self


class ProtocolTopic(ProtocolObject):
    title: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=240)]
    context: Statements
    discussion: Statements
    proposals_and_alternatives: Statements
    outcome: Statements

    @model_validator(mode="after")
    def check_topic_content(self):
        if not (self.context or self.discussion or self.proposals_and_alternatives or self.outcome):
            raise ValueError("protocol_empty_topic")
        return self


class ExtractedFact(ProtocolStatement):
    kind: Literal["context", "argument", "proposal", "decision", "question", "risk", "constraint", "correction"]
    status: Literal["stated", "tentative", "conditional", "confirmed", "rejected", "cancelled", "uncertain"]
    acceptance_source_refs: OptionalEvidenceRefs

    @model_validator(mode="after")
    def check_acceptance(self):
        if self.kind == "decision" and self.status == "confirmed" and not self.acceptance_source_refs:
            raise ValueError("extraction_acceptance_missing")
        return self


class ExtractedAction(ProtocolAction):
    commitment_status: Literal["proposed", "committed", "conditional", "cancelled", "uncertain"]
    due_status: Literal["absent", "tentative", "conditional", "agreed", "uncertain"]

    @model_validator(mode="after")
    def check_due_status(self):
        if (self.due_status == "absent") != (self.due_date_text is None):
            raise ValueError("extraction_due_status_invalid")
        return self


class FactualExtraction(ProtocolObject):
    facts: Annotated[list[ExtractedFact], Field(max_length=500)]
    actions: Annotated[list[ExtractedAction], Field(max_length=200)]


class MeetingProtocol(ProtocolObject):
    meeting_type: Literal[
        "work", "official", "customer", "hr", "brainstorm", "retro_or_incident",
        "interview", "personal", "high_risk", "mixed_or_unknown",
    ]
    objectives: Statements
    topics: Annotated[list[ProtocolTopic], Field(max_length=100)]
    decisions: Annotated[list[ProtocolDecision], Field(max_length=500)]
    action_items: Annotated[list[ProtocolAction], Field(max_length=500)]
    open_questions: Statements
    next_steps: Statements
    risks_and_constraints: Statements
    notes: Statements
    uncertain_sections: Annotated[list[ProtocolSection], Field(max_length=9)]
    # Generate the synthesis after the evidence-bearing record; render order is separate.
    executive_summary: Statements


class ProtocolFinding(ProtocolObject):
    code: Literal[
        "unsupported_claim", "missing_topic", "missing_decision", "missing_action",
        "wrong_owner", "wrong_deadline", "proposal_as_decision", "missed_correction",
        "incoherent", "insufficient_evidence",
    ]
    path: Annotated[str, Field(max_length=240)]
    source_refs: OptionalEvidenceRefs


class ProtocolVerification(ProtocolObject):
    verdict: Literal["pass", "fail"]
    findings: Annotated[list[ProtocolFinding], Field(max_length=500)]

    @model_validator(mode="after")
    def check_verdict(self):
        if (self.verdict == "pass") != (not self.findings):
            raise ValueError("protocol_verification_verdict_mismatch")
        return self


def protocol_without_evidence(value):
    if isinstance(value, list | tuple):
        return [protocol_without_evidence(child) for child in value]
    if isinstance(value, dict):
        return {
            key: protocol_without_evidence(child)
            for key, child in value.items()
            if not key.endswith("source_refs") and key not in {
                "quote", "source_result_id", "transcript_segment_id", "source_segment_ids", "source_links",
                "speaker_key", "attribution_state", "template_key", "template_version", "template_name", "detail_level",
            }
        }
    return value


def protocol_source_refs(value):
    """Walk the single nested protocol contract, including independent action refs."""
    if isinstance(value, list):
        for child in value:
            yield from protocol_source_refs(child)
    elif isinstance(value, dict):
        if "sequence" in value and "quote" in value:
            yield value
        else:
            for child in value.values():
                yield from protocol_source_refs(child)


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
