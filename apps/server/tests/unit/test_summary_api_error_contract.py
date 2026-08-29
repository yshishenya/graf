from __future__ import annotations

import pytest

from twobrain_rec_server.api.cabinet import (
    _SUMMARY_PUBLIC_REASON_ALIASES,
    _raise_summary_problem,
)
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.outcomes.ai_service import OutcomeGenerationTerminalError


@pytest.mark.parametrize(
    ("internal_code", "public_code", "status"),
    [
        ("summary_revision_conflict", "summary_revision_conflict", 409),
        ("meeting_deleting", "meeting_deleting", 409),
        ("summary_provider_outcome_ambiguous", "summary_generation_ambiguous", 409),
        ("summary_prompt_snapshot_corrupt", "summary_prompt_revoked", 409),
        ("summary_candidate_unavailable", "summary_generation_blocked", 404),
        ("summary_generation_forbidden", "summary_generation_blocked", 403),
        ("summary_generation_unavailable", "summary_dependency_unavailable", 503),
    ],
)
def test_summary_lifecycle_errors_use_stable_public_codes(
    internal_code: str,
    public_code: str,
    status: int,
) -> None:
    with pytest.raises(ProblemDetail) as raised:
        _raise_summary_problem(OutcomeGenerationTerminalError(internal_code))

    assert raised.value.code == public_code
    assert raised.value.status == status
    assert raised.value.detail is None


def test_unknown_summary_error_does_not_leak_exception_body() -> None:
    sensitive_body = "transcript=PRIVATE provider_response=SECRET prompt=HIDDEN"

    with pytest.raises(ProblemDetail) as raised:
        _raise_summary_problem(OutcomeGenerationTerminalError(sensitive_body))

    problem = raised.value
    assert problem.code == "summary_dependency_unavailable"
    assert problem.status == 503
    assert problem.detail is None
    assert sensitive_body not in repr(problem)


def test_non_string_summary_error_does_not_become_a_public_code() -> None:
    error = OutcomeGenerationTerminalError()
    error.args = (object(),)

    with pytest.raises(ProblemDetail) as raised:
        _raise_summary_problem(error)

    assert raised.value.code == "summary_dependency_unavailable"
    assert raised.value.detail is None


def test_internal_aliases_only_target_contract_codes() -> None:
    contract_codes = {
        "summary_type_not_found",
        "summary_type_unavailable",
        "summary_type_retired",
        "summary_generation_in_progress",
        "summary_generation_blocked",
        "summary_generation_deferred",
        "summary_generation_ambiguous",
        "summary_source_revision_stale",
        "summary_source_not_ready",
        "summary_source_empty",
        "transcript_generation_failed",
        "summary_revision_conflict",
        "summary_result_invalid",
        "summary_prompt_revoked",
        "summary_dependency_unavailable",
        "meeting_deleting",
        "summary_current_revision_missing",
        "summary_default_missing",
        "summary_legacy_state_ambiguous",
        "no_eligible_items",
        "no_selected_items",
        "focus_no_supported_topic",
        "focus_ambiguous",
        "focus_topic_catalog_capacity_exceeded",
    }

    assert set(_SUMMARY_PUBLIC_REASON_ALIASES.values()) <= contract_codes
