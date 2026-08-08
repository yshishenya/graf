from __future__ import annotations

import json

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_retention_deletion_openapi_contract_is_exposed(client) -> None:
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]

    expected_operations = {
        "/api/v1/cabinet/meetings/{meeting_id}/deletion-requests": "createMeetingDeletionRequest",
        "/api/v1/cabinet/meetings/{meeting_id}/deletion-report": "getMeetingDeletionReport",
        "/api/v1/cabinet/meetings/{meeting_id}/lifecycle": "getMeetingLifecycleState",
        "/api/v1/cabinet/meetings/{meeting_id}/deletion-retry": "retryMeetingDeletion",
        "/api/v1/internal/retention/run": "runRetentionScan",
        "/api/v1/desktop/local-purge-tasks": "listDesktopLocalPurgeTasks",
        "/api/v1/desktop/local-purge-tasks/{task_id}/ack": "acknowledgeDesktopLocalPurgeTask",
    }

    for path, operation_id in expected_operations.items():
        assert path in paths
        assert any(operation["operationId"] == operation_id for operation in paths[path].values())


def test_deletion_request_and_report_contract_exposes_no_private_content(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 202
    body = response.json()
    assert body["meeting_id"] == str(seeds.ready_id)
    assert body["lifecycle"]["state"] == "active_purge_complete"
    assert body["lifecycle"]["can_view_report"] is True

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    serialized = json.dumps(report.json(), ensure_ascii=False).lower()
    assert "graf controls" in serialized
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "storage_object_key" not in serialized
    assert "external_job_id" not in serialized
    rows = {row["artifact_class"]: row for row in report.json()["artifact_states"]}
    assert rows["normalization_job"]["state"] == "metadata_retained"
    assert rows["normalization_attempt_temp"]["state"] == "not_applicable"
    assert rows["playback_candidate"]["state"] == "not_applicable"
    assert rows["playback_canonical"]["state"] == "not_applicable"
    assert rows["normalization_backfill"]["state"] == "not_applicable"

    dependency_classes = {row["artifact_class"] for row in report.json()["dependencies"]}
    assert dependency_classes >= {
        "mediascribe",
        "langfuse",
        "processing_workflow",
        "upload_temp",
        "diagnostics",
    }
    assert all(row["artifact_class"] not in dependency_classes for row in report.json()["artifact_states"])
    assert {row["control_scope"] for row in report.json()["dependencies"]} >= {"external", "controlled"}
    assert report.json()["post_egress_limits"][0]["state"] == "outside_2brain_control"
    assert report.json()["post_egress_limits"][0]["control_scope"] == "post_egress"
    assert report.json()["backup"]["safe_reason"] == "backup_expiry_days:30"
    activity = report.json()["activity"]
    assert [item["event_type"] for item in activity] == ["deletion_requested"]
    assert activity[0]["outcome"] == "accepted"
    assert activity[0]["actor_label"] == "Owner/Admin"


def test_retention_run_contract_returns_policy_snapshot_and_counts(client) -> None:
    response = client.post(
        "/api/v1/internal/retention/run",
        headers=auth_headers(),
        json={"limit": 10, "dry_run": True},
    )

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"evaluated", "created_requests", "skipped", "blocked", "policy_snapshot_id"}
    assert body["evaluated"] >= 0
    assert body["created_requests"] == 0
    assert body["policy_snapshot_id"] is not None


def test_local_purge_task_contract_is_device_scoped_and_metadata_only(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    tasks = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers())

    assert tasks.status_code == 200
    body = tasks.json()
    assert len(body["tasks"]) == 1
    task = body["tasks"][0]
    assert task["meeting_id"] == str(seeds.ready_id)
    assert task["task_type"] == "purge_local_buffers"
    assert task["state"] == "pending"
    assert task["safe_reason"] == "delete_requested"
    assert task["ack_url"].endswith(f"/api/v1/desktop/local-purge-tasks/{task['task_id']}/ack")

    serialized = json.dumps(body, ensure_ascii=False).lower()
    assert "/users/" not in serialized
    assert "storage_object_key" not in serialized
    assert "transcript" not in serialized
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "storage_object_key" not in serialized


def test_deletion_retry_guidance_is_safe_and_state_specific(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    retry = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-retry",
        headers=auth_headers(),
    )

    assert retry.status_code == 409
    body = retry.json()
    assert body["code"] == "deletion_retry_unavailable"
    assert "current lifecycle state" in body["detail"]
    assert SAFE_TRANSCRIPT_TEXT.lower() not in retry.text.lower()
