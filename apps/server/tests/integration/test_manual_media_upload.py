from hashlib import sha256
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.db.models import TrackArtifact


def test_manual_media_upload_creates_single_media_artifact_and_starts_processing(client) -> None:
    client.app.state.settings.processing_enabled = True
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

    async def load_artifact_roles() -> list[str]:
        async with client.app_state["sessionmaker"]() as db:
            artifacts = await db.scalars(
                select(TrackArtifact)
                .where(TrackArtifact.meeting_id == UUID(body["meeting"]["meeting_id"]))
                .order_by(TrackArtifact.track_role)
            )
            return [artifact.track_role for artifact in artifacts]

    import asyncio

    assert asyncio.run(load_artifact_roles()) == ["manifest", "media"]


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


def test_manual_media_upload_without_client_identity_uses_deterministic_single_track_path(client) -> None:
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
