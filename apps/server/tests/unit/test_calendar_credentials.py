import json

from twobrain_rec_server.api.problems import ProblemDetail, problem_response
from twobrain_rec_server.calendar.credentials import (
    calendar_connection_secret,
    credential_fingerprint,
    generate_credential_key,
    safe_credential_failure,
    seal_credential,
    sealed_credential_metadata,
    unseal_credential,
)


def test_credential_metadata_never_returns_raw_secret() -> None:
    metadata = sealed_credential_metadata(secret="synthetic-secret", secret_kind="app_password")

    assert metadata["secret_kind"] == "app_password"
    assert metadata["secret_fingerprint_sha256"] == credential_fingerprint("synthetic-secret")
    assert "synthetic-secret" not in str(metadata)
    assert "sealed_payload" not in metadata


def test_credential_fingerprint_is_stable_and_not_raw_secret() -> None:
    assert credential_fingerprint("synthetic-secret") == credential_fingerprint("synthetic-secret")
    assert credential_fingerprint("synthetic-secret") != "synthetic-secret"


def test_sealed_credential_round_trips_without_plaintext_payload() -> None:
    key = generate_credential_key()
    sealed = seal_credential("synthetic-secret", key)

    assert b"synthetic-secret" not in sealed
    assert unseal_credential(sealed, key) == "synthetic-secret"


def test_safe_credential_failures_never_include_provider_secrets() -> None:
    expected_codes = {
        "invalid_app_password": "invalid_credentials",
        "tenant_denied": "tenant_policy_denied",
        "provider_timeout": "provider_timeout",
        "rate_limited": "rate_limited",
    }

    for reason, expected_code in expected_codes.items():
        failure = safe_credential_failure(reason)
        assert failure["safe_error_code"] == expected_code
        assert "synthetic-secret" not in str(failure)


def test_calendar_connection_secret_packs_manual_url_without_url_credentials() -> None:
    packed = calendar_connection_secret(
        method_category="manual_url",
        caldav_url="https://calendar.example.test/dav/",
        username="owner@example.test",
        credential_input="synthetic-secret",
    )

    assert json.loads(packed) == {
        "caldav_url": "https://calendar.example.test/dav/",
        "username": "owner@example.test",
        "credential_input": "synthetic-secret",
    }
    assert (
        calendar_connection_secret(
            method_category="manual_url",
            caldav_url="https://owner:secret@calendar.example.test/dav/",
            username=None,
            credential_input="synthetic-secret",
        )
        is None
    )


def test_calendar_provider_problem_codes_are_retryable_and_metadata_only() -> None:
    response = problem_response(
        ProblemDetail(
            status=409,
            code="calendar_rate_limited",
            title="Calendar provider rate limited",
        )
    )
    body = json.loads(response.body)

    assert body["retry_class"] == "automatic"
    assert body["normal_user_action"] == "none"
    assert body["metadata_safety"] == "metadata_only"
