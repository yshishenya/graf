"""A result view cannot invent evidence of local capture (T112)."""

import base64
import hmac
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import uuid4

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


@pytest.fixture
def result_binding():
    from twobrain_rec_server.cabinet.result_visibility import ResultViewBinding, ResultViewSource

    return ResultViewBinding(
        source=ResultViewSource(
            owner_id=uuid4(), workspace_id=uuid4(), meeting_id=uuid4(),
            media_revision_id=uuid4(), source_fingerprint="a" * 64,
            result_id=uuid4(), result_version=3, deletion_epoch=2,
            first_recording_completed=None,
        ),
        auth_session_id=uuid4(), session_device_id=uuid4(),
        block_type="transcript", block_digest="b" * 64, outcome_set_id=None,
    )


def test_result_proof_round_trip_is_bounded_and_expires_without_acceptance(result_binding):
    from twobrain_rec_server.cabinet.result_visibility import (
        issue_result_view_proof,
        verify_result_view_proof,
    )

    issued = datetime(2026, 11, 16, 10, tzinfo=UTC)
    secret = "synthetic-csrf-secret"
    token = issue_result_view_proof(result_binding, secret=secret, issued_at=issued)
    assert token is not None and len(token.encode("ascii")) <= 1536
    assert len(json.dumps({"proof": token}).encode()) <= 2048
    for seconds, expected in [(0, "valid"), (599, "valid"), (600, "expired"), (-1, "invalid")]:
        assert verify_result_view_proof(
            token, result_binding, secret=secret, now=issued + timedelta(seconds=seconds),
        ) == expected
    payload = json.loads(base64.urlsafe_b64decode(token.split(".")[0] + "==="))
    serialized = json.dumps(payload)
    assert secret not in serialized
    assert "text" not in serialized and "title" not in serialized
    assert "https" not in serialized and "stable_pseudonymous_user_id" not in serialized


@pytest.mark.parametrize("field", [
    "owner_id", "workspace_id", "meeting_id", "media_revision_id", "result_id",
    "source_fingerprint", "result_version", "deletion_epoch", "auth_session_id",
    "session_device_id", "block_type", "block_digest", "outcome_set_id",
])
def test_result_proof_binds_every_authority_source_version_and_block_field(result_binding, field):
    from twobrain_rec_server.cabinet.result_visibility import (
        issue_result_view_proof,
        verify_result_view_proof,
    )

    issued = datetime(2026, 11, 16, 10, tzinfo=UTC)
    token = issue_result_view_proof(result_binding, secret="synthetic", issued_at=issued)
    if field in {"source_fingerprint", "block_digest"}:
        value = "c" * 64
    elif field in {"result_version", "deletion_epoch"}:
        value = 4
    elif field == "block_type":
        value = "summary"
    else:
        value = uuid4()
    if hasattr(result_binding.source, field):
        changed = replace(result_binding, source=replace(result_binding.source, **{field: value}))
    else:
        changed = replace(result_binding, **{field: value})
    assert verify_result_view_proof(token, changed, secret="synthetic", now=issued) == "invalid"


@pytest.mark.parametrize("token", [None, "", "x" * 1537, "not-base64.signature", "é.signature"])
def test_result_proof_rejects_malformed_or_oversized_input(result_binding, token):
    from twobrain_rec_server.cabinet.result_visibility import verify_result_view_proof

    assert verify_result_view_proof(
        token, result_binding, secret="synthetic", now=datetime.now(UTC),
    ) == "invalid"


def test_result_proof_uses_a_distinct_signing_domain_and_rejects_unknown_fields(result_binding):
    from twobrain_rec_server.cabinet.result_visibility import (
        issue_result_view_proof,
        verify_result_view_proof,
    )

    issued = datetime(2026, 11, 16, 10, tzinfo=UTC)
    secret = "synthetic"
    token = issue_result_view_proof(result_binding, secret=secret, issued_at=issued)
    encoded, signature = token.split(".")
    csrf_signature = hmac.new(secret.encode(), f"{result_binding.auth_session_id}:{encoded}".encode(), sha256).hexdigest()
    assert signature != csrf_signature
    assert verify_result_view_proof(
        encoded + "." + csrf_signature, result_binding, secret=secret, now=issued,
    ) == "invalid"
    payload = json.loads(base64.urlsafe_b64decode(encoded + "==="))
    payload["trusted"] = True
    tampered = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    signed = hmac.new(secret.encode(), f"f273-result-view-v1:{tampered}".encode(), sha256).hexdigest()
    assert verify_result_view_proof(
        tampered + "." + signed, result_binding, secret=secret, now=issued,
    ) == "invalid"


@pytest.mark.parametrize("secret", [None, ""])
def test_missing_proof_secret_leaves_measurement_closed(result_binding, secret):
    from twobrain_rec_server.cabinet.result_visibility import issue_result_view_proof

    assert issue_result_view_proof(result_binding, secret=secret, issued_at=datetime.now(UTC)) is None
