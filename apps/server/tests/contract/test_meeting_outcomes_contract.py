from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.api import schemas
from twobrain_rec_server.domain import statuses

EXPECTED_CATEGORIES = {
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "followups",
    "risks",
    "questions",
    "evidence",
}

EXPECTED_CATEGORY_STATES = {
    "available",
    "not_found",
    "not_inferable",
    "processing",
    "blocked",
    "unsafe",
    "unavailable",
}


def test_outcome_domain_enums_cover_review_contract_values() -> None:
    category_enum = getattr(statuses, "OutcomeCategory", None)
    category_state_enum = getattr(statuses, "OutcomeCategoryState", None)
    set_status_enum = getattr(statuses, "OutcomeSetStatus", None)
    attempt_status_enum = getattr(statuses, "OutcomeGenerationAttemptStatus", None)
    generator_kind_enum = getattr(statuses, "OutcomeGeneratorKind", None)

    assert category_enum is not None
    assert category_state_enum is not None
    assert set_status_enum is not None
    assert attempt_status_enum is not None
    assert generator_kind_enum is not None
    assert {item.value for item in category_enum} == EXPECTED_CATEGORIES
    assert {item.value for item in category_state_enum} == EXPECTED_CATEGORY_STATES
    assert "available" in {item.value for item in set_status_enum}
    assert "stored" in {item.value for item in attempt_status_enum}
    assert "deterministic_extractive" in {item.value for item in generator_kind_enum}
    assert statuses.DeletionArtifactClass.NOTES_SUMMARY.value == "notes_summary"


def test_notes_action_truth_schema_accepts_stored_outcome_items_and_provenance() -> None:
    source_ref = schemas.OutcomeSourceReferenceView(
        transcript_segment_id=uuid4(),
        sequence=3,
        start_seconds=12.5,
        end_seconds=18.0,
        speaker_label="Speaker 1",
        source_role="incoming",
        evidence_kind="segment",
    )
    item = schemas.OutcomeItemView(
        category="summary",
        sequence=0,
        text="Synthetic stored outcome text.",
        truth_label="supported",
        source_refs=[source_ref],
    )
    category = schemas.NotesActionCategoryState(
        state="available",
        label="Итоги готовы",
        reason="Stored outcome content is available.",
        readiness_impact="closes_gap",
        copy_key="notes.summary.available",
        items=[item],
    )
    not_found = schemas.NotesActionCategoryState(
        state="not_found",
        label="Не найдено",
        reason="Transcript does not support this category.",
        readiness_impact="closes_gap",
        copy_key="notes.decisions.not_found",
        items=[],
    )
    truth = schemas.NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=not_found,
        action_items=not_found,
        followups=not_found,
        risks=not_found,
        questions=not_found,
        evidence=category,
        source_basis="stored_output",
        provenance=schemas.OutcomeProvenanceView(
            generator_kind="deterministic_extractive",
            generator_version="outcomes-extractive-v1",
            generated_at=datetime(2026, 6, 25, tzinfo=UTC),
            latency_ms=1200,
        ),
    )

    assert truth.summary.items[0].source_refs[0].start_seconds == 12.5
    assert truth.decisions.state == "not_found"
    assert truth.provenance is not None
    assert truth.provenance.generator_kind == "deterministic_extractive"


def test_default_notes_action_truth_keeps_gap_open_until_stored_outcomes_exist() -> None:
    truth = schemas.default_notes_action_truth()

    assert truth.summary.state == "deferred"
    assert truth.source_basis == "policy_deferral"
    assert truth.summary.items == []
    assert truth.provenance is None
