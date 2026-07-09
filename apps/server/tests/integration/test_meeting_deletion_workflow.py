from __future__ import annotations

import asyncio

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import set_artifact_policy
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    TemporaryUploadObject,
    TrackArtifact,
)

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_manual_deletion_persists_request_audit_report_and_meeting_lifecycle(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    persisted = asyncio.run(_load_deletion_rows(client, seeds.ready_id))
    assert persisted["meeting"].deletion_state == "deleting"
    assert persisted["request"].state == "deleting"
    assert persisted["request"].confirmation_boundary == BOUNDED_COPY
    assert persisted["audit"].event_type == "deletion_requested"
    assert persisted["report"].bounded_copy == BOUNDED_COPY
    assert {row.artifact_class for row in persisted["artifact_states"]} >= {
        "meeting_row",
        "audio_object",
        "transcript",
        "diarization",
        "mediascribe",
        "langfuse",
        "backup",
        "post_egress_copy",
    }


def test_manual_deletion_purges_server_audio_objects_and_upload_temps(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def purge_targets() -> tuple[list[str], list[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == seeds.ready_id).order_by(TrackArtifact.track_role)
                )
            ).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject)
                    .where(TemporaryUploadObject.media_revision_id == artifacts[0].media_revision_id)
                    .order_by(TemporaryUploadObject.storage_object_key)
                )
            ).all()
            return [artifact.storage_object_key for artifact in artifacts], [temp.storage_object_key for temp in temps]

    artifact_keys, temp_keys = asyncio.run(purge_targets())
    storage = client.app_state["storage"]
    assert all(key in storage.objects for key in artifact_keys + temp_keys)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    assert all(key not in storage.objects for key in artifact_keys + temp_keys)

    async def purge_states() -> tuple[set[str], set[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (await db.scalars(select(TrackArtifact).where(TrackArtifact.meeting_id == seeds.ready_id))).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject).where(TemporaryUploadObject.storage_object_key.in_(temp_keys))
                )
            ).all()
            return {artifact.status for artifact in artifacts}, {temp.cleanup_status for temp in temps}

    assert asyncio.run(purge_states()) == ({"purged"}, {"purged"})


def test_deletion_report_includes_safe_post_egress_limits_from_download_and_export_audit(client) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(client, seeds.ready_id, transcript_download="allowed", package_export="allowed")
    download = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/downloads/transcript",
        headers=auth_headers(),
    )
    export = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/exports",
        headers=auth_headers(),
        json={"artifact_classes": ["transcript"]},
    )
    assert download.status_code == 200
    assert export.status_code == 202

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    serialized = report.text.lower()
    assert "download_completed" in serialized
    assert "export_completed" in serialized
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "storage_object_key" not in serialized
    assert "share_token_hash" not in serialized


def test_deletion_report_treats_legacy_playback_completed_as_post_egress(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_playback_egress() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            db.add(
                MeetingEgressAuditEvent(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    actor_user_id=None,
                    device_id=None,
                    event_type="playback_completed",
                    artifact_class="audio",
                    policy_reason="server_mediated_review_playback",
                    outcome="completed",
                    metadata_json={"artifact_class": "audio", "source_mode": "stored_review_m4a"},
                )
            )
            await db.commit()

    asyncio.run(seed_playback_egress())

    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    assert "post_egress_events:playback_completed" in report.text
    assert "stored_review_m4a" not in report.text


def test_deletion_report_activity_remains_metadata_only_after_local_purge_ack(client) -> None:
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
        json={"state": "acknowledged", "reason_code": "local_buffers_purged"},
    )
    assert ack.status_code == 200

    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert report.status_code == 200
    activity = report.json()["activity"]
    assert [item["event_type"] for item in activity] == [
        "deletion_requested",
        "local_purge_acknowledged",
    ]
    assert activity[0]["actor_label"] == "Owner/Admin"
    assert activity[1]["actor_label"] == "Desktop device"
    serialized = report.text.lower()
    assert SAFE_TRANSCRIPT_TEXT.lower() not in serialized
    assert "/users/" not in serialized
    assert "storage_object_key" not in serialized


async def _load_deletion_rows(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        request = await db.scalar(
            select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting_id)
        )
        audit = await db.scalar(
            select(MeetingLifecycleAuditEvent).where(MeetingLifecycleAuditEvent.meeting_id == meeting_id)
        )
        report = await db.scalar(
            select(MeetingDeletionReport).where(MeetingDeletionReport.meeting_id == meeting_id)
        )
        artifact_states = (
            await db.scalars(
                select(MeetingDeletionArtifactState).where(
                    MeetingDeletionArtifactState.meeting_id == meeting_id
                )
            )
        ).all()
        return {
            "meeting": meeting,
            "request": request,
            "audit": audit,
            "report": report,
            "artifact_states": artifact_states,
        }
