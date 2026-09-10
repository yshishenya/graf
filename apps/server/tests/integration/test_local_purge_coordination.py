from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.db.models import LocalPurgeTask

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_local_purge_acknowledgement_updates_task_and_deletion_report(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={
            "state": "acknowledged",
            "reason_code": "local_buffers_purged",
            "client_version": "local-macos-test",
        },
    )

    assert ack.status_code == 200
    assert ack.json()["state"] == "acknowledged"

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    local_rows = report.json()["local_purge"]
    assert len(local_rows) == 1
    assert local_rows[0]["task_id"] == task["task_id"]
    assert local_rows[0]["state"] == "acknowledged"
    artifact_rows = report.json()["artifact_states"]
    local_artifact = next(row for row in artifact_rows if row["artifact_class"] == "local_desktop_buffer")
    assert local_artifact["state"] == "local_acknowledged"


def test_expired_local_purge_converges_report_and_accepts_verified_late_ack(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202
    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]

    async def expire_task() -> None:
        async with client.app_state["sessionmaker"]() as db:
            stored = await db.scalar(select(LocalPurgeTask).where(LocalPurgeTask.id == task["task_id"]))
            assert stored is not None
            stored.expires_at = datetime.now(UTC) - timedelta(minutes=1)
            await db.commit()

    asyncio.run(expire_task())
    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    local_row = report.json()["local_purge"][0]
    assert local_row["state"] == "expired"
    artifact_row = next(
        row for row in report.json()["artifact_states"] if row["artifact_class"] == "local_desktop_buffer"
    )
    assert artifact_row["state"] == "local_expiry_relied_upon"

    late_ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={"state": "acknowledged", "reason_code": "local_buffers_purged"},
    )
    assert late_ack.status_code == 200
    assert late_ack.json()["state"] == "acknowledged"
    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report", headers=auth_headers(),
    )
    assert report.json()["local_purge"][0]["state"] == "acknowledged"


def test_local_purge_acknowledgement_rejects_private_local_path_payloads(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={
            "state": "acknowledged",
            "reason_code": "/Users/person/Library/Application Support/2brain/private.wav",
        },
    )

    assert ack.status_code == 422
    assert "local_path" not in ack.text.lower()


def test_local_purge_acknowledgement_rejects_unverified_success(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={
            "state": "acknowledged",
            "reason_code": "local_purge_unverified",
            "client_version": "local-macos-test",
        },
    )

    assert ack.status_code == 422
    assert ack.json()["code"] == "local_purge_unverified_ack"


def test_failed_local_purge_acknowledgement_updates_report_without_private_payload(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={
            "state": "failed",
            "reason_code": "device_storage_locked",
            "client_version": "local-macos-test",
        },
    )

    assert ack.status_code == 200
    assert ack.json()["state"] == "failed"
    assert ack.json()["safe_reason"] == "device_storage_locked"

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    local_artifact = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "local_desktop_buffer")
    assert local_artifact["state"] == "retryable_failed"
    assert local_artifact["safe_reason"] == "Local purge acknowledgement failed"
    serialized = report.text.lower()
    assert "/users/" not in serialized
    assert "storage_object_key" not in serialized


def test_unverified_local_purge_acknowledgement_updates_report_as_safe_failure(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    ack = client.post(
        task["ack_url"],
        headers=auth_headers(),
        json={
            "state": "failed",
            "reason_code": "local_purge_unverified",
            "client_version": "local-macos-test",
        },
    )

    assert ack.status_code == 200
    assert ack.json()["state"] == "failed"
    assert ack.json()["safe_reason"] == "local_purge_unverified"

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )
    assert report.status_code == 200
    local_artifact = next(row for row in report.json()["artifact_states"] if row["artifact_class"] == "local_desktop_buffer")
    assert local_artifact["state"] == "retryable_failed"
    assert "/users/" not in report.text.lower()


def test_ensure_task_is_repeatable_and_rejects_live_recording(client):
    seeds = seed_cabinet_meetings(client)
    url = f"/api/v1/desktop/meetings/{seeds.ready_id}/local-purge-task"
    assert client.post(url, headers=auth_headers()).status_code == 409
    assert client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(), json={"confirmation_boundary": BOUNDED_COPY},
    ).status_code == 202
    first = client.post(url, headers=auth_headers())
    second = client.post(url, headers=auth_headers())
    assert first.status_code == second.status_code == 200
    assert first.json()["task_id"] == second.json()["task_id"]
    assert len(client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"]) == 1


def test_new_device_gets_own_task_without_acknowledging_old_device(client):
    from uuid import uuid4

    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.db.models import RegisteredDevice

    seeds = seed_cabinet_meetings(client)
    assert client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(), json={"confirmation_boundary": BOUNDED_COPY},
    ).status_code == 202
    old = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]
    device_id = uuid4()

    async def register():
        async with client.app_state["sessionmaker"]() as db:
            db.add(RegisteredDevice(id=device_id, workspace_id=WORKSPACE_ID, user_id=USER_ID,
                                    device_public_id="synthetic-new-device"))
            await db.commit()
    asyncio.run(register())
    headers = auth_headers() | {"X-Device-Id": str(device_id)}
    url = f"/api/v1/desktop/meetings/{seeds.ready_id}/local-purge-task"
    new = client.post(url, headers=headers)
    assert new.status_code == 200
    assert new.json()["task_id"] != old["task_id"]
    assert client.post(url, headers=headers).json()["task_id"] == new.json()["task_id"]
    assert client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][0]["state"] == "pending"
