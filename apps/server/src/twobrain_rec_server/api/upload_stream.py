from dataclasses import dataclass
from hashlib import sha256
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from fastapi import Request

from twobrain_rec_server.api.problems import ProblemDetail


@dataclass(slots=True)
class BoundedUploadBody:
    stream: BinaryIO
    byte_length: int
    sha256: str


async def read_bounded_upload_body(
    request: Request,
    *,
    expected_sha256: str,
    max_bytes: int,
    spool_memory_bytes: int,
) -> BoundedUploadBody:
    content_length = getattr(request, "headers", {}).get("content-length")
    if content_length is not None:
        try:
            declared_bytes = int(content_length)
        except ValueError:
            raise ProblemDetail(status=400, code="invalid_content_length", title="Invalid Content-Length") from None
        if declared_bytes < 0:
            raise ProblemDetail(status=400, code="invalid_content_length", title="Invalid Content-Length")
        if declared_bytes > max_bytes:
            raise ProblemDetail(status=413, code="upload_part_bytes_exceeded", title="Upload part byte limit exceeded")

    digest = sha256()
    spool = SpooledTemporaryFile(max_size=spool_memory_bytes, mode="w+b")  # noqa: SIM115 - ownership passes to accept_part for streamed storage writes.
    total = 0
    try:
        async for chunk in request.stream():
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ProblemDetail(status=413, code="upload_part_bytes_exceeded", title="Upload part byte limit exceeded")
            digest.update(chunk)
            spool.write(chunk)
        actual_sha = digest.hexdigest()
        if actual_sha != expected_sha256:
            raise ProblemDetail(status=400, code="checksum_mismatch", title="Checksum mismatch")
        spool.seek(0)
        return BoundedUploadBody(stream=spool, byte_length=total, sha256=actual_sha)
    except Exception:
        spool.close()
        raise
