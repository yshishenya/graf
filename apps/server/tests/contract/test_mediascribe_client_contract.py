import httpx
import pytest

from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError


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
