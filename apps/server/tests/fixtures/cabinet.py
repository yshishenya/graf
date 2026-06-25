from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.db.models import (
    DiarizationSegment,
    MediaRevision,
    MediaScribeJob,
    Meeting,
    Organization,
    ProcessingDependencyState,
    ProcessingResult,
    ProcessingWorkflow,
    RegisteredDevice,
    TrackArtifact,
    TranscriptSegment,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    MeetingStatus,
    ProcessingAvailabilityStatus,
    ProcessingDependencyName,
    ProcessingDependencyStateValue,
    ProcessingResultStatus,
    ProcessingStatus,
    SummaryStatus,
    TrackRole,
)

FOREIGN_ORG_ID = UUID("10000000-0000-0000-0000-000000000016")
FOREIGN_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000016")
FOREIGN_USER_ID = UUID("30000000-0000-0000-0000-000000000016")
FOREIGN_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000016")

SAFE_TRANSCRIPT_TEXT = "Обсудили запуск кабинета встреч."
SAFE_SECOND_TRANSCRIPT_TEXT = "Проверили статус обработки и следующие шаги."
PRIVATE_EXTERNAL_JOB_ID = "fixture-mediascribe-private-job-id"


@dataclass(slots=True)
class CabinetSeed:
    ready_id: UUID
    processing_id: UUID
    failed_id: UUID
    partial_id: UUID
    foreign_id: UUID


def seed_cabinet_meetings(client: TestClient) -> CabinetSeed:
    ready_id = _create_ready_meeting(client, "cabinet-ready", "Проектный синк")
    processing_id = _create_processing_meeting(client, "cabinet-processing", "Планирование релиза")
    failed_id = _create_failed_meeting(client, "cabinet-failed", "Сбой обработки")
    partial_id = _create_partial_meeting(client, "cabinet-partial", "Частичный импорт")
    foreign_id = _create_foreign_meeting(client)
    return CabinetSeed(
        ready_id=ready_id,
        processing_id=processing_id,
        failed_id=failed_id,
        partial_id=partial_id,
        foreign_id=foreign_id,
    )


def _create_ready_meeting(client: TestClient, local_recording_id: str, title: str) -> UUID:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    asyncio.run(
        _seed_processed_rows(
            client,
            meeting_id=meeting_id,
            title=title,
            transcript_available=True,
            diarization_available=True,
            processing_status=ProcessingStatus.PROCESSED,
        )
    )
    return meeting_id


def create_summary_reported_meeting(client: TestClient) -> UUID:
    finalized = create_finalized_meeting(client, "cabinet-summary-reported")
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    asyncio.run(
        _seed_processed_rows(
            client,
            meeting_id=meeting_id,
            title="Summary reported without stored output",
            transcript_available=True,
            diarization_available=True,
            processing_status=ProcessingStatus.PROCESSED,
            summary_status=SummaryStatus.AVAILABLE,
        )
    )
    return meeting_id


def create_outcome_ready_meeting(
    client: TestClient,
    local_recording_id: str = "cabinet-outcome-ready",
) -> UUID:
    return _create_ready_meeting(client, local_recording_id, "Итоги встречи")


def _create_partial_meeting(client: TestClient, local_recording_id: str, title: str) -> UUID:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    asyncio.run(
        _seed_processed_rows(
            client,
            meeting_id=meeting_id,
            title=title,
            transcript_available=True,
            diarization_available=False,
            processing_status=ProcessingStatus.PROCESSED,
        )
    )
    return meeting_id


def _create_processing_meeting(client: TestClient, local_recording_id: str, title: str) -> UUID:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    asyncio.run(
        _seed_workflow_only(
            client,
            meeting_id=meeting_id,
            title=title,
            status=ProcessingStatus.POLLING,
            reason_code=None,
        )
    )
    return meeting_id


def _create_failed_meeting(client: TestClient, local_recording_id: str, title: str) -> UUID:
    finalized = create_finalized_meeting(client, local_recording_id)
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    asyncio.run(
        _seed_workflow_only(
            client,
            meeting_id=meeting_id,
            title=title,
            status=ProcessingStatus.FAILED_TERMINAL,
            reason_code="mediascribe_validation_failed",
        )
    )
    return meeting_id


async def _seed_workflow_only(
    client: TestClient,
    *,
    meeting_id: UUID,
    title: str,
    status: ProcessingStatus,
    reason_code: str | None,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        meeting.title = title
        meeting.started_at = datetime(2026, 6, 16, 9, 30, tzinfo=UTC)
        meeting.ended_at = datetime(2026, 6, 16, 10, 0, tzinfo=UTC)
        meeting.duration_seconds = 1800
        meeting.status = MeetingStatus.INGESTED_PENDING_PROCESSING.value
        meeting.processing_status = status.value
        media_revision = await db.scalar(
            select(MediaRevision).where(
                MediaRevision.workspace_id == WORKSPACE_ID,
                MediaRevision.meeting_id == meeting_id,
            )
        )
        assert media_revision is not None
        workflow = ProcessingWorkflow(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            media_revision_id=media_revision.id,
            workflow_id=f"processing/{media_revision.id}",
            status=status.value,
            attempt_count=2,
            last_reason_code=reason_code,
            started_at=datetime.now(UTC) - timedelta(minutes=12),
            ended_at=datetime.now(UTC) if status == ProcessingStatus.FAILED_TERMINAL else None,
        )
        db.add(workflow)
        await db.commit()


async def _seed_processed_rows(
    client: TestClient,
    *,
    meeting_id: UUID,
    title: str,
    transcript_available: bool,
    diarization_available: bool,
    processing_status: ProcessingStatus,
    summary_status: SummaryStatus = SummaryStatus.NOT_REQUESTED,
) -> None:
    async with client.app_state["sessionmaker"]() as db:
        meeting = await db.get(Meeting, meeting_id)
        assert meeting is not None
        meeting.title = title
        meeting.started_at = datetime(2026, 6, 16, 8, 0, tzinfo=UTC)
        meeting.ended_at = datetime(2026, 6, 16, 8, 31, tzinfo=UTC)
        meeting.duration_seconds = 1860
        meeting.status = MeetingStatus.INGESTED_PENDING_PROCESSING.value
        meeting.processing_status = processing_status.value

        artifacts = (
            await db.scalars(
                select(TrackArtifact)
                .where(TrackArtifact.workspace_id == WORKSPACE_ID, TrackArtifact.meeting_id == meeting_id)
                .order_by(TrackArtifact.track_role)
            )
        ).all()
        mic = next(artifact for artifact in artifacts if artifact.track_role == TrackRole.MICROPHONE.value)
        system = next(artifact for artifact in artifacts if artifact.track_role == TrackRole.SYSTEM.value)
        media_revision = await db.scalar(
            select(MediaRevision).where(
                MediaRevision.workspace_id == WORKSPACE_ID,
                MediaRevision.meeting_id == meeting_id,
            )
        )
        assert media_revision is not None
        workflow = ProcessingWorkflow(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            media_revision_id=media_revision.id,
            workflow_id=f"processing/{media_revision.id}",
            workflow_run_id="private-run-id",
            status=processing_status.value,
            attempt_count=1,
            started_at=datetime.now(UTC) - timedelta(minutes=8),
            ended_at=datetime.now(UTC),
        )
        db.add(workflow)
        await db.flush()
        external_job_id = f"{PRIVATE_EXTERNAL_JOB_ID}-{meeting_id}"
        job = MediaScribeJob(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            media_revision_id=media_revision.id,
            processing_workflow_id=workflow.id,
            external_job_id=external_job_id,
            status=MediaScribeJobStatus.READY.value,
            mic_track_artifact_id=mic.id,
            incoming_track_artifact_id=system.id,
            submitted_at=datetime.now(UTC) - timedelta(minutes=7),
            ready_at=datetime.now(UTC) - timedelta(minutes=3),
        )
        db.add(job)
        await db.flush()
        result = ProcessingResult(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            media_revision_id=media_revision.id,
            mediascribe_job_id=job.id,
            result_version=1,
            status=ProcessingResultStatus.IMPORTED.value,
            transcript_status=(
                ProcessingAvailabilityStatus.AVAILABLE.value
                if transcript_available
                else ProcessingAvailabilityStatus.UNAVAILABLE.value
            ),
            diarization_status=(
                ProcessingAvailabilityStatus.AVAILABLE.value
                if diarization_available
                else ProcessingAvailabilityStatus.UNAVAILABLE.value
            ),
            summary_status=summary_status.value,
            language="ru",
            segment_count=2 if transcript_available else 0,
            diarization_segment_count=2 if diarization_available else 0,
            source_result_hash="fixture-result-hash",
            imported_at=datetime.now(UTC) - timedelta(minutes=2),
        )
        db.add(result)
        await db.flush()
        if transcript_available:
            db.add_all(
                [
                    TranscriptSegment(
                        processing_result_id=result.id,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        sequence=0,
                        start_seconds=Decimal("0.000"),
                        end_seconds=Decimal("12.500"),
                        text=SAFE_TRANSCRIPT_TEXT,
                        source_role="mic",
                        source_role_original="microphone",
                    ),
                    TranscriptSegment(
                        processing_result_id=result.id,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        sequence=1,
                        start_seconds=Decimal("12.500"),
                        end_seconds=Decimal("28.000"),
                        text=SAFE_SECOND_TRANSCRIPT_TEXT,
                        source_role="incoming",
                        source_role_original="system",
                    ),
                ]
            )
        if diarization_available:
            db.add_all(
                [
                    DiarizationSegment(
                        processing_result_id=result.id,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        sequence=0,
                        start_seconds=Decimal("0.000"),
                        end_seconds=Decimal("12.500"),
                        speaker_label="Speaker 1",
                        text=SAFE_TRANSCRIPT_TEXT,
                        source_role="mic",
                    ),
                    DiarizationSegment(
                        processing_result_id=result.id,
                        workspace_id=WORKSPACE_ID,
                        meeting_id=meeting_id,
                        sequence=1,
                        start_seconds=Decimal("12.500"),
                        end_seconds=Decimal("28.000"),
                        speaker_label="Speaker 2",
                        text=SAFE_SECOND_TRANSCRIPT_TEXT,
                        source_role="incoming",
                    ),
                ]
            )
        db.add(
            ProcessingDependencyState(
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                media_revision_id=media_revision.id,
                dependency=ProcessingDependencyName.MEDIASCRIBE.value,
                state=ProcessingDependencyStateValue.IMPORTED.value,
                external_reference=external_job_id,
                notes="fixture only",
            )
        )
        await db.commit()


def _create_foreign_meeting(client: TestClient) -> UUID:
    meeting_id = UUID("50000000-0000-0000-0000-000000000016")
    asyncio.run(_seed_foreign_workspace(client, meeting_id))
    return meeting_id


async def _seed_foreign_workspace(client: TestClient, meeting_id: UUID) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add_all(
            [
                Organization(id=FOREIGN_ORG_ID, slug="foreign-org", name="Foreign Org"),
                Workspace(
                    id=FOREIGN_WORKSPACE_ID,
                    organization_id=FOREIGN_ORG_ID,
                    slug="foreign-workspace",
                    name="Foreign Workspace",
                ),
                UserIdentity(
                    id=FOREIGN_USER_ID,
                    organization_id=FOREIGN_ORG_ID,
                    external_subject=str(FOREIGN_USER_ID),
                    display_name="Foreign User",
                ),
                WorkspaceMembership(
                    workspace_id=FOREIGN_WORKSPACE_ID,
                    user_id=FOREIGN_USER_ID,
                    role="owner",
                    status="active",
                ),
                RegisteredDevice(
                    id=FOREIGN_DEVICE_ID,
                    workspace_id=FOREIGN_WORKSPACE_ID,
                    user_id=FOREIGN_USER_ID,
                    device_public_id="foreign-device",
                    status="active",
                ),
                Meeting(
                    id=meeting_id,
                    workspace_id=FOREIGN_WORKSPACE_ID,
                    created_by_user_id=FOREIGN_USER_ID,
                    device_id=FOREIGN_DEVICE_ID,
                    local_recording_id="foreign-private-recording",
                    title="Foreign private meeting",
                    started_at=datetime(2026, 6, 16, 7, 0, tzinfo=UTC),
                    duration_seconds=120,
                    status=MeetingStatus.INGESTED_PENDING_PROCESSING.value,
                    processing_status=ProcessingStatus.PROCESSED.value,
                ),
            ]
        )
        await db.commit()
