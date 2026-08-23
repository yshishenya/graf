from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import WORKSPACE_ID
from twobrain_rec_server.api.meeting_detection import _assisted_auto_start_policy
from twobrain_rec_server.auth.context import TenantScope


def meeting_detection_payload(**overrides: object) -> dict[str, object]:
    started = datetime(2026, 7, 8, 9, 0, tzinfo=UTC)
    payload: dict[str, object] = {
        "schemaVersion": 1,
        "clientVersion": "macos-test-1",
        "platform": "macos",
        "osVersionMajor": "15",
        "registryVersion": "2026.07.08.1",
        "candidateFilterVersion": "vks-filter-1",
        "createdAt": started.isoformat().replace("+00:00", "Z"),
        "rollupWindow": {
            "bucket": "day",
            "startedAt": started.isoformat().replace("+00:00", "Z"),
            "endedAt": (started + timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
        },
        "policy": {
            "detectionMode": "detect_and_ask",
            "uploadMode": "automatic_candidate_upload",
            "unknownIdentityUploadAllowed": True,
        },
        "targetRollups": [
            {
                "targetId": "yandex_telemost",
                "targetFamily": "native_app",
                "supportMode": "prompt_enabled",
                "signalFamilies": ["macos_audio_hal_assertion"],
                "outcomes": {"observed": 2, "promptEligible": 1, "prompted": 1},
                "durationBuckets": {"over5m": 1},
                "reasonCodes": ["stable_mic_duration"],
            }
        ],
        "unknownNativeAppRollups": [
            {
                "identityMode": "raw_candidate_allowed",
                "uploadEligibility": "server_candidate_upload",
                "candidateScore": 6,
                "candidateReasons": ["stable_mic_duration", "vks_name_token"],
                "bundleId": "ru.example.vks",
                "displayName": "Example VKS",
                "signingTeamId": "ABCDE12345",
                "version": "1.0.0",
                "stableObservationCount": 3,
                "durationBuckets": {"over5m": 1},
                "manualRecordNearbyCount": 1,
                "calendarOrJoinHintCount": 1,
            }
        ],
        "resourceRollup": {
            "cpuP95PercentBucket": "under_1",
            "memoryOverheadBucketMb": "under_10",
            "parserRestartCount": 0,
            "droppedEventCount": 0,
            "diskBytesWritten": 1024,
            "uploadAttemptCount": 1,
        },
    }
    payload.update(overrides)
    return payload


def test_openapi_exposes_meeting_detection_telemetry_endpoint(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    path = "/api/v1/desktop/meeting-detection/telemetry"

    assert path in openapi["paths"]
    operation = openapi["paths"][path]["post"]
    assert operation["operationId"] == "createMeetingDetectionTelemetry"
    assert "MeetingDetectionTelemetryRequest" in str(operation["requestBody"])
    assert "MeetingDetectionTelemetryResponse" in str(operation["responses"]["201"])
    assert "Idempotency-Key" in str(operation["parameters"])
    assert "audio" not in str(operation["responses"]["201"]).lower()


def test_openapi_exposes_meeting_detection_registry_endpoint(client: TestClient) -> None:
    openapi = client.get("/openapi.json").json()
    path = "/api/v1/desktop/meeting-detection/target-registry"

    assert path in openapi["paths"]
    operation = openapi["paths"][path]["get"]
    assert operation["operationId"] == "getMeetingDetectionTargetRegistry"
    assert "MeetingDetectionRegistryResponse" in str(operation["responses"]["200"])
    assert "304" in operation["responses"]
    assert "If-None-Match" in str(operation["parameters"])
    assert "audio" not in str(operation["responses"]["200"]).lower()


def test_meeting_detection_telemetry_contract_accepts_metadata_only_payload(client: TestClient) -> None:
    response = client.post(
        "/api/v1/desktop/meeting-detection/telemetry",
        headers=auth_headers() | {"Idempotency-Key": "meeting-detection:test-contract-001"},
        json=meeting_detection_payload(),
    )

    assert response.status_code == 201
    body = response.json()
    assert body["dedupe_status"] == "created"
    assert body["accepted_target_rollup_count"] == 1
    assert body["accepted_candidate_count"] == 1
    assert body["suppressed_candidate_count"] == 0
    assert body["registry_version"] == "2026.07.08.1"
    assert body["next_upload_after"]


def test_meeting_detection_registry_contract_returns_metadata_only_registry(client: TestClient) -> None:
    response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    body = response.json()
    assert body["schemaVersion"] == 1
    assert body["registryVersion"] == "2026.07.21.1"
    assert body["etag"] == response.headers["etag"].strip('"')
    assert body["nonTargetRules"] == []
    assert any(target["id"] == "yandex_telemost" for target in body["targets"])
    exported = str(body).lower()
    for forbidden in (
        "passcode",
        "transcript",
        "audio_url",
        "audiourl",
        "audio_bytes",
        "audiobytes",
        "raw_audio",
        "rawaudio",
    ):
        assert forbidden not in exported


def test_meeting_detection_registry_policy_is_fail_closed_and_workspace_scoped(
    client: TestClient,
) -> None:
    settings = client.app.state.settings
    default_response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    assert "assistedAutoStartPolicy" not in default_response.json()

    settings.assisted_auto_start_enabled = True
    settings.assisted_auto_start_workspace_id = WORKSPACE_ID
    settings.assisted_auto_start_policy_version = "2026.08.12.1"
    settings.assisted_auto_start_acknowledgement_version = "2026.08.12.1"
    settings.assisted_auto_start_policy_issued_at = datetime.now(UTC) - timedelta(days=1)
    settings.assisted_auto_start_policy_expires_at = datetime.now(UTC) + timedelta(days=30)

    settings.assisted_auto_start_workspace_id = UUID("20000000-0000-0000-0000-000000000099")
    wrong_workspace_response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    assert "assistedAutoStartPolicy" not in wrong_workspace_response.json()

    settings.assisted_auto_start_workspace_id = WORKSPACE_ID

    enabled_response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    policy = enabled_response.json()["assistedAutoStartPolicy"]
    assert policy["enabled"] is True
    assert policy["scope"] == "workspace"
    assert policy["policyRef"].startswith("sha256:")
    assert policy["acknowledgementSubjectRef"].startswith("sha256:")
    assert policy["deviceRef"].startswith("sha256:")
    assert str(WORKSPACE_ID) not in str(policy)
    assert enabled_response.headers["etag"] != default_response.headers["etag"]

    settings.assisted_auto_start_policy_issued_at = datetime.now(UTC) + timedelta(days=1)
    future_response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    assert "assistedAutoStartPolicy" not in future_response.json()

    settings.assisted_auto_start_policy_issued_at = datetime.now(UTC) - timedelta(days=1)
    settings.assisted_auto_start_policy_expires_at = datetime.now(UTC) - timedelta(seconds=1)
    expired_response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    assert "assistedAutoStartPolicy" not in expired_response.json()


def test_meeting_detection_registry_global_policy_binds_scope_without_cross_workspace_refs(
    client: TestClient,
) -> None:
    settings = client.app.state.settings
    settings.assisted_auto_start_enabled = True
    settings.assisted_auto_start_all_workspaces = True
    settings.assisted_auto_start_all_workspaces_approved = True
    settings.assisted_auto_start_workspace_id = None
    settings.assisted_auto_start_policy_version = "2026.08.23.1"
    settings.assisted_auto_start_acknowledgement_version = "2026.08.23.1"
    settings.assisted_auto_start_policy_issued_at = datetime.now(UTC) - timedelta(days=1)
    settings.assisted_auto_start_policy_expires_at = datetime.now(UTC) + timedelta(days=30)

    response = client.get(
        "/api/v1/desktop/meeting-detection/target-registry",
        headers=auth_headers(),
    )
    policy = response.json()["assistedAutoStartPolicy"]
    assert policy["scope"] == "all_workspaces"

    base_scope = TenantScope(
        organization_id=UUID("10000000-0000-0000-0000-000000000001"),
        workspace_id=UUID("20000000-0000-0000-0000-000000000001"),
        user_id=UUID("30000000-0000-0000-0000-000000000001"),
        device_id=UUID("40000000-0000-0000-0000-000000000001"),
    )
    other_scope = TenantScope(
        organization_id=base_scope.organization_id,
        workspace_id=UUID("20000000-0000-0000-0000-000000000099"),
        user_id=UUID("30000000-0000-0000-0000-000000000099"),
        device_id=UUID("40000000-0000-0000-0000-000000000099"),
    )
    first = _assisted_auto_start_policy(settings=settings, tenant_scope=base_scope)
    second = _assisted_auto_start_policy(settings=settings, tenant_scope=other_scope)
    assert first is not None and second is not None
    assert first["scope"] == second["scope"] == "all_workspaces"
    assert first["policyRef"] == second["policyRef"]
    assert first["acknowledgementSubjectRef"] != second["acknowledgementSubjectRef"]
    assert first["deviceRef"] != second["deviceRef"]
