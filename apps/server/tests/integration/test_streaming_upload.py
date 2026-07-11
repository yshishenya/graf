import pytest
from starlette.datastructures import State

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.upload_stream import read_bounded_upload_body


class StreamingRequest:
    def __init__(self, chunks: list[bytes], headers: dict[str, str] | None = None) -> None:
        self._chunks = chunks
        self.headers = headers or {}
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


def test_bounded_upload_stream_rejects_declared_oversize_before_streaming() -> None:
    consumed = 0

    class CountingRequest(StreamingRequest):
        async def stream(self):
            nonlocal consumed
            consumed += 1
            yield b"aaaa"

    async def run() -> None:
        with pytest.raises(ProblemDetail) as exc:
            await read_bounded_upload_body(
                CountingRequest([b"aaaa"], headers={"content-length": "12"}),  # type: ignore[arg-type]
                expected_sha256="0" * 64,
                max_bytes=6,
                spool_memory_bytes=4,
            )
        assert exc.value.status == 413
        assert exc.value.code == "upload_part_bytes_exceeded"

    import asyncio

    asyncio.run(run())
    assert consumed == 0


def test_bounded_upload_stream_rejects_invalid_declared_size_before_streaming() -> None:
    async def run(header_value: str) -> None:
        with pytest.raises(ProblemDetail) as exc:
            await read_bounded_upload_body(
                StreamingRequest([b"aaaa"], headers={"content-length": header_value}),  # type: ignore[arg-type]
                expected_sha256="0" * 64,
                max_bytes=6,
                spool_memory_bytes=4,
            )
        assert exc.value.status == 400
        assert exc.value.code == "invalid_content_length"

    import asyncio

    asyncio.run(run("not-a-number"))
    asyncio.run(run("-1"))


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


def _multipart_body(boundary: str, file_bytes: bytes) -> bytes:
    return (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"duration_seconds\"\r\n\r\n60\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"title\"\r\n\r\nUploaded\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"meeting.wav\"\r\n"
        f"Content-Type: audio/wav\r\n\r\n"
    ).encode() + file_bytes + f"\r\n--{boundary}--\r\n".encode()


def test_manual_media_multipart_stream_rejects_declared_oversize_before_streaming() -> None:
    import asyncio

    from twobrain_rec_server.api.upload_stream import read_manual_media_upload_body

    consumed = 0

    class CountingRequest(StreamingRequest):
        async def stream(self):
            nonlocal consumed
            consumed += 1
            yield b"unused"

    async def run() -> None:
        with pytest.raises(ProblemDetail) as exc:
            await read_manual_media_upload_body(
                CountingRequest(
                    [b"unused"],
                    headers={
                        "content-type": "multipart/form-data; boundary=manual",
                        "content-length": str(65_536 + 12),
                    },
                ),  # type: ignore[arg-type]
                max_file_bytes=10,
                spool_memory_bytes=4,
            )
        assert exc.value.status == 413
        assert exc.value.code == "upload_part_bytes_exceeded"

    asyncio.run(run())
    assert consumed == 0


def test_manual_media_multipart_stream_spools_file_without_whole_file_bytes() -> None:
    import asyncio
    from hashlib import sha256

    from twobrain_rec_server.api.upload_stream import read_manual_media_upload_body

    boundary = "manual"
    data = b"a" * 12
    body = _multipart_body(boundary, data)

    async def run() -> None:
        upload = await read_manual_media_upload_body(
            StreamingRequest(
                [body[:40], body[40:90], body[90:]],
                headers={
                    "content-type": f"multipart/form-data; boundary={boundary}",
                    "content-length": str(len(body)),
                },
            ),  # type: ignore[arg-type]
            max_file_bytes=64,
            spool_memory_bytes=4,
        )
        assert upload.duration_seconds == 60
        assert upload.title == "Uploaded"
        assert upload.filename == "meeting.wav"
        assert upload.content_type == "audio/wav"
        assert upload.file.byte_length == len(data)
        assert upload.file.sha256 == sha256(data).hexdigest()
        assert getattr(upload.file.stream, "_rolled", False) is True
        assert upload.file.stream.read() == data
        upload.file.stream.close()

    asyncio.run(run())
