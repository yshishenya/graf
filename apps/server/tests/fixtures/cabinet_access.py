from __future__ import annotations

import asyncio
import io
import wave
from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    MediaRevision,
    Meeting,
    MeetingArtifactPolicy,
    MeetingEgressAuditEvent,
    MeetingShareGrant,
    PlaybackNormalizationJob,
    RegisteredDevice,
    TrackArtifact,
    UserIdentity,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import TrackRole
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
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


def grant_meeting_to_user(
    client: TestClient,
    meeting_id: UUID,
    *,
    user_id: UUID = SHARED_USER_ID,
) -> None:
    asyncio.run(_grant_meeting_to_user(client, meeting_id, user_id=user_id))


async def _grant_meeting_to_user(
    client: TestClient,
    meeting_id: UUID,
    *,
    user_id: UUID,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        db.add(
            MeetingShareGrant(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                grant_type="user",
                grantee_user_id=user_id,
                created_by_user_id=meeting.created_by_user_id,
                status="active",
                metadata_json={},
            )
        )
        await db.commit()


async def _add_workspace_user(
    client: TestClient,
    *,
    user_id: UUID,
    device_id: UUID,
    role: str,
    display_name: str,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            UserIdentity(
                id=user_id,
                organization_id=ORG_ID,
                external_subject=str(user_id),
                display_name=display_name,
                status="active",
            )
        )
        await db.flush()
        db.add_all(
            [
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


def set_meeting_deletion_state(client: TestClient, meeting_id: UUID, deletion_state: str) -> None:
    asyncio.run(_set_meeting_deletion_state(client, meeting_id, deletion_state))


async def _set_meeting_deletion_state(
    client: TestClient, meeting_id: UUID, deletion_state: str
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        meeting.deletion_state = deletion_state
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


def set_retained_audio_source_status(
    client: TestClient, meeting_id: UUID, role: TrackRole, status: str
) -> None:
    asyncio.run(_set_retained_audio_source_status(client, meeting_id, role, status))


async def _set_retained_audio_source_status(
    client: TestClient,
    meeting_id: UUID,
    role: TrackRole,
    status: str,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        artifact = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.track_role == role.value,
            )
        )
        assert artifact is not None
        artifact.status = status
        await db.commit()


def audit_events(client: TestClient, meeting_id: UUID) -> list[MeetingEgressAuditEvent]:
    return asyncio.run(_audit_events(client, meeting_id))


async def _audit_events(client: TestClient, meeting_id: UUID) -> list[MeetingEgressAuditEvent]:
    async with client.app_state["sessionmaker"]() as db:
        return (
            await db.scalars(
                select(MeetingEgressAuditEvent)
                .where(
                    MeetingEgressAuditEvent.workspace_id == WORKSPACE_ID,
                    MeetingEgressAuditEvent.meeting_id == meeting_id,
                )
                .order_by(MeetingEgressAuditEvent.created_at.asc())
            )
        ).all()


def replace_retained_audio_with_test_wav(client: TestClient, meeting_id: UUID) -> None:
    asyncio.run(_replace_retained_audio_with_test_wav(client, meeting_id))


def add_retained_playback_m4a(
    client: TestClient, meeting_id: UUID, body: bytes = b"fixture-m4a-review"
) -> bytes:
    asyncio.run(_add_retained_playback_m4a(client, meeting_id, body))
    return body


async def _add_retained_playback_m4a(client: TestClient, meeting_id: UUID, body: bytes) -> None:
    storage = client.app_state["storage"]
    object_key = f"tests/cabinet/{meeting_id}/meeting-review.m4a"
    storage.put_bytes(object_key, body)
    async with client.app_state["sessionmaker"]() as db:
        media_revision = await db.scalar(
            select(MediaRevision).where(
                MediaRevision.workspace_id == WORKSPACE_ID,
                MediaRevision.meeting_id == meeting_id,
            )
        )
        assert media_revision is not None
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                PlaybackNormalizationJob.meeting_id == meeting_id,
                PlaybackNormalizationJob.media_revision_id == media_revision.id,
                PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
            )
        )
        assert job is not None
        artifact = await db.scalar(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.meeting_id == meeting_id,
                TrackArtifact.media_revision_id == media_revision.id,
                TrackArtifact.track_role == TrackRole.PLAYBACK.value,
            )
        )
        if artifact is None:
            artifact = TrackArtifact(
                meeting_id=meeting_id,
                media_revision_id=media_revision.id,
                workspace_id=WORKSPACE_ID,
                track_role=TrackRole.PLAYBACK.value,
                codec="m4a-aac-lc",
                sample_rate_hz=48_000,
                channel_count=1,
                duration_seconds=1,
                byte_length=len(body),
                sha256=sha256(body).hexdigest(),
                storage_object_key=object_key,
                status="stored",
                normalization_profile_version=CANONICAL_PROFILE_VERSION,
                validated_at=datetime.now(UTC),
                derivation_kind="uploaded_candidate",
                source_fingerprint_sha256=job.source_fingerprint_sha256,
                validation_version=VALIDATION_VERSION,
            )
            db.add(artifact)
        else:
            artifact.media_revision_id = media_revision.id
            artifact.codec = "m4a-aac-lc"
            artifact.sample_rate_hz = 48_000
            artifact.channel_count = 1
            artifact.duration_seconds = 1
            artifact.byte_length = len(body)
            artifact.sha256 = sha256(body).hexdigest()
            artifact.storage_object_key = object_key
            artifact.status = "stored"
            artifact.normalization_profile_version = CANONICAL_PROFILE_VERSION
            artifact.validated_at = datetime.now(UTC)
            artifact.derivation_kind = "uploaded_candidate"
            artifact.source_fingerprint_sha256 = job.source_fingerprint_sha256
            artifact.validation_version = VALIDATION_VERSION
        await db.flush()
        job.state = "ready"
        job.reason_code = None
        job.canonical_track_artifact_id = artifact.id
        job.ready_at = datetime.now(UTC)
        await db.commit()


async def _replace_retained_audio_with_test_wav(client: TestClient, meeting_id: UUID) -> None:
    mic_bytes = _wav_bytes([1000, 1000, 0, 0])
    incoming_bytes = _wav_bytes([0, 0, 2000, 2000])
    by_role = {
        TrackRole.MICROPHONE.value: mic_bytes,
        TrackRole.SYSTEM.value: incoming_bytes,
    }
    storage = client.app_state["storage"]
    async with client.app_state["sessionmaker"]() as db:
        artifacts = (
            await db.scalars(
                select(TrackArtifact)
                .where(
                    TrackArtifact.workspace_id == WORKSPACE_ID,
                    TrackArtifact.meeting_id == meeting_id,
                )
                .order_by(TrackArtifact.track_role.asc())
            )
        ).all()
        for artifact in artifacts:
            data = by_role.get(artifact.track_role)
            if data is None:
                continue
            storage.put_bytes(artifact.storage_object_key, data)
            artifact.codec = "pcm_s16le"
            artifact.sample_rate_hz = 16_000
            artifact.channel_count = 1
            artifact.duration_seconds = 1
            artifact.byte_length = len(data)
            artifact.sha256 = sha256(data).hexdigest()
        await db.commit()


def _wav_bytes(samples: list[int], *, sample_rate: int = 16_000) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(sample.to_bytes(2, "little", signed=True) for sample in samples))
    return buffer.getvalue()
