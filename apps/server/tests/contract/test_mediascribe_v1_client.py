from io import BytesIO

import pytest

from tests.fakes.mediascribe_v1 import MediaScribeV1Fixture
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient
from twobrain_rec_server.mediascribe.schemas import MediaScribeDeletionState


@pytest.mark.asyncio
async def test_v1_fixture_covers_capabilities_single_dual_status_result_and_deletion() -> None:
    fixture = MediaScribeV1Fixture()
    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-only-key",
        transport=fixture.transport(),
    )

    capabilities = await client.get_capabilities(request_id="capability-fixture")
    single = await client.submit_single_track(
        media_file=BytesIO(b"wav"),
        media_content_type="audio/wav",
        media_filename="fixture.wav",
        diarize=True,
        summarize=False,
        idempotency_key="fixture-single-key",
    )
    dual = await client.submit_dual_track(
        mic_file=BytesIO(b"mic"),
        incoming_file=BytesIO(b"incoming"),
        diarize=True,
        summarize=False,
        idempotency_key="fixture-dual-key",
    )
    status = await client.poll_job(single.external_job_id)
    result = await client.fetch_result(single.external_job_id)
    deletion = await client.delete_job(single.external_job_id)

    assert capabilities.dual_track_supported
    assert capabilities.summary_available
    assert single.external_job_id == dual.external_job_id == fixture.job_id
    assert status.status == MediaScribeJobStatus.READY
    assert result.diarization
    assert result.summary_status.value == "unavailable"
    assert deletion.state == MediaScribeDeletionState.COMPLETED
    assert fixture.submissions == ["fixture-single-key", "fixture-dual-key"]
    assert all("server-only-key" not in path for _, path in fixture.calls)


@pytest.mark.asyncio
async def test_v1_fixture_preserves_retry_hint_and_same_key_replay() -> None:
    fixture = MediaScribeV1Fixture(status="transcribing", retry_after="17", replayed=True)
    client = MediaScribeClient(
        base_url="https://mediascribe.test",
        api_key="server-only-key",
        transport=fixture.transport(),
    )

    first = await client.submit_single_track(
        media_file=BytesIO(b"wav"),
        media_content_type="audio/wav",
        media_filename="fixture.wav",
        diarize=True,
        summarize=False,
        idempotency_key="same-key",
    )
    replay = await client.submit_single_track(
        media_file=BytesIO(b"wav"),
        media_content_type="audio/wav",
        media_filename="fixture.wav",
        diarize=True,
        summarize=False,
        idempotency_key="same-key",
    )

    assert first.external_job_id == replay.external_job_id
    assert first.idempotency_replayed is True
    assert first.retry_after_seconds == 17
    assert fixture.submissions == ["same-key"]
