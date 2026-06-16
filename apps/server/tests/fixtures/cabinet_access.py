from __future__ import annotations

import asyncio
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    Meeting,
    MeetingArtifactPolicy,
    MeetingEgressAuditEvent,
    RegisteredDevice,
    UserIdentity,
    WorkspaceMembership,
)

SHARED_USER_ID = UUID("30000000-0000-0000-0000-000000000017")
SHARED_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000017")


def auth_headers_for(
    *,
    user_id: UUID = SHARED_USER_ID,
    device_id: UUID = SHARED_DEVICE_ID,
    workspace_id: UUID = WORKSPACE_ID,
    organization_id: UUID = ORG_ID,
) -> dict[str, str]:
    return {
        "X-Organization-Id": str(organization_id),
        "X-Workspace-Id": str(workspace_id),
        "X-User-Id": str(user_id),
        "X-Device-Id": str(device_id),
    }


def add_workspace_user(
    client: TestClient,
    *,
    user_id: UUID = SHARED_USER_ID,
    device_id: UUID = SHARED_DEVICE_ID,
    role: str = "member",
    display_name: str = "Shared User",
) -> None:
    asyncio.run(
        _add_workspace_user(
            client,
            user_id=user_id,
            device_id=device_id,
            role=role,
            display_name=display_name,
        )
    )


async def _add_workspace_user(
    client: TestClient,
    *,
    user_id: UUID,
    device_id: UUID,
    role: str,
    display_name: str,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add_all(
            [
                UserIdentity(
                    id=user_id,
                    organization_id=ORG_ID,
                    external_subject=str(user_id),
                    display_name=display_name,
                    status="active",
                ),
                WorkspaceMembership(
                    workspace_id=WORKSPACE_ID,
                    user_id=user_id,
                    role=role,
                    status="active",
                ),
                RegisteredDevice(
                    id=device_id,
                    workspace_id=WORKSPACE_ID,
                    user_id=user_id,
                    device_public_id=f"device-{device_id}",
                    status="active",
                ),
            ]
        )
        await db.commit()


def set_meeting_visibility(client: TestClient, meeting_id: UUID, visibility: str) -> None:
    asyncio.run(_set_meeting_visibility(client, meeting_id, visibility))


async def _set_meeting_visibility(client: TestClient, meeting_id: UUID, visibility: str) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        meeting.visibility = visibility
        await db.commit()


def set_artifact_policy(
    client: TestClient,
    meeting_id: UUID,
    *,
    audio_download: str = "disabled",
    transcript_download: str = "disabled",
    summary_download: str = "disabled",
    package_export: str = "disabled",
) -> None:
    asyncio.run(
        _set_artifact_policy(
            client,
            meeting_id,
            audio_download=audio_download,
            transcript_download=transcript_download,
            summary_download=summary_download,
            package_export=package_export,
        )
    )


async def _set_artifact_policy(
    client: TestClient,
    meeting_id: UUID,
    *,
    audio_download: str,
    transcript_download: str,
    summary_download: str,
    package_export: str,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = MeetingArtifactPolicy(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            audio_download=audio_download,
            transcript_download=transcript_download,
            summary_download=summary_download,
            package_export=package_export,
            policy_source="test_fixture",
        )
        db.add(policy)
        await db.commit()


def audit_events(client: TestClient, meeting_id: UUID) -> list[MeetingEgressAuditEvent]:
    return asyncio.run(_audit_events(client, meeting_id))


async def _audit_events(client: TestClient, meeting_id: UUID) -> list[MeetingEgressAuditEvent]:
    async with client.app_state["sessionmaker"]() as db:
        return (
            await db.scalars(
                select(MeetingEgressAuditEvent)
                .where(MeetingEgressAuditEvent.workspace_id == WORKSPACE_ID, MeetingEgressAuditEvent.meeting_id == meeting_id)
                .order_by(MeetingEgressAuditEvent.created_at.asc())
            )
        ).all()
