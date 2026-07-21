from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_github import FakeGitHubIssueClient
from tests.unit.test_support_incident_redaction import safe_report_payload


def test_support_incident_contract_creates_private_issue_server_side(client: TestClient) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github

    response = client.post(
        "/api/v1/desktop/support-incidents",
        headers=auth_headers() | {"Idempotency-Key": "support-incident:synthetic"},
        json=safe_report_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["incident_id"].startswith("CUST-")
    assert body["incident_status"] == "synced"
    assert body["github_issue_number"] == 123
    assert body["dedupe_status"] == "created"
    assert body["copy_fallback_available"] is True
    assert body["user_message"] == f"Запрос принят и передан в поддержку. Номер: {body['incident_id']}"
    assert len(fake_github.created_issues) == 1
    assert "github_token" not in response.text


def test_support_incident_contract_v2_issue_exposes_searchable_safe_metadata(client: TestClient) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    payload = safe_report_payload() | {
        "schema_version": "desktop-support-incident.v2",
        "client_report_fingerprint": "report_fpr_1234abcd",
        "client_dedupe_key": "support_dedupe_1234abcd",
        "canonical_stage": "server_deletion",
        "server_copy_state": "deleted",
        "server_deletion_state": "complete",
        "server_access_state": "owner",
        "server_next_action": "send_support_report",
        "timeline": [
            {"event": "reconciled", "at": "2026-06-26T10:06:00Z", "source": "server_truth"}
        ],
    }

    response = client.post(
        "/api/v1/desktop/support-incidents",
        headers=auth_headers() | {"Idempotency-Key": "support-incident:v2-contract"},
        json=payload,
    )

    assert response.status_code == 201
    assert len(fake_github.created_issues) == 1
    issue = fake_github.created_issues[0]
    assert issue["title"].startswith("[114][P0][support/custody] T000:")
    assert "feature:114" in issue["labels"]
    assert "Канонический этап: `server_deletion`" in issue["body"]
    assert "report_fpr_1234abcd" in issue["body"]
    assert "/Users/" not in issue["body"]
    assert "token=redacted" not in issue["body"]


def test_support_incident_contract_rejects_unsafe_payload_with_copy_fallback(client: TestClient) -> None:
    client.app.state.support_incident_github_client = FakeGitHubIssueClient()
    payload = safe_report_payload()
    payload["raw_transcript_text"] = "transcript text: private words"

    response = client.post("/api/v1/desktop/support-incidents", headers=auth_headers(), json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "support_incident.unsafe_payload"
    assert response.json()["normal_user_action"] == "copy_safe_report"
    assert response.json()["custody"]["metadata_safety"] == "metadata_only"


def test_support_incident_contract_maps_fallback_problem_responses(client: TestClient) -> None:
    client.app.state.support_incident_github_client = FakeGitHubIssueClient()

    unsupported = safe_report_payload() | {"schema_version": "desktop-support-incident.v0"}
    unsupported_response = client.post("/api/v1/desktop/support-incidents", headers=auth_headers(), json=unsupported)
    assert unsupported_response.status_code == 422
    assert unsupported_response.json()["code"] == "support_incident.unsupported_schema"

    forbidden_response = client.post(
        "/api/v1/desktop/support-incidents",
        headers=auth_headers() | {"X-Workspace-Id": "20000000-0000-0000-0000-000000000099"},
        json=safe_report_payload(),
    )
    assert forbidden_response.status_code == 403

    client.app.state.support_incident_github_client = None
    config_response = client.post("/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload())
    assert config_response.status_code == 202
    assert config_response.json()["incident_status"] == "pending_sync"
    assert config_response.json()["github_issue_number"] is None


def test_support_incident_contract_rate_limit_blocks_github_mutation(client: TestClient) -> None:
    fake_github = FakeGitHubIssueClient()
    client.app.state.support_incident_github_client = fake_github
    client.app.state.settings.support_incident_rate_limit_max_attempts = 1

    first = client.post("/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload())
    second = client.post("/api/v1/desktop/support-incidents", headers=auth_headers(), json=safe_report_payload())

    assert first.status_code == 201
    assert second.status_code == 429
    assert second.json()["code"] == "support_incident.rate_limited"
    assert len(fake_github.created_issues) == 1
    assert not fake_github.updated_issues


def test_support_incident_sync_contract_has_no_report_request_body(client: TestClient) -> None:
    operation = client.app.openapi()["paths"]["/api/v1/desktop/support-incidents/{incident_id}/sync"]["post"]

    assert "requestBody" not in operation
    assert "SupportIncidentReportRequest" not in str(operation)
