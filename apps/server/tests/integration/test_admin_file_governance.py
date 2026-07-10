from __future__ import annotations

import asyncio

from sqlalchemy import select

from tests.fixtures.admin import (
    DEFAULT_ADMIN_DEVICE_ID,
    DEFAULT_ADMIN_USER_ID,
    auth_headers_for,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    add_retained_playback_m4a,
    audit_events,
    replace_retained_audio_with_test_wav,
    set_artifact_policy,
)
from twobrain_rec_server.db.models import Meeting, MeetingDeletionRequest
from twobrain_rec_server.domain.statuses import (
    DeletionRequestSource,
    DeletionState,
    RetentionPolicyState,
)


def test_admin_file_list_detail_and_review_access_are_workspace_scoped(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A admin-review")
    headers = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)

    file_list = client.get("/api/v1/admin/files", headers=headers)
    detail = client.get(f"/api/v1/admin/files/{seeds.ready_id}", headers=headers)
    review = client.post(f"/api/v1/admin/files/{seeds.ready_id}/review-access", headers=headers)
    foreign_detail = client.get(f"/api/v1/admin/files/{seeds.foreign_id}", headers=headers)

    assert file_list.status_code == 200
    assert str(seeds.ready_id) in file_list.text
    assert str(seeds.foreign_id) not in file_list.text
    assert detail.status_code == 200
    assert detail.json()["meeting_id"] == str(seeds.ready_id)
    assert detail.json()["access"]["outcome"] == "allowed"
    assert review.status_code == 200
    assert review.json()["review_path"].endswith(str(seeds.ready_id))
    assert "storage_object_key" not in review.text
    assert foreign_detail.status_code == 404


def test_admin_download_and_export_use_admin_access_for_non_owned_meeting(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    headers = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)
    set_artifact_policy(
        client,
        seeds.ready_id,
        audio_download="allowed",
        transcript_download="allowed",
        package_export="allowed",
    )
    replace_retained_audio_with_test_wav(client, seeds.ready_id)
    add_retained_playback_m4a(client, seeds.ready_id, b"\x00\x00\x00\x18ftypM4A admin")

    detail = client.get(f"/api/v1/admin/files/{seeds.ready_id}", headers=headers)
    download = client.get(f"/api/v1/admin/files/{seeds.ready_id}/downloads/audio", headers=headers)
    export = client.post(
        f"/api/v1/admin/files/{seeds.ready_id}/exports",
        headers=headers,
        json={"artifact_classes": ["audio", "transcript"]},
    )

    assert detail.status_code == 200
    assert detail.json()["actions"]["download"] is True
    assert detail.json()["actions"]["export"] is True
    assert download.status_code == 200
    assert download.headers["content-type"].startswith("application/octet-stream")
    assert export.status_code == 202
    assert export.json()["status"] == "ready"
    assert {event.event_type for event in audit_events(client, seeds.ready_id)} >= {
        "download_requested",
        "download_stream_prepared",
        "export_requested",
        "export_completed",
    }


def test_admin_file_detail_reports_retention_and_post_egress_blocks(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    headers = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)

    asyncio.run(
        _set_meeting_states(
            client, seeds.ready_id, retention_state=RetentionPolicyState.BLOCKED.value
        )
    )
    retention_detail = client.get(f"/api/v1/admin/files/{seeds.ready_id}", headers=headers)
    asyncio.run(
        _set_meeting_states(
            client,
            seeds.ready_id,
            retention_state=RetentionPolicyState.ACTIVE.value,
            deletion_state=DeletionState.POST_EGRESS_LIMIT.value,
        )
    )
    post_egress_detail = client.get(f"/api/v1/admin/files/{seeds.ready_id}", headers=headers)

    assert retention_detail.status_code == 200
    assert (
        retention_detail.json()["access"]["outcome"]
        == "unavailable_retention_or_lifecycle_block"
    )
    assert post_egress_detail.status_code == 200
    assert post_egress_detail.json()["access"]["outcome"] == "unavailable_post_egress_limit"


def test_admin_file_type_filter_uses_stored_artifacts_not_download_policy(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    headers = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)
    set_artifact_policy(client, seeds.ready_id, audio_download="disabled")

    response = client.get("/api/v1/admin/files?type=audio", headers=headers)

    assert response.status_code == 200
    assert str(seeds.ready_id) in response.text


def test_admin_browser_deletion_uses_admin_source_and_audit_journal(client) -> None:
    asyncio.run(_seed_roles(client))
    seeds = seed_cabinet_meetings(client)
    headers = auth_headers_for(user_id=DEFAULT_ADMIN_USER_ID, device_id=DEFAULT_ADMIN_DEVICE_ID)

    response = client.post(
        f"/admin/files/{seeds.ready_id}/deletion-requests",
        headers=headers,
        data={"confirm": "true", "reason_code": "user_request"},
        follow_redirects=False,
    )
    audit = client.get("/api/v1/admin/audit?action=deletion_requested", headers=headers)
    request_source = asyncio.run(_deletion_request_source(client, seeds.ready_id))

    assert response.status_code == 303
    assert request_source == DeletionRequestSource.ADMIN.value
    assert audit.status_code == 200
    assert any(
        entry["source"] == "meeting_lifecycle_audit_events"
        and entry["object_id"] == str(seeds.ready_id)
        for entry in audit.json()["entries"]
    )


async def _seed_roles(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        await seed_default_workspace_admin_roles(db)


async def _set_meeting_states(
    client,
    meeting_id,
    *,
    retention_state: str | None = None,
    deletion_state: str | None = None,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        if retention_state is not None:
            meeting.retention_policy_state = retention_state
        if deletion_state is not None:
            meeting.deletion_state = deletion_state
        await db.commit()


async def _deletion_request_source(client, meeting_id) -> str:
    async with client.app_state["sessionmaker"]() as db:
        request = await db.scalar(
            select(MeetingDeletionRequest).where(MeetingDeletionRequest.meeting_id == meeting_id)
        )
        assert request is not None
        return request.request_source
