"""A result view cannot invent evidence of local capture (T112)."""

import pytest

from twobrain_rec_server.cabinet.web import build_first_value_product_analytics_payload
from twobrain_rec_server.product_analytics.identity import build_safe_identity


def _first_value(**kwargs):
    return build_first_value_product_analytics_payload(
        stable_pseudonymous_user_id=build_safe_identity(
            user_source_id="synthetic-result-owner"
        ).stable_pseudonymous_user_id,
        result_state="ready",
        useful_output_present=True,
        useful_result_type="transcript",
        **kwargs,
    )


@pytest.mark.parametrize("capture", [False, None, True])
def test_first_value_preserves_capture_evidence_without_inventing_it(capture):
    payload = _first_value(first_recording_completed=capture)

    assert payload is not None
    assert payload["event_name"] == "first_value_session_completed"
    properties = payload["properties"]
    if capture is None:
        assert "first_recording_completed" not in properties
    else:
        assert properties["first_recording_completed"] is capture
    assert properties["first_result_viewed"] is True
    assert properties["useful_output_present"] is True
    assert properties["attribution_reliability"] == "unknown"


def test_first_value_requires_an_explicit_capture_decision():
    with pytest.raises(TypeError, match="first_recording_completed"):
        _first_value()


@pytest.mark.parametrize("capture", ["false", 0, 1, "", {}])
def test_first_value_rejects_non_boolean_capture_evidence(capture):
    with pytest.raises(ValueError, match="capture evidence"):
        _first_value(first_recording_completed=capture)


@pytest.mark.parametrize("state,present", [("processing", True), ("failed", True), ("ready", False)])
def test_capture_evidence_does_not_make_an_unready_result_eligible(state, present):
    assert build_first_value_product_analytics_payload(
        stable_pseudonymous_user_id=build_safe_identity(
            user_source_id="synthetic-result-owner"
        ).stable_pseudonymous_user_id,
        result_state=state,
        useful_output_present=present,
        useful_result_type="transcript",
        first_recording_completed=True,
    ) is None
