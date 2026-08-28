from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthSession, AuthSessionDeviceBinding, Meeting

OWNER_UPLOAD_TEST_TOKEN = "csrf-owner-manual-upload-session-cookie-token"


@pytest.fixture(autouse=True)
def enable_manual_upload_preparation(client) -> None:
    client.app.state.settings.playback_normalization_enabled = True


def test_cabinet_manual_upload_accepts_session_bound_csrf_and_reuses_single_track_response(client) -> None:
    client.app.state.settings.processing_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    csrf_token = _login_owner_session(client)

    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={
            "title": "Cabinet upload",
            "duration_seconds": "72",
            "local_recording_id": "cabinet-manual-upload-001",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(96), "audio/wav")},
    )

    assert response.status_code == 202
    body = response.json()
    assert body["request_mode"] == "single_track"
    assert body["meeting"]["title"] == "Cabinet upload"
    assert body["meeting"]["media_revision"]["source_kind"] == "manual_upload"
    assert body["upload_session"]["expected_tracks"] == ["manifest", "media"]
    assert body["workflow_started"] is True
    assert "storage_object_key" not in response.text
    assert "external_job_id" not in response.text
    assert body["upload_session"]["mediascribe_job_id"] is None

    listed = client.get("/api/v1/cabinet/meetings?q=Cabinet%20upload", headers=auth_headers())

    assert listed.status_code == 200
    item = listed.json()["items"][0]
    assert item["meeting_id"] == body["meeting"]["meeting_id"]
    assert item["source"] == "manual_upload"
    assert item["status"] == "processing"
    assert item["transcript_available"] is False
    assert item["notes_available"] is False


def test_embedded_desktop_manual_upload_accepts_same_session_cookie_path(client) -> None:
    csrf_token = _login_owner_session(client)

    page = client.get("/desktop/meetings")
    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={
            "title": "Embedded upload",
            "duration_seconds": "61",
            "local_recording_id": "desktop-embedded-manual-upload",
        },
        files={"file": ("meeting.wav", deterministic_wav_bytes(80), "audio/wav")},
    )

    assert page.status_code == 200
    assert 'data-upload-surface="desktop_embedded"' in page.text
    assert "Record live" not in page.text
    assert "Screen Recording" not in page.text
    assert response.status_code == 202
    assert response.json()["meeting"]["title"] == "Embedded upload"


def test_cabinet_manual_upload_uses_file_name_when_title_is_blank(client) -> None:
    csrf_token = _login_owner_session(client)

    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={
            "title": "   ",
            "duration_seconds": "61",
            "local_recording_id": "cabinet-file-title-fallback",
        },
        files={"file": ("/Users/private/Саша Трубишина CRM и т.д..wave", deterministic_wav_bytes(80), "audio/wav")},
    )

    assert response.status_code == 202
    assert response.json()["meeting"]["title"] == "Саша Трубишина CRM и т.д..wave"
    visible_title = "Саша Трубишина CRM и т.д."
    listed = client.get(
        "/api/v1/cabinet/meetings",
        params={"q": visible_title},
        headers=auth_headers(),
    )
    detail = client.get(
        f"/api/v1/cabinet/meetings/{response.json()['meeting']['meeting_id']}",
        headers=auth_headers(),
    )
    page = client.get("/meetings", params={"q": visible_title})

    assert listed.status_code == 200
    assert [item["title"] for item in listed.json()["items"]] == [
        "Саша Трубишина CRM и т.д..wave"
    ]
    assert detail.status_code == 200
    assert detail.json()["meeting"]["title"] == "Саша Трубишина CRM и т.д..wave"
    assert page.status_code == 200
    assert visible_title in page.text
    assert "Загруженная запись" not in page.text


def test_cabinet_manual_upload_requires_csrf_for_cookie_session(client) -> None:
    _login_owner_session(client)

    response = client.post(
        "/api/v1/cabinet/media-uploads",
        data={"duration_seconds": "60", "local_recording_id": "cabinet-missing-csrf"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_missing"


def test_cabinet_manual_upload_rejects_stale_csrf_token(client) -> None:
    _login_owner_session(client)

    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": "stale"},
        data={"duration_seconds": "60", "local_recording_id": "cabinet-stale-csrf"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )

    assert response.status_code == 403
    assert response.json()["code"] == "csrf_token_invalid"


def test_cabinet_manual_upload_rejects_expired_session(client) -> None:
    csrf_token = _login_owner_session(client, expired=True)

    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={"duration_seconds": "60", "local_recording_id": "cabinet-expired-session"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_expired"


def test_cabinet_manual_upload_rejects_legacy_header_only_context(client) -> None:
    response = client.post(
        "/api/v1/cabinet/media-uploads",
        headers=auth_headers(),
        data={"duration_seconds": "60", "local_recording_id": "cabinet-legacy-headers"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )

    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_required_for_manual_upload"


def test_cabinet_manual_upload_rejects_invalid_file_and_duration_inputs_safely(client) -> None:
    csrf_token = _login_owner_session(client)

    missing_file = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={"duration_seconds": "60", "local_recording_id": "cabinet-missing-file"},
    )
    invalid_duration = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={"duration_seconds": "0", "local_recording_id": "cabinet-invalid-duration"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )
    empty_file = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={"duration_seconds": "60", "local_recording_id": "cabinet-empty-file"},
        files={"file": ("empty.wav", b"", "audio/wav")},
    )
    original_limit = client.app.state.settings.max_upload_part_bytes
    client.app.state.settings.max_upload_part_bytes = 4
    oversized = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data={"duration_seconds": "60", "local_recording_id": "cabinet-oversized-file"},
        files={"file": ("meeting.wav", deterministic_wav_bytes(16), "audio/wav")},
    )
    client.app.state.settings.max_upload_part_bytes = original_limit

    assert missing_file.status_code == 422
    assert missing_file.json()["code"] == "request_validation_error"
    assert invalid_duration.status_code == 422
    assert invalid_duration.json()["code"] == "request_validation_error"
    assert empty_file.status_code == 400
    assert empty_file.json()["code"] == "empty_media_upload"
    assert oversized.status_code == 413
    assert oversized.json()["code"] == "upload_part_bytes_exceeded"
    for response in (missing_file, invalid_duration, empty_file, oversized):
        assert "storage_object_key" not in response.text
        assert "external_job_id" not in response.text
        assert "/Users/" not in response.text


def test_cabinet_manual_upload_retry_does_not_create_duplicate_meeting(client) -> None:
    csrf_token = _login_owner_session(client)
    payload = {
        "title": "Duplicate-safe upload",
        "duration_seconds": "60",
        "local_recording_id": "cabinet-duplicate-upload",
    }
    files = {"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")}

    first = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data=payload,
        files=files,
    )
    retry = client.post(
        "/api/v1/cabinet/media-uploads",
        headers={"X-CSRF-Token": csrf_token},
        data=payload,
        files={"file": ("meeting.wav", deterministic_wav_bytes(48), "audio/wav")},
    )

    assert first.status_code == 202
    assert retry.status_code == 202
    assert retry.json()["meeting"]["meeting_id"] == first.json()["meeting"]["meeting_id"]

    async def count_meetings() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(func.count())
                .select_from(Meeting)
                .where(Meeting.local_recording_id == "cabinet-duplicate-upload")
            )

    assert client.portal.call(count_meetings) == 1


def _login_owner_session(client, *, expired: bool = False) -> str:
    session = client.portal.call(_seed_owner_upload_session, client, expired)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_UPLOAD_TEST_TOKEN)
    return csrf_token


async def _seed_owner_upload_session(client, expired: bool) -> AuthSession:
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        session = AuthSession(
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID,
            provider="manual_upload_test",
            session_token_hash=hash_token(OWNER_UPLOAD_TEST_TOKEN),
            status="active",
            issued_at=now - timedelta(minutes=5),
            expires_at=now - timedelta(minutes=1) if expired else now + timedelta(minutes=20),
            claims_fingerprint="feature-090-manual-upload",
        )
        db.add(session)
        await db.flush()
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=session.id,
                registered_device_id=DEVICE_ID,
                device_state="trusted",
            )
        )
        await db.commit()
        return session
