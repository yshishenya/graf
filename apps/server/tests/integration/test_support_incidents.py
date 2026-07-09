import asyncio

import httpx
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_github import FakeGitHubIssueClient
from tests.unit.test_support_incident_redaction import safe_report_payload
from twobrain_rec_server.db.models import SupportIncident, SupportIncidentRateLimitBucket
from twobrain_rec_server.support.github_issues import GitHubIssueClient
from twobrain_rec_server.support.incidents import SUPPORT_INCIDENT_RATE_LIMIT_SCOPE


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
    assert incident.incident_number == "CUST-123"
    assert incident.github_issue_number == 123
    assert incident.status == "open"
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
    assert second.json()["incident_id"] == "CUST-123"
    assert second.json()["dedupe_status"] == "updated"
    assert second.json()["affected_count"] == 2
    assert len(fake_github.created_issues) == 1
    assert len(fake_github.updated_issues) == 1
    assert "Affected count: `2`" in fake_github.updated_issues[0]["body"]


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

    assert response.status_code == 503
    assert response.json()["code"] == "support_incident.github_unavailable"
    sessionmaker = client.app_state["sessionmaker"]

    async def load_incident() -> SupportIncident:
        async with sessionmaker() as session:
            return await session.scalar(select(SupportIncident))

    incident = asyncio.run(load_incident())
    assert incident.incident_number is None
    assert incident.status == "github_unavailable"
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

    assert response.status_code == 503
    assert response.json()["code"] == "support_incident.github_unavailable"


def test_support_incident_configuration_failures_are_safe_fallbacks(client) -> None:
    for fake_github in (
        FakeGitHubIssueClient(repo_private=False),
        FakeGitHubIssueClient(missing_required_labels=("needs-triage",)),
    ):
        client.app.state.support_incident_github_client = fake_github
        response = client.post(
            "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
        )
        assert response.status_code == 503
        assert response.json()["code"] == "support_incident.configuration_invalid"
        assert not fake_github.created_issues


def test_support_incident_wrong_repo_config_does_not_mutate_github(client) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    client.app.state.settings.support_incident_github_repo = "public-support"

    response = client.post(
        "/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload()
    )

    assert response.status_code == 503
    assert response.json()["code"] == "support_incident.configuration_invalid"
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
