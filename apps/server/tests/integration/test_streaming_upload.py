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
            )
        assert exc.value.status == 413
        assert exc.value.code == "track_bytes_exceeded"

    import asyncio

    asyncio.run(run())
    assert consumed == 2
