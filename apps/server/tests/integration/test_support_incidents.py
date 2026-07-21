import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import httpx
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_github import FakeGitHubIssueClient
from tests.unit.test_support_incident_redaction import safe_report_payload
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    SupportIncident,
    SupportIncidentRateLimitBucket,
)
from twobrain_rec_server.support.github_issues import GitHubIssueClient
from twobrain_rec_server.support.incidents import SUPPORT_INCIDENT_RATE_LIMIT_SCOPE

SUPPORT_SESSION_TOKEN = "support-incident-cookie-session-token"


def test_support_incident_success_persists_redacted_private_issue_link(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert response.status_code == 201
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    assert incident.incident_number is not None
    assert incident.incident_number.startswith("CUST-")
    assert incident.github_issue_number == 123
    assert incident.status == "synced"
    assert incident.affected_count == 1
    assert incident.latest_safe_report_json["redaction_state"] == "metadata_only"
    assert "raw_path" not in str(incident.latest_safe_report_json)
    assert len(fake_github.created_issues) == 1


def test_support_incident_duplicate_updates_existing_issue_and_aggregate(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )
    second = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["incident_id"] == first.json()["incident_id"]
    assert second.json()["incident_status"] == "synced"
    assert second.json()["dedupe_status"] == "updated"
    assert second.json()["affected_count"] == 2
    assert len(fake_github.created_issues) == 1
    assert len(fake_github.updated_issues) == 1
    assert "Affected count: `2`" in fake_github.updated_issues[0]["body"]


def test_support_incident_v2_duplicate_updates_one_issue_with_latest_safe_report(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    payload = safe_report_payload() | {
        "schema_version": "desktop-support-incident.v2",
        "client_report_fingerprint": "report_fpr_1234abcd",
        "client_dedupe_key": "support_dedupe_1234abcd",
        "canonical_stage": "server_access",
        "server_copy_state": "blocked",
        "server_access_state": "revoked",
        "server_next_action": "send_support_report",
    }

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=payload
    )
    second = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=payload
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["incident_id"] == first.json()["incident_id"]
    assert second.json()["dedupe_status"] == "updated"
    assert len(fake_github.created_issues) == 1
    assert len(fake_github.updated_issues) == 1
    assert "server_access" in fake_github.updated_issues[0]["body"]
    assert '"schema_version": "desktop-support-incident.v2"' in fake_github.updated_issues[0]["body"]


def test_support_incident_server_scope_overrides_payload_fingerprints_for_dedupe(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    spoofed_payload = safe_report_payload() | {
        "workspace_fingerprint": "ws_fpr_deadbeef",
        "user_fingerprint": "usr_fpr_deadbeef",
        "device_fingerprint": "dev_fpr_deadbeef",
        "safe_device_identifier": "device:dev_fpr_deadbeef",
    }

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )
    second = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=spoofed_payload
    )

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["affected_count"] == 2
    assert len(fake_github.created_issues) == 1
    assert len(fake_github.updated_issues) == 1
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    report = incident.latest_safe_report_json
    assert report["workspace_fingerprint"] != "ws_fpr_deadbeef"
    assert report["user_fingerprint"] != "usr_fpr_deadbeef"
    assert report["device_fingerprint"] != "dev_fpr_deadbeef"
    assert report["workspace_fingerprint"].startswith("ws_fpr_")
    assert report["user_fingerprint"].startswith("usr_fpr_")
    assert report["device_fingerprint"].startswith("dev_fpr_")
    assert report["safe_device_identifier"] == f"device:{report['device_fingerprint']}"
    assert report["dedupe_key"] == incident.dedupe_key


def test_support_incident_idempotency_replay_does_not_increment_or_mutate_github(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    headers = auth_headers() | {"Idempotency-Key": "support-incident:report_fpr_replay"}
    payload = safe_report_payload()

    first = client.post("/api/v1/desktop/support-incidents", headers=headers, json=payload)
    replay = client.post("/api/v1/desktop/support-incidents", headers=headers, json=payload)

    assert first.status_code == 201
    assert replay.status_code == 200
    assert replay.json()["incident_id"] == first.json()["incident_id"]
    assert replay.json()["affected_count"] == 1
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    assert incident.affected_count == 1
    assert incident.last_duplicate_received_at is None
    assert incident.last_idempotency_key_fingerprint.startswith("idem_fpr_")
    assert "report_fpr_replay" not in incident.last_idempotency_key_fingerprint
    assert incident.last_idempotency_report_fingerprint == incident.latest_safe_report_fingerprint
    assert incident.last_idempotency_report_fingerprint.startswith("report_fpr_")


def test_support_incident_idempotency_conflict_does_not_create_second_issue(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    headers = auth_headers() | {"Idempotency-Key": "support-incident:conflict-key"}

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=headers, json=safe_report_payload()
    )
    conflicting_payload = safe_report_payload() | {
        "problem_code": "custody.auth_required.local_retained",
        "failure_category": "auth_session",
    }
    conflict = client.post(
        "/api/v1/desktop/support-incidents", headers=headers, json=conflicting_payload
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "support_incident.idempotency_conflict"
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues


def test_support_incident_idempotency_conflict_for_same_dedupe_different_report(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    headers = auth_headers() | {"Idempotency-Key": "support-incident:conflict-same-dedupe"}

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=headers, json=safe_report_payload()
    )
    conflicting_payload = safe_report_payload() | {
        "local_recording_id_fingerprint": "rec_fpr_beef",
        "safe_recording_identity": "local:rec_fpr_beef",
    }
    conflict = client.post(
        "/api/v1/desktop/support-incidents", headers=headers, json=conflicting_payload
    )

    assert first.status_code == 201
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "support_incident.idempotency_conflict"
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues


def test_support_incident_aggregate_report_creates_one_issue_with_bounded_identities(
    client,
) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    payload = safe_report_payload() | {
        "affected_count": 5,
        "safe_affected_identities": [
            "affected_fpr_01",
            "affected_fpr_02",
            "affected_fpr_03",
            "affected_fpr_04",
            "affected_fpr_05",
        ],
    }

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=payload
    )

    assert response.status_code == 201
    assert response.json()["affected_count"] == 5
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    assert incident.affected_count == 5
    assert incident.safe_affected_identities == [
        "affected_fpr_01",
        "affected_fpr_02",
        "affected_fpr_03",
        "affected_fpr_04",
        "affected_fpr_05",
    ]
    assert len(fake_github.created_issues) == 1
    assert "Affected count: `5`" in fake_github.created_issues[0]["body"]


def test_support_incident_dependency_failure_persists_fallback_state(client) -> None:
    fake_github = FakeGitHubIssueClient(failure_reason_code="support_incident.github_unavailable")
    client.app.state.support_incident_github_client = fake_github

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert response.status_code == 202
    assert response.json()["incident_status"] == "pending_sync"
    assert response.json()["github_issue_number"] is None
    assert response.json()["incident_id"].startswith("CUST-")
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    assert incident.incident_number == response.json()["incident_id"]
    assert incident.status == "pending_github"
    assert incident.github_failure_code == "support_incident.github_unavailable"
    assert not fake_github.created_issues


def test_support_incident_github_timeout_is_safe_fallback(client) -> None:
    async def timeout_handler(_request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("synthetic timeout")

    client.app.state.support_incident_github_client = GitHubIssueClient(
        token="synthetic-server-token",
        transport=httpx.MockTransport(timeout_handler),
    )

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert response.status_code == 202
    assert response.json()["incident_status"] == "pending_sync"


def test_support_incident_configuration_failures_are_safe_fallbacks(client) -> None:
    for fake_github in (
        FakeGitHubIssueClient(repo_private=False),
        FakeGitHubIssueClient(missing_required_labels=("needs-triage",)),
    ):
        client.app.state.support_incident_github_client = fake_github
        response = client.post(
            "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
        )
        assert response.status_code == 202
        assert response.json()["incident_status"] == "pending_sync"
        assert not fake_github.created_issues


def test_support_incident_wrong_repo_config_does_not_mutate_github(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    client.app.state.settings.support_incident_github_repo = "public-support"

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert response.status_code == 202
    assert response.json()["incident_status"] == "pending_sync"
    assert not fake_github.created_issues
    assert not fake_github.updated_issues


def test_support_incident_rate_limit_bucket_is_durable_and_blocks_github(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    client.app.state.settings.support_incident_rate_limit_max_attempts = 1

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )
    second = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert first.status_code == 201
    assert second.status_code == 429
    sessionmaker = client.app_state["sessionmaker"]

    async def load_bucket() -> SupportIncidentRateLimitBucket:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncidentRateLimitBucket))

    bucket = asyncio.run(load_bucket())
    assert bucket.attempt_count == 2
    assert bucket.blocked_until is not None
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues


def test_cookie_authenticated_support_incident_requires_csrf_and_accepts_bound_token(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    session = client.portal.call(_seed_support_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, SUPPORT_SESSION_TOKEN)

    missing_csrf = client.post(
        "/api/v1/desktop/support-incidents",
        json=safe_report_payload(),
    )
    assert missing_csrf.status_code == 403
    assert missing_csrf.json()["code"] == "csrf_token_missing"

    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )
    accepted = client.post(
        "/api/v1/desktop/support-incidents",
        headers={"X-CSRF-Token": csrf_token},
        json=safe_report_payload(),
    )
    assert accepted.status_code == 201
    assert accepted.json()["incident_status"] == "synced"
    assert accepted.json()["incident_id"].startswith("CUST-")
    assert len(fake_github.created_issues) == 1


def test_production_support_incident_rejects_legacy_headers_without_session(client) -> None:
    client.app.state.settings.env = "production"
    client.app.state.support_incident_github_client = FakeGitHubIssueClient()

    response = client.post(
        "/api/v1/desktop/support-incidents",
        headers=auth_headers(),
        json=safe_report_payload(),
    )

    assert response.status_code == 401
    assert response.json()["code"] == "legacy_header_auth_disabled"


def test_pending_support_incident_sync_retries_by_correlation_number_only(client) -> None:
    fake_github = FakeGitHubIssueClient(failure_reason_code="support_incident.github_unavailable")
    client.app.state.support_incident_github_client = fake_github

    pending = client.post(
        "/api/v1/desktop/support-incidents",
        headers=auth_headers() | {"Idempotency-Key": "support-incident:pending-sync"},
        json=safe_report_payload(),
    )
    assert pending.status_code == 202
    incident_id = pending.json()["incident_id"]
    assert pending.json()["incident_status"] == "pending_sync"

    fake_github.failure_reason_code = None
    synced = client.post(
        f"/api/v1/desktop/support-incidents/{incident_id}/sync",
        headers=auth_headers(),
    )

    assert synced.status_code == 200
    assert synced.json()["incident_id"] == incident_id
    assert synced.json()["incident_status"] == "synced"
    assert synced.json()["github_issue_number"] == 123
    assert len(fake_github.created_issues) == 1


async def _seed_support_session(client) -> AuthSession:
    async with client.app_state["sessionmaker"]() as db:
        session = AuthSession(
            id=uuid4(),
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID,
            provider="support_incident_test",
            session_token_hash=hash_token(SUPPORT_SESSION_TOKEN),
            status="active",
            issued_at=datetime.now(UTC) - timedelta(minutes=1),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
            claims_fingerprint="support-incident-csrf",
        )
        db.add(session)
        await db.flush()
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=session.id,
                registered_device_id=DEVICE_ID,
                device_state="trusted",
            )
        )
        await db.commit()
        return session


def test_support_incident_rate_limit_is_not_bypassed_by_new_dedupe_key(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    client.app.state.settings.support_incident_rate_limit_max_attempts = 1
    changed_payload = safe_report_payload() | {
        "problem_code": "custody.auth_required.local_retained",
        "failure_category": "auth_session",
        "sync_conflict_state": "auth_required",
    }

    first = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )
    second = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=changed_payload
    )

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["code"] == "support_incident.rate_limited"
    sessionmaker = client.app_state["sessionmaker"]

    async def load_bucket() -> SupportIncidentRateLimitBucket:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncidentRateLimitBucket))

    bucket = asyncio.run(load_bucket())
    assert bucket.dedupe_key == SUPPORT_INCIDENT_RATE_LIMIT_SCOPE
    assert bucket.attempt_count == 2
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues
