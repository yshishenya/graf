from __future__ import annotations

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

    assert category_enum is not None
    assert category_state_enum is not None
    assert set_status_enum is not None
    assert attempt_status_enum is not None
    assert {item.value for item in category_enum} == EXPECTED_CATEGORIES
    assert {item.value for item in category_state_enum} == EXPECTED_CATEGORY_STATES
    assert "available" in {item.value for item in set_status_enum}
    assert "stored" in {item.value for item in attempt_status_enum}
    assert statuses.DeletionArtifactClass.NOTES_SUMMARY.value == "notes_summary"


def test_notes_action_truth_schema_uses_one_full_protocol_and_provenance() -> None:
    from tests.fixtures.meeting_protocol import protocol_outcome
    from twobrain_rec_server.cabinet.view_models import stored_outcome_truth_state

    truth = stored_outcome_truth_state(protocol_outcome())
    assert truth.protocol.schema_version == "graf-meeting-protocol-v2"
    assert truth.protocol.topics[0].discussion[0].source_refs[0].start_seconds == 12.5
    assert truth.decisions.state == "not_found"
    assert truth.provenance.generator_kind == "litellm"
    assert not hasattr(schemas, "OutcomeItemView")
    assert "items" not in schemas.NotesActionCategoryState.model_fields


def test_default_notes_action_truth_keeps_gap_open_until_stored_outcomes_exist() -> None:
    truth = schemas.default_notes_action_truth()

    assert truth.summary.state == "deferred"
    assert truth.source_basis == "policy_deferral"
    assert truth.protocol is None
    assert truth.provenance is None
