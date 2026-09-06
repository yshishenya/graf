from io import BytesIO

import httpx
import pytest

from twobrain_rec_server.mediascribe.client import MediaScribeClient, _safe_media_content_type


@pytest.mark.parametrize(
    ("content_type", "expected"),
    [
        ("audio/wav", "audio/wav"),
        ("audio/x-wav", "audio/x-wav"),
        ("audio/wave", "audio/wave"),
        ("audio/mpeg", "audio/mpeg"),
        ("audio/mp3", "audio/mp3"),
        ("audio/mp4", "audio/mp4"),
        ("audio/x-m4a", "audio/mp4"),
        ("audio/m4a", "audio/mp4"),
        ("audio/aac", "audio/aac"),
        ("audio/webm", "audio/webm"),
        ("audio/ogg", "audio/ogg"),
        ("audio/flac", "audio/flac"),
        ("video/mp4", "video/mp4"),
        ("video/quicktime", "video/quicktime"),
        ("video/webm", "video/webm"),
    ],
)
def test_single_track_request_keeps_supported_media_types(content_type: str, expected: str) -> None:
    assert _safe_media_content_type(content_type, b"unknown") == expected


@pytest.mark.asyncio
async def test_dual_track_request_uses_mic_and_incoming_without_mixed_or_silence_flags() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Idempotency-Key"] == "mediascribe-job-1"
        body = await request.aread()
        assert b'name="mic_file"' in body
        assert b'name="incoming_file"' in body
        assert b"name=\"mixed_file\"" not in body
        assert b"playback" not in body.lower()
        assert b"silence" not in body.lower()
        return httpx.Response(200, json={"id": "job_mapping", "status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    response = await client.submit_dual_track(
        mic_file=BytesIO(b"mic-audio"),
        incoming_file=BytesIO(b"incoming-audio"),
        diarize=True,
        summarize=False,
        idempotency_key="mediascribe-job-1",
    )
    assert response.external_job_id == "job_mapping"


@pytest.mark.asyncio
async def test_single_track_request_uses_one_file_without_dual_track_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions"
        body = await request.aread()
        assert b'name="file"' in body
        assert b'filename="manual-media.m4a"' in body
        assert b"Content-Type: audio/mp4" in body
        assert b'name="mic_file"' not in body
        assert b'name="incoming_file"' not in body
        assert b"name=\"mixed_file\"" not in body
        assert b"playback" not in body.lower()
        return httpx.Response(200, json={"id": "job_single", "status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    response = await client.submit_single_track(
        media_file=BytesIO(b"media-audio"),
        media_content_type="audio/mp4",
        diarize=True,
        summarize=True,
    )
    assert response.external_job_id == "job_single"


@pytest.mark.asyncio
async def test_single_track_request_infers_safe_filename_when_upload_codec_is_generic() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert b'filename="manual-media.mp4"' in body
        assert b"Content-Type: video/mp4" in body
        assert b"private-meeting" not in body
        return httpx.Response(200, json={"id": "job_inferred", "status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    response = await client.submit_single_track(
        media_file=BytesIO(b"\x00\x00\x00\x18ftypisommedia"),
        media_content_type="application/octet-stream",
        diarize=True,
        summarize=True,
    )
    assert response.external_job_id == "job_inferred"
