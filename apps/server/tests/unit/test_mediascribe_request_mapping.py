from io import BytesIO

import httpx
import pytest

from twobrain_rec_server.mediascribe.client import MediaScribeClient


@pytest.mark.asyncio
async def test_dual_track_request_uses_mic_and_incoming_without_mixed_or_silence_flags() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        body = await request.aread()
        assert b'name="mic_file"' in body
        assert b'name="incoming_file"' in body
        assert b"name=\"mixed_file\"" not in body
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
    )
    assert response.external_job_id == "job_mapping"
