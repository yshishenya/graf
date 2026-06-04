from uuid import UUID

from sqlalchemy import select
from twobrain_rec_server.db.models import IngestAuditEvent
from twobrain_rec_server.ingest.audit import record_audit_event
from twobrain_rec_server.ingest.store import persist_audit_event

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID


def test_ingest_audit_events_persist_actor_user_and_device(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "audit-actor-device", "duration_seconds": 60},
    )
    assert meeting.status_code == 200

    async def audit_events() -> list[IngestAuditEvent]:
        async with client.app_state["sessionmaker"]() as db:
            return list((await db.scalars(select(IngestAuditEvent).order_by(IngestAuditEvent.created_at))).all())

    import asyncio

    events = asyncio.run(audit_events())
    assert events
    for event in events:
        assert event.actor_user_id == USER_ID
        assert event.device_id == DEVICE_ID
        assert event.workspace_id == UUID(meeting.json()["workspace_id"])


def test_ingest_audit_events_preserve_operation_order_content_and_redaction(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "audit-order-content", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 4}},
    ).json()
    redacted_event = record_audit_event(
        event_type="manual_redaction_probe",
        workspace_id=WORKSPACE_ID,
        meeting_id=UUID(meeting["meeting_id"]),
        upload_session_id=UUID(session["session_id"]),
        actor_user_id=USER_ID,
        device_id=DEVICE_ID,
        metadata={
            "safe_key": "safe value",
            "token": "must-not-persist",
            "authorization": "Bearer must-not-persist",
            "very_long": "x" * 300,
        },
    )

    async def persist_probe_and_load() -> list[IngestAuditEvent]:
        async with client.app_state["sessionmaker"]() as db:
            await persist_audit_event(db, redacted_event)
        async with client.app_state["sessionmaker"]() as db:
            return list((await db.scalars(select(IngestAuditEvent).order_by(IngestAuditEvent.created_at))).all())

    import asyncio

    events = asyncio.run(persist_probe_and_load())
    assert [event.event_type for event in events] == [
        "meeting_created",
        "session_created",
        "manual_redaction_probe",
    ]
    assert events[0].metadata_json == {"local_recording_id": "audit-order-content"}
    assert events[1].meeting_id == UUID(meeting["meeting_id"])
    assert events[1].upload_session_id == UUID(session["session_id"])
    assert events[2].metadata_json == {"safe_key": "safe value", "very_long": "x" * 240}
    for event in events:
        assert event.workspace_id == WORKSPACE_ID
        assert event.actor_user_id == USER_ID
        assert event.device_id == DEVICE_ID
