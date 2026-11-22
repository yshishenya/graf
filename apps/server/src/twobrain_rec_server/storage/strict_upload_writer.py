"""Exact, non-retrying transport for one journalled multipart write."""

import re
from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from hashlib import sha256
from math import isfinite
from threading import Event
from time import monotonic
from typing import BinaryIO
from urllib.parse import parse_qsl, urlsplit
from uuid import UUID
from xml.etree import ElementTree as ET

from minio import Minio
from urllib3 import PoolManager

from twobrain_rec_server.storage.strict_source_transport import strict_storage_http
from twobrain_rec_server.storage.strict_upload_cleanup import (
    ATTEMPT_METADATA,
    strict_upload_key_matches_epoch,
)

PART_BYTES = 8 * 1024 * 1024
MAX_PARTS = 10_000
_MAX_RESPONSE_BYTES = 16 * 1024
_XML = "{http://s3.amazonaws.com/doc/2006-03-01/}"
_ETAG = re.compile(r"[a-fA-F0-9]{32}(?:-[1-9][0-9]{0,4})?")
_DIGEST = re.compile(r"[a-f0-9]{64}")


class StrictUploadWriteError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class StrictUploadWriteTarget:
    # Resolved addresses belong to this exact origin, before any DB row lock.
    origin: str
    addresses: list
    bucket: str
    client_with_pool: Callable[[PoolManager], Minio]


def _remaining(deadline: float, cancelled: Event) -> None:
    if not isfinite(deadline) or monotonic() >= deadline or cancelled.is_set():
        raise StrictUploadWriteError("protected_upload_stopped")


def _exact_text(root: ET.Element, tag: str) -> str | None:
    nodes = root.findall(_XML + tag)
    return nodes[0].text if len(nodes) == 1 and not len(nodes[0]) else None


def _valid_upload_id(upload_id: str | None) -> bool:
    return bool(upload_id and len(upload_id) <= 1024 and all(33 <= ord(c) <= 126 for c in upload_id))


class StrictMultipartWrite:
    """One Create, then one transfer with the exact ID confirmed by the caller.

    The caller owns the deployment lease and database journal. Keep both
    through the corresponding I/O; no failure here attempts Abort or Delete.
    """

    def __init__(
        self, target: StrictUploadWriteTarget, *, key: str, epoch: int,
        attempt_id: UUID, deadline: float, cancelled: Event,
    ) -> None:
        origin = urlsplit(target.origin)
        if (
            not strict_upload_key_matches_epoch(key, epoch)
            or origin.scheme not in {"http", "https"} or not origin.hostname
            or origin.username is not None or origin.password is not None
            or origin.path or origin.query or origin.fragment
            or not target.addresses or not target.bucket
        ):
            raise StrictUploadWriteError("protected_upload_target_invalid")
        self._target = target
        self._origin = (origin.scheme, origin.hostname, origin.port)
        self._key = key
        self._attempt_id = attempt_id
        self._deadline = deadline
        self._cancelled = cancelled
        self._create_started = False
        self._transfer_started = False
        self._upload_id: str | None = None

    @contextmanager
    def _client(self):
        expected: tuple[str, dict[str, str]] | None = None

        def permit(method: str, url: str) -> bool:
            nonlocal expected
            parsed = urlsplit(url)
            if (
                (parsed.scheme, parsed.hostname, parsed.port) != self._origin
                or parsed.path != f"/{self._target.bucket}/{self._key}"
                or expected is None
            ):
                return False
            allowed_method, query = expected
            if method != allowed_method or sorted(parse_qsl(parsed.query, keep_blank_values=True)) != sorted(query.items()):
                return False
            expected = None
            return True

        with strict_storage_http(
            self._deadline, self._cancelled, self._target.addresses, permit=permit,
        ) as pool:
            client = self._target.client_with_pool(pool)
            if client._http is not pool or not client._base_url.region or client._provider is None:
                raise StrictUploadWriteError("protected_upload_client_invalid")

            def send(method: str, query: dict[str, str], **kwargs):
                nonlocal expected
                _remaining(self._deadline, self._cancelled)
                expected = (method, query)
                response = client._execute(
                    method, self._target.bucket, self._key, query_params=query,
                    no_body_trace=True, preload_content=False, **kwargs,
                )
                try:
                    if expected is not None or response.status != 200:
                        raise StrictUploadWriteError("protected_upload_response_invalid")
                    body = response.read(_MAX_RESPONSE_BYTES + 1)
                    _remaining(self._deadline, self._cancelled)
                    if len(body) > _MAX_RESPONSE_BYTES:
                        raise StrictUploadWriteError("protected_upload_response_invalid")
                    return response.headers, body
                finally:
                    response.close()
                    response.release_conn()

            yield send

    def create(self) -> str:
        if self._create_started:
            raise StrictUploadWriteError("protected_upload_create_already_attempted")
        self._create_started = True
        with self._client() as send:
            _, body = send("POST", {"uploads": ""}, headers={
                "Content-Type": "application/octet-stream", ATTEMPT_METADATA: str(self._attempt_id),
            })
            root = ET.fromstring(body)
            upload_id = _exact_text(root, "UploadId")
            if (
                root.tag != _XML + "InitiateMultipartUploadResult"
                or _exact_text(root, "Bucket") != self._target.bucket
                or _exact_text(root, "Key") != self._key
                or not _valid_upload_id(upload_id)
            ):
                raise StrictUploadWriteError("protected_upload_create_unconfirmed")
        assert upload_id is not None
        self._upload_id = upload_id
        return upload_id

    def transfer(
        self, upload_id: str, source: BinaryIO, *, byte_length: int, expected_sha256: str,
    ) -> None:
        if self._transfer_started or self._upload_id is None or self._upload_id != upload_id:
            raise StrictUploadWriteError("protected_upload_id_not_admitted")
        self._transfer_started = True
        if not 0 < byte_length <= PART_BYTES * MAX_PARTS or not _DIGEST.fullmatch(expected_sha256):
            raise StrictUploadWriteError("protected_upload_source_invalid")

        digest = sha256()
        completion = ET.Element("CompleteMultipartUpload")
        with self._client() as send:
            for number, offset in enumerate(range(0, byte_length, PART_BYTES), 1):
                _remaining(self._deadline, self._cancelled)
                size = min(PART_BYTES, byte_length - offset)
                body = source.read(size)
                if len(body) != size:
                    raise StrictUploadWriteError("protected_upload_source_invalid")
                digest.update(body)
                headers, _ = send("PUT", {"uploadId": upload_id, "partNumber": str(number)}, body=body)
                etag = headers.get("etag", "").strip('"')
                if not _ETAG.fullmatch(etag):
                    raise StrictUploadWriteError("protected_upload_part_unconfirmed")
                part = ET.SubElement(completion, "Part")
                ET.SubElement(part, "PartNumber").text = str(number)
                ET.SubElement(part, "ETag").text = f'"{etag}"'
            if source.read(1) or digest.hexdigest() != expected_sha256:
                raise StrictUploadWriteError("protected_upload_source_invalid")
            _, body = send("POST", {"uploadId": upload_id}, body=ET.tostring(completion), headers={
                "Content-Type": "application/xml", "If-None-Match": "*",
            })
            root = ET.fromstring(body)
            if (
                root.tag != _XML + "CompleteMultipartUploadResult"
                or _exact_text(root, "Bucket") != self._target.bucket
                or _exact_text(root, "Key") != self._key
                or not _ETAG.fullmatch((_exact_text(root, "ETag") or "").strip('"'))
            ):
                raise StrictUploadWriteError("protected_upload_complete_unconfirmed")
        _remaining(self._deadline, self._cancelled)
