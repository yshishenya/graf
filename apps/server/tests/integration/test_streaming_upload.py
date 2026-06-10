import pytest
from starlette.datastructures import State

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.upload_stream import read_bounded_upload_body


class StreamingRequest:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks
        self.app = type("App", (), {"state": State()})()

    async def stream(self):
        for chunk in self._chunks:
            yield chunk


def test_bounded_upload_stream_rejects_before_consuming_all_chunks() -> None:
    consumed = 0

    class CountingRequest:
        async def stream(self):
            nonlocal consumed
            for chunk in [b"aaaa", b"bbbb", b"cccc"]:
                consumed += 1
                yield chunk

    async def run() -> None:
        with pytest.raises(ProblemDetail) as exc:
            await read_bounded_upload_body(
                CountingRequest(),  # type: ignore[arg-type]
                expected_sha256="0" * 64,
                max_bytes=6,
                spool_memory_bytes=4,
            )
        assert exc.value.status == 413
        assert exc.value.code == "upload_part_bytes_exceeded"

    import asyncio

    asyncio.run(run())
    assert consumed == 2


def test_successful_bounded_upload_returns_spooled_stream_not_bytes() -> None:
    import asyncio
    from hashlib import sha256

    data = b"aaaabbbbcccc"

    async def run():
        body = await read_bounded_upload_body(
            StreamingRequest([data[:4], data[4:8], data[8:]]),  # type: ignore[arg-type]
            expected_sha256=sha256(data).hexdigest(),
            max_bytes=64,
            spool_memory_bytes=4,
        )
        assert body.byte_length == len(data)
        assert body.sha256 == sha256(data).hexdigest()
        assert not isinstance(body, bytes)
        assert getattr(body.stream, "_rolled", False) is True
        assert body.stream.read() == data
        body.stream.close()

    asyncio.run(run())


def test_upload_part_limit_rejects_before_storage_write(client) -> None:
    from hashlib import sha256

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fixtures.artifacts import deterministic_wav_bytes

    client.app.state.settings.max_upload_part_bytes = 3
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "streaming-part-limit", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"system": 4}},
    ).json()
    data = deterministic_wav_bytes(4)
    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": sha256(data).hexdigest()},
        content=data,
    )

    assert response.status_code == 413
    assert response.json()["code"] == "upload_part_bytes_exceeded"
    assert client.app_state["storage"].objects == {}
