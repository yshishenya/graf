from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from twobrain_rec_server.cabinet import view_models
from twobrain_rec_server.db.models import MeetingOutcomeItem, MeetingOutcomeSet
from twobrain_rec_server.outcomes.store import OUTCOME_GENERATOR_VERSION


def _outcome_set() -> MeetingOutcomeSet:
    return MeetingOutcomeSet(
        workspace_id=uuid4(),
        meeting_id=uuid4(),
        media_revision_id=uuid4(),
        processing_result_id=uuid4(),
        status="available",
        summary_state="available",
        key_points_state="available",
        decisions_state="not_found",
        action_items_state="not_inferable",
        followups_state="not_found",
        risks_state="not_found",
        questions_state="not_found",
        evidence_state="available",
        generator_kind="deterministic_extractive",
        generator_version=OUTCOME_GENERATOR_VERSION,
        generated_at=datetime(2026, 6, 25, tzinfo=UTC),
        latency_ms=820,
    )


def _outcome_item(outcome_set: MeetingOutcomeSet) -> MeetingOutcomeItem:
    return MeetingOutcomeItem(
        workspace_id=outcome_set.workspace_id,
        meeting_id=outcome_set.meeting_id,
        outcome_set_id=uuid4(),
        category="summary",
        sequence=0,
        state="available",
        text="Launch-safe stored outcome",
        truth_label="supported",
        source_refs_json=[
            {
                "sequence": 3,
                "start_seconds": 12.5,
                "end_seconds": 18.0,
                "speaker_label": "Speaker 1",
                "source_role": "local_microphone",
                "evidence_kind": "segment",
            }
        ],
    )


def test_stored_outcomes_map_to_available_categories_with_source_refs() -> None:
    outcome_set = _outcome_set()
    truth = view_models.notes_action_truth_state(
        status="ready",
        result=None,
        outcome_set=outcome_set,
        outcome_items=[_outcome_item(outcome_set)],
    )

    assert truth.source_basis == "stored_output"
    assert truth.summary.state == "available"
    assert truth.summary.readiness_impact == "closes_gap"
    assert truth.summary.items[0].text == "Launch-safe stored outcome"
    assert truth.summary.items[0].source_refs[0].start_seconds == 12.5
    assert truth.summary.items[0].source_refs[0].evidence_kind == "segment"
    assert truth.decisions.state == "not_found"
    assert truth.decisions.items == []
    assert truth.action_items.state == "not_inferable"
    assert truth.provenance is not None
    assert truth.provenance.generator_version == OUTCOME_GENERATOR_VERSION
    assert truth.provenance.latency_ms == 820


def test_stored_ai_outcome_without_evidence_kind_remains_renderable() -> None:
    outcome_set = _outcome_set()
    item = _outcome_item(outcome_set)
    item.source_refs_json = [{"sequence": 3, "start_seconds": 12.5}]

    truth = view_models.notes_action_truth_state(
        status="ready",
        result=None,
        outcome_set=outcome_set,
        outcome_items=[item],
    )

    assert truth.summary.items[0].source_refs[0].evidence_kind == "segment"


def test_list_mapping_preserves_category_truth_without_outcome_text() -> None:
    truth = view_models.notes_action_truth_state(
        status="ready",
        result=None,
        outcome_set=_outcome_set(),
        outcome_items=[],
    )

    assert truth.source_basis == "stored_output"
    assert truth.summary.state == "available"
    assert truth.summary.items == []
    assert truth.key_points.state == "available"
    assert truth.key_points.items == []
