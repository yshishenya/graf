import httpx
import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
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
        mic_bytes=b"mic",
        incoming_bytes=b"incoming",
        diarize=True,
        summarize=False,
    )
    assert captured == {"path": "/v1/audio/transcriptions/dual-track", "api_key": "server-side-key"}
    assert response.external_job_id == "job_contract"
    assert response.status == MediaScribeJobStatus.UPLOADED


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
            mic_bytes=b"mic",
            incoming_bytes=b"incoming",
            diarize=True,
            summarize=False,
        )

    assert exc.value.reason_code == "mediascribe_malformed_response"
    assert exc.value.retryable
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
