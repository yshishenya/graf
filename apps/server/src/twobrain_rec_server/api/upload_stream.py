from hashlib import sha256

from fastapi import Request
from twobrain_rec_server.api.problems import ProblemDetail


async def read_bounded_upload_body(
    request: Request,
    *,
    expected_sha256: str,
    max_bytes: int,
) -> bytes:
    digest = sha256()
    chunks: list[bytes] = []
    total = 0
    async for chunk in request.stream():
        if not chunk:
            continue
        total += len(chunk)
        if total > max_bytes:
            raise ProblemDetail(status=413, code="track_bytes_exceeded", title="Track byte limit exceeded")
        digest.update(chunk)
        chunks.append(chunk)
    if digest.hexdigest() != expected_sha256:
        raise ProblemDetail(status=400, code="checksum_mismatch", title="Checksum mismatch")
    return b"".join(chunks)
