from __future__ import annotations

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.contract.test_meeting_detection_api_contract import meeting_detection_payload

TELEMETRY_PATH = "/api/v1/desktop/meeting-detection/telemetry"
ADMIN_REVIEW_PATH = "/api/v1/admin/meeting-detection"


def _create_candidate(client, key: str = "meeting-detection:admin-contract"):
    telemetry = client.post(
        TELEMETRY_PATH,
        headers=auth_headers() | {"Idempotency-Key": key},
        json=meeting_detection_payload(),
    )
    assert telemetry.status_code == 201
    review = client.get(ADMIN_REVIEW_PATH, headers=auth_headers())
    assert review.status_code == 200
    return review.json()["candidates"][0]


def test_openapi_exposes_admin_meeting_detection_actions(client) -> None:
    openapi = client.get("/openapi.json").json()

    for path in [
        "/api/v1/admin/meeting-detection",
        "/api/v1/admin/meeting-detection/candidates/{candidate_id}/mark-non-target",
        "/api/v1/admin/meeting-detection/candidates/{candidate_id}/merge",
        "/api/v1/admin/meeting-detection/candidates/{candidate_id}/add-diagnostic-only-draft",
        "/api/v1/admin/meeting-detection/candidates/{candidate_id}/request-validation",
        "/api/v1/admin/meeting-detection/registry-drafts/{draft_id}/publish",
    ]:
        assert path in openapi["paths"]


def test_admin_can_mark_candidate_non_target_without_prompt_enablement(client) -> None:
    candidate = _create_candidate(client)

    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/mark-non-target",
        headers=auth_headers(),
        json={"reason_code": "admin_marked_non_target"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "non_target"
    assert body["bundle_id"] == "ru.example.vks"


def test_admin_can_create_diagnostic_only_draft_from_candidate(client) -> None:
    candidate = _create_candidate(client, key="meeting-detection:admin-draft")

    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/add-diagnostic-only-draft",
        headers=auth_headers(),
        json={
            "target_id": "example_vks",
            "display_name": "Example VKS",
            "market": "russia",
            "reason_code": "candidate_runtime_observed",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["candidate"]["state"] == "diagnostic_only_draft"
    assert body["registry_draft"]["status"] == "draft"
    assert body["registry_draft"]["target_count"] > 1


def test_admin_can_publish_diagnostic_only_registry_draft(client) -> None:
    candidate = _create_candidate(client, key="meeting-detection:admin-publish")
    draft = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/add-diagnostic-only-draft",
        headers=auth_headers(),
        json={
            "target_id": "example_vks",
            "display_name": "Example VKS",
            "market": "russia",
            "reason_code": "candidate_runtime_observed",
        },
    )
    assert draft.status_code == 200

    response = client.post(
        f"{ADMIN_REVIEW_PATH}/registry-drafts/{draft.json()['registry_draft']['registry_version_id']}/publish",
        headers=auth_headers(),
        json={"reason_code": "candidate_runtime_observed"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "published"
    assert body["target_count"] > 1


def test_admin_can_request_candidate_validation(client) -> None:
    candidate = _create_candidate(client, key="meeting-detection:admin-validation")

    response = client.post(
        f"{ADMIN_REVIEW_PATH}/candidates/{candidate['candidate_id']}/request-validation",
        headers=auth_headers(),
        json={"validation_kind": "runtime", "reason_code": "runtime_validation_needed"},
    )

    assert response.status_code == 200
    assert response.json()["state"] == "validation_needed"
