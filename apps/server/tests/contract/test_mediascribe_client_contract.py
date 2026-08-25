from io import BytesIO

import httpx
import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingAvailabilityStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.mediascribe.schemas import MediaScribeDeletionState


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
    ("status_code", "reason_code", "retryable"),
    [(429, "mediascribe_rate_limited", True), (500, "mediascribe_server_error", False)],
)
async def test_mediascribe_client_marks_retryable_http_responses_as_received(
    status_code: int, reason_code: str, retryable: bool
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
    assert exc.value.retryable is retryable
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
        if request.url.path == "/v1/audio/transcriptions/job_live":
            return httpx.Response(200, json={"id": "job_live", "status": "ready", "result_available": True})
        if request.url.path == "/v1/audio/transcriptions/job_live/result":
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
    assert captured_paths == ["/v1/audio/transcriptions/job_live", "/v1/audio/transcriptions/job_live/result"]
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
        assert request.url.path == "/v1/audio/transcriptions/job_minimal/result"
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

    assert result.transcript[0].source_role == "mixed"
    assert result.diarization[0].source_role == "mixed"


@pytest.mark.asyncio
async def test_mediascribe_client_keeps_v053_words_and_full_text_with_partial_timestamps() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions/job_words/result"
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_words", "source_mode": "single"},
                "transcript": [{"start": 0, "end": 1, "text": "hello world"}],
                "diarization": [
                    {
                        "start": 0,
                        "end": 1,
                        "speaker": "SPEAKER_00",
                        "text": "hello world",
                        "words": [
                            {"word": "hello", "start": 0, "end": 0.4, "probability": 0.98},
                            {"word": "world", "start": None, "end": None, "future": "ignored"},
                        ],
                    }
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    result = await client.fetch_result("job_words")

    assert result.diarization[0].text == "hello world"
    assert [word.word for word in result.diarization[0].words or []] == ["hello", "world"]
    assert result.diarization[0].words[0].probability == 0.98
    assert not hasattr(result.diarization[0].words[1], "future")


@pytest.mark.asyncio
async def test_mediascribe_client_does_not_guess_missing_dual_track_roles() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_dual", "source_mode": "dual"},
                "transcript": [{"start": 0, "end": 1, "text": "hello"}],
                "diarization": [{"start": 0, "end": 1, "speaker": "REMOTE_00", "text": "hello"}],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )
    result = await client.fetch_result("job_dual")

    assert result.transcript[0].source_role == "unknown_provider_state"
    assert result.diarization[0].source_role == "unknown_provider_state"


@pytest.mark.asyncio
async def test_mediascribe_client_rejects_word_item_without_required_word() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "job": {"id": "job_bad_words", "source_mode": "single"},
                "transcript": [{"start": 0, "end": 1, "text": "hello"}],
                "diarization": [
                    {
                        "start": 0,
                        "end": 1,
                        "speaker": "SPEAKER_00",
                        "text": "hello",
                        "words": [{"start": 0, "end": 1}],
                    }
                ],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_bad_words")

    assert exc.value.reason_code == "mediascribe_malformed_response"


@pytest.mark.asyncio
async def test_mediascribe_client_preserves_empty_provider_speaker_key() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions/job_empty_speaker/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_absent_speaker/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_no_speech/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_provider_only/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_bad_reason/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_bad_status/result"
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
        assert request.url.path == "/v1/audio/transcriptions/job_invalid_audio"
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
        assert request.url.path == "/v1/audio/transcriptions/job_invalid_audio"
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


@pytest.mark.asyncio
async def test_v1_poll_preserves_headers_and_unknown_provider_states() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions/job_future"
        assert request.headers["X-Request-ID"] == "graf-poll-1"
        return httpx.Response(
            200,
            headers={
                "X-MediaScribe-API-Version": "v1",
                "X-Request-ID": "provider-poll-1",
                "Retry-After": "11",
                "X-Job-Status": "future_status",
                "X-Queue-State": "future_queue",
            },
            json={
                "id": "job_future",
                "status": "future_status",
                "queue_state": "future_queue",
                "attempt": 2,
                "max_attempts": 5,
                "next_retry_at": "2026-08-23T10:00:00+00:00",
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    poll = await client.poll_job("job_future", request_id="graf-poll-1")

    assert poll.status.value == "future_status"
    assert poll.status.is_known is False
    assert poll.status.safe_value == "unknown_provider_state"
    assert poll.status_projection == "unknown_provider_state"
    assert poll.queue_state is not None
    assert poll.queue_state.value == "future_queue"
    assert poll.queue_state.safe_value == "unknown_provider_state"
    assert poll.retry_after_seconds == 11
    assert poll.request_id == "provider-poll-1"
    assert poll.headers.api_version == "v1"
    assert poll.headers.job_status == "future_status"
    assert poll.headers.queue_state == "future_queue"


@pytest.mark.asyncio
async def test_v1_problem_details_keep_machine_fields_without_using_detail_as_reason() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            headers={
                "X-MediaScribe-API-Version": "v1",
                "X-Request-ID": "provider-result-1",
                "Retry-After": "17",
                "X-Job-Status": "transcribing",
            },
            json={
                "type": "https://mediascribe.test/problems/result_not_ready",
                "title": "Result is not ready",
                "status": 409,
                "detail": "private diagnostic text must not classify the error",
                "instance": "urn:mediascribe:request:req-1",
                "code": "result_not_ready",
                "retryable": True,
                "request_id": "provider-result-body-1",
                "job_id": "job_waiting",
                "errors": [{"field": "result", "reason": "pending"}],
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(MediaScribeClientError) as exc:
        await client.fetch_result("job_waiting")

    error = exc.value
    assert error.reason_code == "result_not_ready"
    assert error.retryable is True
    assert error.status_code == 409
    assert error.retry_after_seconds == 17
    assert error.request_id == "provider-result-1"
    assert error.job_id == "job_waiting"
    assert error.problem is not None
    assert error.problem.code == "result_not_ready"
    assert error.problem.errors == [{"field": "result", "reason": "pending"}]
    assert "private diagnostic text" not in str(error)


@pytest.mark.asyncio
async def test_v1_result_preserves_summary_downloads_provenance_and_unknown_fields() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions/job_result/result"
        return httpx.Response(
            200,
            headers={"X-MediaScribe-API-Version": "v1", "X-Request-ID": "provider-result-2"},
            json={
                "job": {
                    "id": "job_result",
                    "status": "ready",
                    "queue_state": "completed",
                    "source_filename": "meeting.wav",
                    "diarization_enabled": True,
                    "created_at": "2026-08-23T10:00:00+00:00",
                    "updated_at": "2026-08-23T10:01:00+00:00",
                },
                "transcript": [
                    {"start": 0, "end": 1, "text": "hello", "source_role": "future_role", "future_segment": 1}
                ],
                "transcript_status": "available",
                "diarization": [
                    {"start": 0, "end": 1, "speaker": "SPEAKER_00", "text": "hello", "source_role": "incoming"}
                ],
                "acoustic_speaker_turns": [{"start": 0, "end": 1, "speaker": "SPEAKER_00"}],
                "overlaps": [{"start": 0.2, "end": 0.4, "speaker_count": 2}],
                "provenance": {
                    "asr_model_version": "asr-test",
                    "diarization_model_version": "dia-test",
                    "future_provenance_field": {"kept": True},
                },
                "summary": {"status": "running"},
                "downloads": {"archive": "/v1/audio/transcriptions/job_result/downloads/archive"},
                "future_result_field": "kept",
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    result = await client.fetch_result("job_result")

    assert result.job is not None
    assert result.job.status == MediaScribeJobStatus.READY
    assert result.transcript[0].source_role == "future_role"
    assert result.transcript[0].model_extra["future_segment"] == 1
    assert result.diarization is not None
    assert result.acoustic_speaker_turns[0].speaker == "SPEAKER_00"
    assert result.overlaps[0].speaker_count == 2
    assert result.provenance is not None
    assert result.provenance.model_extra["future_provenance_field"] == {"kept": True}
    assert result.summary is not None
    assert result.summary.status.value == "running"
    assert result.summary_status.value == "unavailable"
    assert result.downloads["archive"].startswith("/v1/")
    assert result.model_extra["future_result_field"] == "kept"
    assert result.headers.api_version == "v1"


@pytest.mark.asyncio
async def test_v1_capabilities_version_list_delete_and_download_dtos() -> None:
    requested: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requested.append(request.url.path)
        if request.url.path == "/v1/capabilities":
            assert request.headers["X-Request-ID"] == "capability-check"
            return httpx.Response(
                200,
                headers={"X-MediaScribe-API-Version": "v1", "X-Request-ID": "cap-1"},
                json={
                    "api_contract_version": "v1",
                    "max_upload_size_bytes_per_file": 512,
                    "supported_media_extensions": ["wav"],
                    "max_job_attempts": 3,
                    "queue_dispatch_max_attempts": 3,
                    "queue_dispatch_max_backoff_seconds": 30,
                    "max_active_jobs_per_user": 4,
                    "max_active_jobs_global": 16,
                    "cancellation_grace_seconds": 10,
                    "max_speaker_count_hint": 8,
                    "speaker_count_modes": ["exact", "max"],
                    "summary_available": True,
                },
            )
        if request.url.path == "/version":
            return httpx.Response(
                200,
                headers={"X-MediaScribe-API-Version": "v1", "X-Request-ID": "version-1"},
                json={
                    "api_contract_version": "v1",
                    "service": "mediascribe-api",
                    "service_version": "test",
                    "build_sha": "build-test",
                    "image_digest": "image-test",
                    "queue_contract": "redis-streams-v1",
                    "inference_backend": "test",
                    "inference_runtime": {"status": "ready", "asr_model_version": "asr-test"},
                    "worker_fleet": {"status": "ready", "heartbeat_max_age_seconds": 30},
                    "max_upload_size_bytes_per_file": 512,
                },
            )
        if request.url.path == "/v1/audio/transcriptions" and request.method == "GET":
            assert request.url.params["page"] == "1"
            assert request.url.params["cursor"] == "opaque%2Fcursor" or request.url.params["cursor"] == "opaque/cursor"
            assert "q" not in request.url.params
            return httpx.Response(
                200,
                headers={"X-MediaScribe-API-Version": "v1"},
                json={
                    "object": "list",
                    "data": [
                        {
                            "id": "job_listed",
                            "status": "future_status",
                            "diarization_enabled": True,
                            "summary_enabled": False,
                            "created_at": "2026-08-23T10:00:00+00:00",
                            "updated_at": "2026-08-23T10:00:00+00:00",
                            "retrieve_url": "/v1/audio/transcriptions/job_listed",
                            "result_url": "/v1/audio/transcriptions/job_listed/result",
                        }
                    ],
                    "page": 1,
                    "page_size": 20,
                    "total_items": 1,
                    "total_pages": 1,
                    "has_more": False,
                    "next_cursor": None,
                },
            )
        if request.url.path == "/v1/audio/transcriptions/job_delete" and request.method == "DELETE":
            return httpx.Response(
                202,
                headers={
                    "X-MediaScribe-API-Version": "v1",
                    "X-Job-Deleted": "false",
                    "Location": "/v1/audio/transcriptions/job_delete/deletion",
                    "Retry-After": "3",
                },
                json={
                    "id": "job_delete",
                    "state": "cancelling",
                    "deleted": False,
                    "requested_at": "2026-08-23T10:00:00+00:00",
                    "status_url": "/v1/audio/transcriptions/job_delete/deletion",
                },
            )
        if request.url.path == "/v1/audio/transcriptions/job_delete/deletion":
            return httpx.Response(
                200,
                headers={"X-MediaScribe-API-Version": "v1", "X-Job-Deleted": "true"},
                json={
                    "id": "job_delete",
                    "state": "completed",
                    "deleted": True,
                    "requested_at": "2026-08-23T10:00:00+00:00",
                    "deleted_at": "2026-08-23T10:00:03+00:00",
                    "status_url": "/v1/audio/transcriptions/job_delete/deletion",
                },
            )
        if request.url.path == "/v1/audio/transcriptions/job_download/downloads/transcript":
            return httpx.Response(
                200,
                headers={
                    "X-MediaScribe-API-Version": "v1",
                    "X-Request-ID": "download-1",
                    "Content-Type": "text/plain; charset=utf-8",
                    "Content-Disposition": "attachment; filename=transcript.txt",
                },
                content=b"provider artifact",
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    capabilities = await client.get_capabilities(request_id="capability-check")
    version = await client.get_version()
    jobs = await client.list_jobs(cursor="opaque/cursor")
    deletion = await client.delete_job("job_delete")
    deletion_done = await client.get_deletion("job_delete")
    download = await client.download("/v1/audio/transcriptions/job_download/downloads/transcript")

    assert capabilities.summary_available is True
    assert capabilities.headers.request_id == "cap-1"
    assert version.inference_runtime.asr_model_version == "asr-test"
    assert version.headers.api_version == "v1"
    assert jobs.data[0].status.safe_value == "unknown_provider_state"
    assert jobs.next_cursor is None
    assert deletion.http_status == 202
    assert deletion.state == MediaScribeDeletionState.CANCELLING
    assert deletion.deleted is False
    assert deletion.headers.retry_after_seconds == 3
    assert deletion_done.state == MediaScribeDeletionState.COMPLETED
    assert deletion_done.deleted is True
    assert download.content == b"provider artifact"
    assert download.content_type == "text/plain; charset=utf-8"
    assert requested == [
        "/v1/capabilities",
        "/version",
        "/v1/audio/transcriptions",
        "/v1/audio/transcriptions/job_delete",
        "/v1/audio/transcriptions/job_delete/deletion",
        "/v1/audio/transcriptions/job_download/downloads/transcript",
    ]


@pytest.mark.asyncio
async def test_cursor_cannot_be_mixed_with_filters_or_nonfirst_page() -> None:
    called = False

    async def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal called
        called = True
        return httpx.Response(500, json={})

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(MediaScribeClientError) as filtered:
        await client.list_jobs(cursor="opaque", status="ready")
    with pytest.raises(MediaScribeClientError) as paged:
        await client.list_jobs(cursor="opaque", page=2)

    assert filtered.value.reason_code == "invalid_cursor_filters"
    assert paged.value.reason_code == "invalid_cursor_page"
    assert called is False


@pytest.mark.asyncio
async def test_v1_upload_preserves_202_headers_and_explicit_speaker_options() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/audio/transcriptions"
        assert request.headers["Idempotency-Key"] == "stable-upload-key"
        assert request.headers["X-Request-ID"] == "upload-request-1"
        body = await request.aread()
        assert b'name="num_speakers"' in body
        assert b'\r\n4\r\n' in body
        assert b'name="speaker_count_mode"' in body
        assert b'\r\nmax\r\n' in body
        return httpx.Response(
            202,
            headers={
                "X-MediaScribe-API-Version": "v1",
                "X-Request-ID": "provider-upload-1",
                "Location": "/v1/audio/transcriptions/job_upload",
                "Retry-After": "5",
                "Idempotency-Replayed": "true",
            },
            json={
                "id": "job_upload",
                "status": "uploaded",
                "queue_state": "queued",
                "result_url": "/v1/audio/transcriptions/job_upload/result",
            },
        )

    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-side-key",
        transport=httpx.MockTransport(handler),
    )

    response = await client.submit_single_track(
        media_file=BytesIO(b"audio"),
        media_content_type="audio/wav",
        diarize=True,
        summarize=False,
        num_speakers=4,
        speaker_count_mode="max",
        idempotency_key="stable-upload-key",
        request_id="upload-request-1",
    )

    assert response.http_status == 202
    assert response.external_job_id == "job_upload"
    assert response.idempotency_replayed is True
    assert response.location == "/v1/audio/transcriptions/job_upload"
    assert response.retry_after_seconds == 5
    assert response.headers.api_version == "v1"
