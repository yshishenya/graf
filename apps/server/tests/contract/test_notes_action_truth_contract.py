from __future__ import annotations

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import (
    MeetingListItem,
    MeetingReviewResponse,
    NotesActionCategoryState,
    NotesActionTruthState,
)


def _category(state: str) -> NotesActionCategoryState:
    return NotesActionCategoryState(
        state=state,
        label=f"{state} label",
        reason=f"{state} reason",
        readiness_impact="keeps_gap_open" if state != "available" else "closes_gap",
        copy_key=f"notes.summary.{state}",
    )


def test_notes_action_truth_schema_accepts_contract_states() -> None:
    for state in ["available", "processing", "blocked", "unavailable", "deferred"]:
        truth = NotesActionTruthState(
            summary=_category(state),
            decisions=_category(state),
            action_items=_category(state),
            followups=_category(state),
            source_basis="stored_output" if state == "available" else "policy_deferral",
        )

        assert truth.summary.state == state
        assert truth.decisions.copy_key.endswith(state)
        assert truth.action_items.readiness_impact in {"closes_gap", "keeps_gap_open", "non_blocking"}


def test_notes_action_truth_schema_rejects_unknown_states() -> None:
    with pytest.raises(ValidationError):
        _category("optimistic_placeholder")


def test_list_and_detail_contracts_expose_notes_action_truth() -> None:
    assert "notes_action_truth" in MeetingListItem.model_fields
    assert "notes_action_truth" in MeetingReviewResponse.model_fields
