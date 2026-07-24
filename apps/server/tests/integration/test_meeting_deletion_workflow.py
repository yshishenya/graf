from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

import twobrain_rec_server.deletion.service as deletion_service
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import set_artifact_policy
from twobrain_rec_server.db.models import (
    DispatchIntent,
    Meeting,
    MeetingDeletionArtifactState,
    MeetingDeletionReport,
    MeetingDeletionRequest,
    MeetingEgressAuditEvent,
    MeetingLifecycleAuditEvent,
    PurgeJournal,
    RecordingCalendarContextLink,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
)

BOUNDED_COPY = "Delete this meeting everywhere GRAF controls."


def test_deletion_reconciler_reloads_meetings_after_rollback(client, monkeypatch) -> None:
    """A failed item must not leave the next Meeting ORM row expired."""
    seeds = seed_cabinet_meetings(client)

    async def seed_journals() -> None:
        async with client.app_state["sessionmaker"]() as db:
            for meeting_id in (seeds.ready_id, seeds.processing_id):
                meeting = await db.get(Meeting, meeting_id)
                assert meeting is not None
                db.add(
                    PurgeJournal(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        artifact_class="object_store",
                        object_key=f"tests/reconcile/{meeting.id}",
                        state="pending",
                    )
                )
            await db.commit()

    asyncio.run(seed_journals())
    calls: list[UUID] = []

    async def fail_first_item(db, *, meeting: Meeting, storage, limit: int = 20) -> bool:
        calls.append(meeting.id)
        if len(calls) == 1:
            await db.rollback()
            return False
        return True

    monkeypatch.setattr(deletion_service, "_reconcile_orphan_purge_journals", fail_first_item)

    async def reconcile() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return await deletion_service.reconcile_deletion_purges(
                db,
                storage=None,
                limit=20,
            )

    assert asyncio.run(reconcile()) == 1
    assert len(calls) == 2
    assert set(calls) == {seeds.ready_id, seeds.processing_id}


def test_manual_deletion_persists_request_audit_report_and_meeting_lifecycle(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    persisted = asyncio.run(_load_deletion_rows(client, seeds.ready_id))
    assert persisted["meeting"].deletion_state == "active_purge_complete"
    assert persisted["request"].state == "active_purge_complete"
    assert persisted["request"].confirmation_boundary == BOUNDED_COPY
    assert persisted["audit"].event_type == "deletion_requested"
    assert persisted["report"].bounded_copy == BOUNDED_COPY
    assert {row.artifact_class for row in persisted["artifact_states"]} >= {
        "meeting_row",
        "audio_object",
        "playback_candidate",
        "playback_canonical",
        "normalization_attempt_temp",
        "normalization_job",
        "normalization_backfill",
        "transcript",
        "diarization",
        "mediascribe",
        "langfuse",
        "backup",
        "post_egress_copy",
    }


def test_manual_deletion_cancels_started_outcome_dispatch_and_keeps_workflow_reference(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_started_intent() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.scalar(select(Meeting).where(Meeting.id == seeds.ready_id))
            assert meeting is not None
            workflow_id = f"outcome-generation/{uuid4()}"
            db.add(
                DispatchIntent(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting.id,
                    candidate_id=uuid4(),
                    intent_kind="summary_generation",
                    idempotency_key=f"delete-dispatch-{uuid4()}",
                    state="started",
                    reconciliation_state="started",
                    payload_json={},
                    deletion_epoch=int(meeting.deletion_epoch or 0),
                    lease_expires_at=datetime.now(UTC) + timedelta(minutes=5),
                    external_workflow_id=workflow_id,
                    started_at=datetime.now(UTC),
                )
            )
            await db.commit()
            return workflow_id

    workflow_id = asyncio.run(seed_started_intent())
    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert response.status_code == 202

    async def load_intent() -> DispatchIntent:
        async with client.app_state["sessionmaker"]() as db:
            intent = await db.scalar(
                select(DispatchIntent).where(DispatchIntent.meeting_id == seeds.ready_id)
            )
            assert intent is not None
            return intent

    intent = asyncio.run(load_intent())
    assert intent.state == "cancelled"
    assert intent.reconciliation_state == "cancelled"
    assert intent.lease_expires_at is None
    assert intent.external_workflow_id == workflow_id


def test_098_deletion_report_accounts_for_calendar_context_artifact(client) -> None:
    # FR-041: a synthetic calendar context is named explicitly in lifecycle accounting.
    seeds = seed_cabinet_meetings(client)
    _seed_synthetic_calendar_context(client, seeds.ready_id)

    deletion = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    report = client.get(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-report",
        headers=auth_headers(),
    )

    assert deletion.status_code == 202
    assert report.status_code == 200
    calendar_rows = [
        row
        for row in report.json()["artifact_states"]
        if row["artifact_class"] == "calendar_context"
    ]
    assert len(calendar_rows) == 1
    assert calendar_rows[0]["control_scope"] == "controlled"
    assert calendar_rows[0]["state"] in {"purged", "metadata_retained"}


def test_098_failed_deletion_rolls_back_calendar_context_and_accounting(client) -> None:
    # FR-041, SC-010: fail-closed storage errors preserve pre-request synthetic lifecycle truth.
    seeds = seed_cabinet_meetings(client)
    _seed_synthetic_calendar_context(client, seeds.ready_id)
    original_storage = client.app.state.storage
    client.app.state.storage = object()
    try:
        response = client.post(
            f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
            headers=auth_headers(),
            json={"confirmation_boundary": BOUNDED_COPY},
        )
    finally:
        client.app.state.storage = original_storage
    truth = asyncio.run(_load_calendar_rollback_truth(client, seeds.ready_id))

    assert response.status_code == 503
    assert response.json()["code"] == "deletion_storage_unavailable"
    assert truth["meeting"].deletion_state == "none"
    assert truth["request"] is None
    assert truth["report"] is None
    assert truth["artifact_states"] == []
    assert truth["context"].context_state == "no_context"
    assert truth["context"].manual_override_state == "none"
    assert truth["context"].unlinked_at is None


def test_manual_deletion_purges_server_audio_objects_and_upload_temps(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def purge_targets() -> tuple[list[str], list[str]]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = (
                await db.scalars(
                    select(TrackArtifact)
                    .where(TrackArtifact.meeting_id == seeds.ready_id)
                    .order_by(TrackArtifact.track_role)
                )
            ).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject)
                    .where(
                        TemporaryUploadObject.media_revision_id == artifacts[0].media_revision_id
                    )
                    .order_by(TemporaryUploadObject.storage_object_key)
                )
            ).all()
            return [artifact.storage_object_key for artifact in artifacts], [
                temp.storage_object_key for temp in temps
            ]

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
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == seeds.ready_id)
                )
            ).all()
            temps = (
                await db.scalars(
                    select(TemporaryUploadObject).where(
                        TemporaryUploadObject.storage_object_key.in_(temp_keys)
                    )
                )
            ).all()
            return {artifact.status for artifact in artifacts}, {
                temp.cleanup_status for temp in temps
            }

    assert asyncio.run(purge_states()) == ({"purged"}, {"purged"})


def test_manual_deletion_purges_part_only_upload_object(client) -> None:
    seeds = seed_cabinet_meetings(client)
    object_key = f"workspace/{seeds.ready_id}/part-only-object"

    async def seed_part_only() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            session = UploadSession(
                meeting_id=meeting.id,
                media_revision_id=None,
                workspace_id=meeting.workspace_id,
                device_id=meeting.device_id,
                created_by_user_id=meeting.created_by_user_id,
                upload_strategy="server_mediated",
                status="pending",
                processing_status="not_submitted",
                expected_track_roles=["media"],
                expected_track_sizes={},
                max_package_bytes_snapshot=10_000,
                max_track_bytes_snapshot=10_000,
                expires_at=datetime.now(UTC) + timedelta(hours=1),
            )
            db.add(session)
            await db.flush()
            db.add(
                UploadPart(
                    upload_session_id=session.id,
                    track_role="media",
                    part_number=0,
                    byte_offset=0,
                    byte_length=4,
                    sha256="a" * 64,
                    storage_object_key=object_key,
                    status="accepted",
                )
            )
            await db.commit()

    asyncio.run(seed_part_only())
    storage = client.app.state["storage"]
    storage.objects[object_key] = b"part"

    response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )

    assert response.status_code == 202
    assert object_key not in storage.objects


def test_deletion_report_includes_safe_post_egress_limits_from_download_and_export_audit(
    client,
) -> None:
    seeds = seed_cabinet_meetings(client)
    set_artifact_policy(
        client, seeds.ready_id, transcript_download="allowed", package_export="allowed"
    )
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


def test_deletion_report_treats_stream_prepared_events_as_post_egress(client) -> None:
    seeds = seed_cabinet_meetings(client)

    async def seed_stream_egress() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, seeds.ready_id)
            assert meeting is not None
            for event_type in ("download_stream_prepared", "playback_stream_prepared"):
                db.add(
                    MeetingEgressAuditEvent(
                        workspace_id=meeting.workspace_id,
                        meeting_id=meeting.id,
                        actor_user_id=None,
                        device_id=None,
                        event_type=event_type,
                        artifact_class="audio",
                        policy_reason="server_mediated_review_playback",
                        outcome="prepared",
                        metadata_json={"artifact_class": "audio", "stream_state": "prepared"},
                    )
                )
            await db.commit()

    asyncio.run(seed_stream_egress())

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
    assert "post_egress_events:" in report.text
    assert "download_stream_prepared" in report.text
    assert "playback_stream_prepared" in report.text
    assert "stream_state" not in report.text


def test_deletion_report_activity_remains_metadata_only_after_local_purge_ack(client) -> None:
    seeds = seed_cabinet_meetings(client)
    delete_response = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_COPY},
    )
    assert delete_response.status_code == 202
    task = client.get("/api/v1/desktop/local-purge-tasks", headers=auth_headers()).json()["tasks"][
        0
    ]

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
            select(MeetingLifecycleAuditEvent).where(
                MeetingLifecycleAuditEvent.meeting_id == meeting_id
            )
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


def _seed_synthetic_calendar_context(client, meeting_id) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            if context is None:
                context = RecordingCalendarContextLink(
                    workspace_id=meeting.workspace_id,
                    meeting_id=meeting_id,
                )
                db.add(context)
            context.context_state = "no_context"
            context.context_confidence = "none"
            context.context_reasons_json = ["no_matching_event"]
            context.title_source = "generic"
            context.roster_source = "none"
            context.manual_override_state = "none"
            context.safe_reason_code = "no_matching_event"
            context.decision_source = "system_skip"
            context.candidate_event_ids_json = []
            context.candidate_count = 0
            context.matched_title_state = "unavailable"
            context.matched_roster_json = []
            context.matched_roster_state = "not_available"
            context.matched_roster_count = 0
            context.unlinked_at = None
            await db.commit()

    asyncio.run(seed())


async def _load_calendar_rollback_truth(client, meeting_id):
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        request = await db.scalar(
            select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting_id)
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
        context = await db.scalar(
            select(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.meeting_id == meeting_id
            )
        )
        return {
            "meeting": meeting,
            "request": request,
            "report": report,
            "artifact_states": artifact_states,
            "context": context,
        }
