import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.integration.test_playback_normalization_dispatch import (
    CommitObservingTemporalClient,
)
from twobrain_rec_server.db.models import (
    PlaybackNormalizationJob,
    ProcessingWorkflow,
    PurgeJournal,
    RecordingCalendarContextLink,
    TrackArtifact,
    UploadPart,
)
from twobrain_rec_server.normalization.statuses import NormalizationReason


class FailSecondPutStorage:
    def __init__(self, delegate: object) -> None:
        self.delegate = delegate
        self.put_count = 0

    def put_stream(self, object_key, stream, length) -> None:
        self.put_count += 1
        if self.put_count == 2:
            raise RuntimeError("configured second PUT failure")
        self.delegate.put_stream(object_key, stream, length)

    def __getattr__(self, name: str):
        return getattr(self.delegate, name)


def test_manual_media_upload_creates_single_media_artifact_and_starts_processing(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Uploaded meeting",
            "duration_seconds": "60",
            "local_recording_id": "manual-upload-001",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["request_mode"] == "single_track"
    assert body["meeting"]["status"] == "ingested_pending_processing"
    assert body["meeting"]["processing_status"] == "workflow_started"
    assert body["meeting"]["media_revision"]["source_kind"] == "manual_upload"
    assert body["upload_session"]["status"] == "finalized"
    assert body["upload_session"]["expected_tracks"] == ["manifest", "media"]
    assert body["workflow_started"] is True

    async def load_artifact_roles_and_deadline() -> tuple[list[str], datetime | None]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = await db.scalars(
                select(TrackArtifact)
                .where(TrackArtifact.meeting_id == UUID(body["meeting"]["meeting_id"]))
                .order_by(TrackArtifact.track_role)
            )
            workflow = await db.scalar(
                select(ProcessingWorkflow).where(
                    ProcessingWorkflow.meeting_id == UUID(body["meeting"]["meeting_id"])
                )
            )
            assert workflow is not None
            return [artifact.track_role for artifact in artifacts], workflow.deadline_at

    roles, deadline_at = asyncio.run(load_artifact_roles_and_deadline())
    assert roles == ["manifest", "media"]
    assert deadline_at is None


def test_manual_media_upload_commits_custody_before_the_next_storage_write(client) -> None:
    delegate = client.app_state["storage"]
    client.app.state.storage = FailSecondPutStorage(delegate)
    client.app.state.settings.playback_normalization_enabled = True

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={"duration_seconds": "60", "local_recording_id": "manual-second-put-fails"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )

    assert response.status_code == 503
    stored_keys = set(delegate.objects)
    assert len(stored_keys) == 1

    async def custody_keys() -> set[str]:
        async with client.app_state["sessionmaker"]() as db:
            accepted = set(await db.scalars(select(UploadPart.storage_object_key)))
            cleanup = set(
                await db.scalars(
                    select(PurgeJournal.object_key).where(
                        PurgeJournal.state.not_in({"purged", "superseded"})
                    )
                )
            )
            return accepted | cleanup

    assert stored_keys <= asyncio.run(custody_keys())


@pytest.mark.parametrize("processing_enabled", [True, False])
def test_manual_media_upload_fails_before_acceptance_when_preparation_is_disabled(
    client, processing_enabled: bool
) -> None:
    client.app.state.settings.processing_enabled = processing_enabled
    client.app.state.settings.playback_normalization_enabled = False

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Unavailable preparation",
            "duration_seconds": "60",
            "local_recording_id": "manual-preparation-disabled",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )

    assert response.status_code == 503
    assert response.json()["code"] == "manual_media_preparation_unavailable"


def test_manual_normalization_retry_projects_countdown_and_manual_due_now(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Retryable preparation",
            "duration_seconds": "60",
            "local_recording_id": "manual-preparation-retry",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])
    retry_at = datetime.now(UTC) + timedelta(minutes=5)

    async def schedule_retry() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            job.state = "retry_wait"
            job.reason_code = NormalizationReason.STORAGE_UNAVAILABLE.value
            job.next_attempt_at = retry_at
            job.lease_owner_sha256 = None
            job.lease_expires_at = None
            await db.commit()

    asyncio.run(schedule_retry())
    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    assert status.json()["manual_action"] == "retry_preparation"
    assert status.json()["next_attempt_at"] is not None

    stale = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/check",
        headers=auth_headers(),
        json={"schedule_generation": status.json()["schedule_generation"] + 999},
    )
    assert stale.status_code == 200
    assert stale.json()["request_result"] == "stale_schedule"
    assert stale.json()["manual_action"] == "retry_preparation"
    assert stale.json()["next_attempt_at"] is not None

    retried = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/check",
        headers=auth_headers(),
        json={"schedule_generation": status.json()["schedule_generation"]},
    )
    assert retried.status_code == 200
    assert retried.json()["request_result"] == "accepted"
    assert retried.json()["manual_action"] == "none"
    assert retried.json()["next_attempt_at"] is None

    repeated = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/check",
        headers=auth_headers(),
        json={"command_id": retried.json()["command_id"]},
    )
    assert repeated.status_code == 200
    assert repeated.json()["request_result"] == "already_in_flight"


def test_terminal_manual_normalization_does_not_offer_impossible_processing_attempt(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Terminal preparation",
            "duration_seconds": "60",
            "local_recording_id": "manual-preparation-terminal",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])

    async def fail_preparation() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            job.state = "terminal"
            job.reason_code = NormalizationReason.CORRUPT_SOURCE.value
            job.terminal_at = datetime.now(UTC)
            job.lease_owner_sha256 = None
            job.lease_expires_at = None
            await db.commit()

    asyncio.run(fail_preparation())
    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    assert status.json()["state"] == "failed_terminal"
    assert status.json()["manual_action"] == "upload_another"

    attempt = client.post(
        f"/api/v1/meetings/{meeting_id}/processing/attempt",
        headers=auth_headers(),
    )
    assert attempt.status_code == 409
    assert attempt.json()["code"] == "processing_source_unavailable"


def test_storage_full_manual_normalization_offers_no_archive_upload(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Storage-full preparation",
            "duration_seconds": "60",
            "local_recording_id": "manual-preparation-storage-full",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(128), "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])

    async def fail_preparation() -> None:
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            job.state = "terminal"
            job.reason_code = NormalizationReason.STORAGE_CAPACITY_EXCEEDED.value
            job.terminal_at = datetime.now(UTC)
            job.lease_owner_sha256 = None
            job.lease_expires_at = None
            await db.commit()

    asyncio.run(fail_preparation())
    status = client.get(f"/api/v1/meetings/{meeting_id}/processing", headers=auth_headers())
    assert status.status_code == 200
    assert status.json()["state"] == "failed_terminal"
    assert status.json()["reason_code"] == "storage_capacity_exceeded"
    assert status.json()["manual_action"] == "upload_another"


def test_manual_media_upload_commits_and_starts_normalization_without_processing(client) -> None:
    temporal = CommitObservingTemporalClient(client.app_state["sessionmaker"])
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.settings.processing_enabled = False
    client.app.state.temporal_client = temporal

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Manual normalization",
            "duration_seconds": "60",
            "local_recording_id": "manual-normalization-post-commit",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(256), "audio/wav")},
    )

    assert response.status_code == 202
    body = response.json()
    revision_id = body["meeting"]["media_revision"]["media_revision_id"]
    workflow_id = f"playback-normalization/{revision_id}/v1"
    assert temporal.job_was_committed_before_start is True
    assert workflow_id in temporal.starts
    assert all(not started_id.startswith("processing/") for started_id in temporal.starts)
    assert body["workflow_started"] is False

    async def load_job() -> PlaybackNormalizationJob | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == UUID(body["meeting"]["meeting_id"])
                )
            )

    job = client.portal.call(load_job)
    assert job is not None
    assert job.source_kind == "manual_upload"
    assert job.planned_action == "normalize_source"
    assert job.state == "queued"
    assert job.workflow_id == workflow_id


def test_manual_media_upload_rejects_empty_file(client) -> None:
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={"duration_seconds": "60", "local_recording_id": "manual-upload-empty"},
        files={"file": ("empty.wav", b"", "audio/wav")},
    )

    assert response.status_code == 400
    assert response.json()["code"] == "empty_media_upload"


def test_manual_media_upload_rejects_control_character_recording_identity(client) -> None:
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={"duration_seconds": "60", "local_recording_id": "manual\nupload"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(64), "audio/wav")},
    )

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"
    assert "manual\\nupload" not in response.text


def test_manual_media_upload_without_client_identity_uses_deterministic_single_track_path(
    client,
) -> None:
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    data = deterministic_wav_bytes(80)
    media_sha = sha256(data).hexdigest()

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={"duration_seconds": "45", "title": "Generated identity"},
        files={"file": ("meeting.wav", data, "audio/wav")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["request_mode"] == "single_track"
    assert body["meeting"]["local_recording_id"] == f"manual-upload-{media_sha[:32]}"
    assert body["meeting"]["local_media_revision_id"] == f"manual-upload-{media_sha[:32]}--manual"
    assert body["upload_session"]["expected_tracks"] == ["manifest", "media"]


@pytest.mark.parametrize(
    ("provided_title", "filename", "expected_title", "expected_title_source"),
    [
        (
            "Synthetic Uploaded Planning",
            "synthetic-upload.wav",
            "Synthetic Uploaded Planning",
            "upload_provided",
        ),
        (
            None,
            "synthetic-recovery-recording.wav",
            "synthetic-recovery-recording.wav",
            "file_name_derived",
        ),
    ],
)
def test_us2_manual_upload_persists_skip_without_replacing_upload_title(
    client,
    provided_title: str | None,
    filename: str,
    expected_title: str,
    expected_title_source: str,
) -> None:
    # FR-011/FR-029/FR-035/FR-036, SC-004: uploads are durably out of auto-match scope.
    client.app.state.settings.processing_enabled = True
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    local_recording_id = f"manual-upload-us2-{expected_title_source}-098"
    data = {
        "duration_seconds": "60",
        "local_recording_id": local_recording_id,
    }
    if provided_title is not None:
        data["title"] = provided_title

    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data=data,
        files={"file": (filename, deterministic_wav_bytes(192), "audio/wav")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["meeting"]["title"] == expected_title
    assert body["meeting"]["title_source"] == expected_title_source
    assert body["meeting"]["media_revision"]["source_kind"] == "manual_upload"
    assert body["meeting"]["calendar_context"] == {
        "state": "skipped_manual_upload",
        "label": "Без контекста календаря",
        "title_source": expected_title_source,
        "needs_owner_action": False,
    }
    assert body["upload_session"]["status"] == "finalized"
    assert body["workflow_started"] is True

    async def load_context() -> RecordingCalendarContextLink | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == UUID(body["meeting"]["meeting_id"])
                )
            )

    context = client.portal.call(load_context)
    assert context is not None
    assert context.context_state == "skipped_manual_upload"
    assert context.safe_reason_code == "manual_upload_skipped"
    assert context.decision_source == "system_skip"
    assert context.calendar_event_snapshot_id is None
    assert context.match_attempt_id is None
    assert context.candidate_count == 0
    assert context.matched_title is None
    assert context.matched_roster_json == []
