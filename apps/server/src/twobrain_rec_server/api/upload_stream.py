from dataclasses import dataclass
from hashlib import sha256
from tempfile import SpooledTemporaryFile
from typing import BinaryIO

from fastapi import Request
from python_multipart.multipart import MultipartParseError, MultipartParser, parse_options_header

from twobrain_rec_server.api.problems import ProblemDetail

MAX_MANUAL_MULTIPART_PARTS = 8
MAX_MANUAL_MULTIPART_HEADERS = 32
MAX_MANUAL_MULTIPART_HEADER_BYTES = 16_384
MAX_MANUAL_MULTIPART_HEADER_NAME_BYTES = 256
MAX_MANUAL_MULTIPART_HEADER_VALUE_BYTES = 8_192

MANUAL_MEDIA_UPLOAD_OPENAPI_EXTRA: dict[str, object] = {
    "requestBody": {
        "required": True,
        "content": {
            "multipart/form-data": {
                "schema": {
                    "type": "object",
                    "properties": {
                        "file": {
                            "type": "string",
                            "contentMediaType": "application/octet-stream",
                            "title": "File",
                        },
                        "duration_seconds": {
                            "type": "integer",
                            "exclusiveMinimum": 0.0,
                            "title": "Duration Seconds",
                        },
                        "title": {
                            "anyOf": [{"type": "string", "maxLength": 500}, {"type": "null"}],
                            "title": "Title",
                        },
                        "local_recording_id": {
                            "anyOf": [
                                {
                                    "type": "string",
                                    "maxLength": 240,
                                    "minLength": 1,
                                    "pattern": r"^[^\x00-\x1f\x7f]+$",
                                },
                                {"type": "null"},
                            ],
                            "title": "Local Recording Id",
                        },
                        "archive_audio": {
                            "type": "boolean",
                            "default": True,
                            "description": "Keep playback audio in the server archive; false keeps it transient only.",
                        },
                    },
                    "required": ["file", "duration_seconds"],
                }
            }
        },
    }
}


@dataclass(slots=True)
class BoundedUploadBody:
    stream: BinaryIO
    byte_length: int
    sha256: str


@dataclass(slots=True)
class ManualMediaUploadBody:
    file: BoundedUploadBody
    filename: str | None
    content_type: str
    duration_seconds: int
    title: str | None
    local_recording_id: str | None
    archive_audio: bool = True


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
            raise ProblemDetail(
                status=400, code="invalid_content_length", title="Invalid Content-Length"
            ) from None
        if declared_bytes < 0:
            raise ProblemDetail(
                status=400, code="invalid_content_length", title="Invalid Content-Length"
            )
        if declared_bytes > max_bytes:
            raise ProblemDetail(
                status=413,
                code="upload_part_bytes_exceeded",
                title="Upload part byte limit exceeded",
            )

    digest = sha256()
    spool = SpooledTemporaryFile(max_size=spool_memory_bytes, mode="w+b")  # noqa: SIM115 - ownership passes to accept_part for streamed storage writes.
    total = 0
    try:
        async for chunk in request.stream():
            if not chunk:
                continue
            total += len(chunk)
            if total > max_bytes:
                raise ProblemDetail(
                    status=413,
                    code="upload_part_bytes_exceeded",
                    title="Upload part byte limit exceeded",
                )
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


def _request_content_length(request: Request) -> int | None:
    content_length = getattr(request, "headers", {}).get("content-length")
    if content_length is None:
        return None
    try:
        declared_bytes = int(content_length)
    except ValueError:
        raise ProblemDetail(
            status=400, code="invalid_content_length", title="Invalid Content-Length"
        ) from None
    if declared_bytes < 0:
        raise ProblemDetail(
            status=400, code="invalid_content_length", title="Invalid Content-Length"
        )
    return declared_bytes


def _multipart_boundary(request: Request) -> bytes:
    content_type = getattr(request, "headers", {}).get("content-type", "")
    media_type, options = parse_options_header(content_type.encode("latin-1"))
    boundary = options.get(b"boundary")
    if media_type != b"multipart/form-data":
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )
    if not boundary:
        raise ProblemDetail(
            status=400, code="invalid_multipart_upload", title="Expected multipart/form-data upload"
        )
    return boundary


def _decode_form_value(value: bytes) -> str:
    return value.decode("utf-8", errors="replace")


def _validate_manual_media_form(
    fields: dict[str, str], file_seen: bool
) -> tuple[int, str | None, str | None, bool]:
    if not file_seen:
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )
    raw_duration = fields.get("duration_seconds")
    try:
        duration_seconds = int(raw_duration or "")
    except ValueError:
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        ) from None
    if duration_seconds <= 0:
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )

    title = fields.get("title")
    if title is not None and len(title) > 500:
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )

    local_recording_id = fields.get("local_recording_id")
    if local_recording_id is not None and (
        not 1 <= len(local_recording_id) <= 240
        or any(ord(ch) < 32 or ord(ch) == 127 for ch in local_recording_id)
    ):
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )
    raw_archive = fields.get("archive_audio", "true").strip().lower()
    if raw_archive not in {"true", "false", "1", "0"}:
        raise ProblemDetail(
            status=422, code="request_validation_error", title="Request validation error"
        )
    archive_audio = raw_archive in {"true", "1"}
    return duration_seconds, title, local_recording_id, archive_audio


async def read_manual_media_upload_body(
    request: Request,
    *,
    max_file_bytes: int,
    spool_memory_bytes: int,
) -> ManualMediaUploadBody:
    # Allow only small multipart overhead around the bounded media part. This
    # rejects obviously oversized bodies before Starlette/FastAPI form parsing
    # can spool attacker-controlled data.
    max_body_bytes = max_file_bytes + 65_536
    declared_bytes = _request_content_length(request)
    if declared_bytes is not None and declared_bytes > max_body_bytes:
        raise ProblemDetail(
            status=413, code="upload_part_bytes_exceeded", title="Upload part byte limit exceeded"
        )

    boundary = _multipart_boundary(request)
    fields: dict[str, str] = {}
    file_spool: BinaryIO | None = None
    file_digest = sha256()
    file_bytes = 0
    file_seen = False
    filename: str | None = None
    content_type = "application/octet-stream"
    current_header_field = bytearray()
    current_header_value = bytearray()
    current_headers: dict[bytes, bytes] = {}
    current_name: str | None = None
    current_is_file = False
    current_field = bytearray()
    total_bytes = 0
    part_count = 0
    header_count = 0
    total_header_bytes = 0

    def on_part_begin() -> None:
        nonlocal current_headers, current_name, current_is_file, current_field, part_count
        part_count += 1
        if part_count > MAX_MANUAL_MULTIPART_PARTS:
            raise ProblemDetail(
                status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
            )
        current_headers = {}
        current_name = None
        current_is_file = False
        current_field = bytearray()

    def on_header_begin() -> None:
        current_header_field.clear()
        current_header_value.clear()

    def on_header_field(data: bytes, start: int, end: int) -> None:
        nonlocal total_header_bytes
        chunk = data[start:end]
        total_header_bytes += len(chunk)
        if (
            len(current_header_field) + len(chunk) > MAX_MANUAL_MULTIPART_HEADER_NAME_BYTES
            or total_header_bytes > MAX_MANUAL_MULTIPART_HEADER_BYTES
        ):
            raise ProblemDetail(
                status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
            )
        current_header_field.extend(chunk.lower())

    def on_header_value(data: bytes, start: int, end: int) -> None:
        nonlocal total_header_bytes
        chunk = data[start:end]
        total_header_bytes += len(chunk)
        if (
            len(current_header_value) + len(chunk) > MAX_MANUAL_MULTIPART_HEADER_VALUE_BYTES
            or total_header_bytes > MAX_MANUAL_MULTIPART_HEADER_BYTES
        ):
            raise ProblemDetail(
                status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
            )
        current_header_value.extend(chunk)

    def on_header_end() -> None:
        nonlocal header_count
        header_count += 1
        if header_count > MAX_MANUAL_MULTIPART_HEADERS:
            raise ProblemDetail(
                status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
            )
        current_headers[bytes(current_header_field)] = bytes(current_header_value)

    def on_headers_finished() -> None:
        nonlocal current_name, current_is_file, file_spool, file_seen, filename, content_type
        disposition, options = parse_options_header(
            current_headers.get(b"content-disposition", b"")
        )
        if disposition != b"form-data":
            raise ProblemDetail(
                status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
            )
        raw_name = options.get(b"name")
        current_name = raw_name.decode("utf-8", errors="replace") if raw_name else None
        current_is_file = current_name == "file"
        if current_is_file:
            if file_seen:
                raise ProblemDetail(
                    status=422, code="request_validation_error", title="Request validation error"
                )
            file_seen = True
            raw_filename = options.get(b"filename")
            filename = (
                raw_filename.decode("utf-8", errors="replace") if raw_filename is not None else None
            )
            raw_content_type = current_headers.get(b"content-type")
            if raw_content_type:
                content_type = raw_content_type.decode("latin-1", errors="replace")
            file_spool = SpooledTemporaryFile(max_size=spool_memory_bytes, mode="w+b")  # noqa: SIM115

    def on_part_data(data: bytes, start: int, end: int) -> None:
        nonlocal file_bytes
        chunk = data[start:end]
        if current_is_file:
            if file_spool is None:
                raise ProblemDetail(
                    status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
                )
            file_bytes += len(chunk)
            if file_bytes > max_file_bytes:
                raise ProblemDetail(
                    status=413,
                    code="upload_part_bytes_exceeded",
                    title="Upload part byte limit exceeded",
                )
            file_digest.update(chunk)
            file_spool.write(chunk)
        elif current_name in {"duration_seconds", "title", "local_recording_id", "archive_audio"}:
            current_field.extend(chunk)
            if len(current_field) > 1024:
                raise ProblemDetail(
                    status=422, code="request_validation_error", title="Request validation error"
                )

    def on_part_end() -> None:
        if not current_is_file and current_name in {
            "duration_seconds",
            "title",
            "local_recording_id",
            "archive_audio",
        }:
            fields[current_name] = _decode_form_value(bytes(current_field))

    parser = MultipartParser(
        boundary,
        callbacks={
            "on_part_begin": on_part_begin,
            "on_header_begin": on_header_begin,
            "on_header_field": on_header_field,
            "on_header_value": on_header_value,
            "on_header_end": on_header_end,
            "on_headers_finished": on_headers_finished,
            "on_part_data": on_part_data,
            "on_part_end": on_part_end,
        },
        max_size=max_body_bytes,
    )
    try:
        async for chunk in request.stream():
            total_bytes += len(chunk)
            if total_bytes > max_body_bytes:
                raise ProblemDetail(
                    status=413,
                    code="upload_part_bytes_exceeded",
                    title="Upload part byte limit exceeded",
                )
            parser.write(chunk)
        parser.finalize()
        duration_seconds, title, local_recording_id, archive_audio = _validate_manual_media_form(
            fields, file_seen
        )
        if file_spool is None:
            raise ProblemDetail(
                status=422, code="request_validation_error", title="Request validation error"
            )
        file_spool.seek(0)
        return ManualMediaUploadBody(
            file=BoundedUploadBody(
                stream=file_spool, byte_length=file_bytes, sha256=file_digest.hexdigest()
            ),
            filename=filename,
            content_type=content_type or "application/octet-stream",
            duration_seconds=duration_seconds,
            title=title,
            local_recording_id=local_recording_id,
            archive_audio=archive_audio,
        )
    except ProblemDetail:
        if file_spool is not None:
            file_spool.close()
        raise
    except MultipartParseError as exc:
        if file_spool is not None:
            file_spool.close()
        raise ProblemDetail(
            status=400, code="invalid_multipart_upload", title="Invalid multipart upload"
        ) from exc
    except Exception:
        if file_spool is not None:
            file_spool.close()
        raise
