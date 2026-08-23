from io import BytesIO

import httpx
import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingAvailabilityStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError


def test_mediascribe_client_maps_unreadable_secret_file_to_safe_blocked_config(tmp_path) -> None:
    settings = Settings(
        mediascribe_base_url="https://mediascribe.test",
        mediascribe_api_key_file=tmp_path / "missing.key",
    )

    with pytest.raises(MediaScribeClientError) as exc:
        MediaScribeClient.from_settings(settings)

    assert exc.value.reason_code == "blocked_config"
    assert not exc.value.retryable
    assert "missing.key" not in str(exc.value)


@pytest.mark.asyncio
async def test_mediascribe_client_submits_only_dual_track_fields_and_server_key() -> None:
    captured: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        captured["path"] = request.url.path
        captured["api_key"] = request.headers.get("x-api-key")
        captured["idempotency_key"] = request.headers.get("idempotency-key")
        body = await request.aread()
        assert b'name="mic_file"' in body
        assert b'name="incoming_file"' in body
        assert b'name="mixed_file"' not in body
        return httpx.Response(200, json={"id": "job_contract", "status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    response = await client.submit_dual_track(
        mic_file=BytesIO(b"mic"),
        incoming_file=BytesIO(b"incoming"),
        diarize=True,
        summarize=False,
        idempotency_key="job-contract-key",
    )
    assert captured == {
        "path": "/v1/audio/transcriptions/dual-track",
        "api_key": "server-side-key",
        "idempotency_key": "job-contract-key",
    }
    assert response.external_job_id == "job_contract"
    assert response.status == MediaScribeJobStatus.UPLOADED


@pytest.mark.asyncio
async def test_v5_canonical_wav_uses_one_audio_wav_part_and_never_includes_playback() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions"
        body = await request.aread()
        assert b'name="file"' in body
        assert b'filename="meeting-transcription.wav"' in body
        assert b"Content-Type: audio/wav" in body
        assert b'name="mic_file"' not in body
        assert b'name="incoming_file"' not in body
        assert b"dual-track" not in request.url.path.encode()
        assert b"playback" not in body.lower()
        assert b"m4a" not in body.lower()
        return httpx.Response(200, json={"id": "job_v5_wav", "status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    response = await client.submit_single_track(
        media_file=BytesIO(b"RIFF\x00\x00\x00\x00WAVE"),
        media_content_type="audio/wav",
        media_filename="meeting-transcription.wav",
        diarize=True,
        summarize=False,
    )

    assert response.external_job_id == "job_v5_wav"


@pytest.mark.asyncio
async def test_mediascribe_client_maps_auth_failure_without_response_secret() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "bad key"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(MediaScribeClientError) as exc:
        await client.poll_job("job_401")
    assert exc.value.reason_code == "mediascribe_auth_failed"
    assert not exc.value.retryable
    assert "server-side-key" not in str(exc.value)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "reason_code"),
    [(429, "mediascribe_rate_limited"), (500, "mediascribe_server_error")],
)
async def test_mediascribe_client_marks_retryable_http_responses_as_received(
    status_code: int, reason_code: str
) -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"detail": "temporary"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(MediaScribeClientError) as exc:
        await client.poll_job("job_retryable")

    assert exc.value.reason_code == reason_code
    assert exc.value.retryable
    assert exc.value.egress_state == "response_received"


@pytest.mark.asyncio
async def test_mediascribe_client_rejects_empty_poll_payload_as_terminal_malformed() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(MediaScribeClientError) as exc:
        await client.poll_job("job_empty")

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.egress_state == "not_sent"


@pytest.mark.asyncio
async def test_mediascribe_client_rejects_empty_result_payload_as_terminal_malformed() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_empty")

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.egress_state == "not_sent"


@pytest.mark.asyncio
async def test_mediascribe_client_maps_malformed_success_payloads_to_safe_retryable_error() -> None:
    async def submit_missing_job_id(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "uploaded"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(submit_missing_job_id),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.submit_dual_track(
            mic_file=BytesIO(b"mic"),
            incoming_file=BytesIO(b"incoming"),
            diarize=True,
            summarize=False,
        )

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.retryable
    assert exc.value.egress_state == "unknown"
    assert "server-side-key" not in str(exc.value)


@pytest.mark.asyncio
async def test_mediascribe_client_maps_invalid_result_payload_to_safe_retryable_error() -> None:
    async def result_with_invalid_timing(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_bad_result"},
                "transcript": [
                    {"start": -1, "end": 2, "text": "bad timing", "source_role": "mic"},
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(result_with_invalid_timing),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_bad_result")

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.retryable
    assert "bad timing" not in str(exc.value)


@pytest.mark.asyncio
async def test_mediascribe_client_polls_and_maps_live_result_contract_shape() -> None:
    captured_paths: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured_paths.append(request.url.path)
        if request.url.path == "/jobs/job_live":
            return httpx.Response(200, json={"id": "job_live", "status": "ready", "result_available": True})
        if request.url.path == "/jobs/job_live/result":
            return httpx.Response(
                200,
                json={
                    "job": {"id": "job_live"},
                    "transcript": [
                        {"start": 0.1, "end": 1.2, "text": "local", "source_role": "mic"},
                        {"start": 1.3, "end": 2.4, "text": "remote", "source_role": "incoming"},
                    ],
                    "diarization": [
                        {"start": 0.1, "end": 1.2, "speaker": "MIC", "text": "local", "source_role": "mic"},
                        {"start": 1.3, "end": 2.4, "speaker": "REMOTE_00", "text": "remote", "source_role": "incoming"},
                    ],
                    "summary": None,
                },
            )
        return httpx.Response(404, json={"detail": "missing"})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    poll = await client.poll_job("job_live")
    result = await client.fetch_result("job_live")

    assert poll.status == MediaScribeJobStatus.READY
    assert captured_paths == ["/jobs/job_live", "/jobs/job_live/result"]
    assert result.external_job_id == "job_live"
    assert len(result.transcript) == 2
    assert result.transcript[0].start_seconds == 0.1
    assert result.transcript[1].source_role == "incoming"
    assert len(result.diarization) == 2
    assert result.diarization[0].speaker_label == "MIC"
    assert result.diarization[1].speaker_label == "REMOTE_00"


@pytest.mark.asyncio
async def test_mediascribe_client_accepts_contract_segments_without_optional_roles() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_minimal/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_minimal"},
                "transcript": [{"start": 0, "end": 1, "text": "hello"}],
                "diarization": [{"start": 0, "end": 1, "speaker": "SPEAKER_00", "text": "hello"}],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    result = await client.fetch_result("job_minimal")

    assert result.transcript[0].source_role == "incoming"
    assert result.diarization[0].source_role == "incoming"


@pytest.mark.asyncio
async def test_mediascribe_client_preserves_empty_provider_speaker_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_empty_speaker/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_empty_speaker"},
                "transcript": [{"start": 0, "end": 1, "text": "synthetic"}],
                "diarization": [
                    {"start": 0, "end": 1, "speaker_label": "", "text": "synthetic"}
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_result("job_empty_speaker")

    assert result.diarization[0].speaker_label == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("speaker_fields", [{"speaker": None}, {}])
async def test_mediascribe_client_keeps_text_when_provider_speaker_key_is_absent(
    speaker_fields: dict[str, object],
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_absent_speaker/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_absent_speaker"},
                "transcript": [{"start": 0, "end": 1, "text": "synthetic"}],
                "diarization": [
                    {"start": 0, "end": 1, "text": "synthetic", **speaker_fields}
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_result("job_absent_speaker")

    assert result.diarization[0].speaker_label == ""
    assert result.diarization[0].text == "synthetic"


@pytest.mark.asyncio
async def test_mediascribe_client_maps_new_result_transcript_status_contract() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_no_speech/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_no_speech", "status": "ready"},
                "transcript_status": "unavailable",
                "transcript_reason": "no_recognizable_speech",
                "transcript": [],
                "downloads": {},
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_result("job_no_speech")

    assert result.external_job_id == "job_no_speech"
    assert result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
    assert result.transcript_reason == "no_recognizable_speech"
    assert result.transcript == []


@pytest.mark.asyncio
async def test_mediascribe_client_accepts_provider_turns_without_raw_transcript() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_provider_only/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_provider_only", "status": "ready"},
                "transcript_status": "unavailable",
                "transcript": [],
                "diarization": [
                    {
                        "start": 0,
                        "end": 1,
                        "speaker": "voice-a",
                        "text": "synthetic",
                    }
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_result("job_provider_only")

    assert result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
    assert result.transcript == []
    assert result.diarization[0].speaker_label == "voice-a"


@pytest.mark.asyncio
async def test_mediascribe_client_rejects_unknown_transcript_reason() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_bad_reason/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_bad_reason", "status": "ready"},
                "transcript_status": "unavailable",
                "transcript_reason": "private meeting words",
                "transcript": [],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_bad_reason")

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.retryable
    assert "private meeting words" not in str(exc.value)


@pytest.mark.asyncio
async def test_mediascribe_client_rejects_unsupported_transcript_status() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_bad_status/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_bad_status", "status": "ready"},
                "transcript_status": "failed",
                "transcript": [],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_bad_status")

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.retryable
    assert "failed" not in str(exc.value)


@pytest.mark.asyncio
async def test_mediascribe_client_maps_failed_poll_error_code_and_origin() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_invalid_audio"
        return httpx.Response(
            200,
            json={
                "id": "job_invalid_audio",
                "status": "failed",
                "error_code": "invalid_audio_payload",
                "error_origin": "input_audio",
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    poll = await client.poll_job("job_invalid_audio")

    assert poll.status == MediaScribeJobStatus.FAILED
    assert poll.reason_code == "invalid_audio_payload"
    assert poll.error_code == "invalid_audio_payload"
    assert poll.error_origin == "input_audio"


@pytest.mark.asyncio
async def test_mediascribe_client_maps_nested_failed_poll_job_error_code_and_origin() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/jobs/job_invalid_audio"
        return httpx.Response(
            200,
            json={
                "job": {
                    "id": "job_invalid_audio",
                    "status": "failed",
                    "error_code": "invalid_audio_payload",
                    "error_origin": "input_audio",
                }
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    poll = await client.poll_job("job_invalid_audio")

    assert poll.external_job_id == "job_invalid_audio"
    assert poll.status == MediaScribeJobStatus.FAILED
    assert poll.reason_code == "invalid_audio_payload"
    assert poll.error_code == "invalid_audio_payload"
    assert poll.error_origin == "input_audio"
