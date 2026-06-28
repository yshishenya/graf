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
    assert body["incident_id"] == "CUST-123"
    assert body["github_issue_number"] == 123
    assert body["dedupe_status"] == "created"
    assert body["copy_fallback_available"] is True
    assert body["user_message"] == "Отчет отправлен. Мы разберемся. Номер: CUST-123"
    assert len(fake_github.created_issues) == 1
    assert "github_token" not in response.text


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
    assert config_response.status_code == 503
    assert config_response.json()["code"] == "support_incident.configuration_invalid"


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
