import re
from asyncio import CancelledError
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from threading import Event
from time import monotonic
from urllib.parse import unquote_plus
from uuid import UUID
from xml.etree import ElementTree

from anyio import to_thread
from minio import Minio
from minio.error import S3Error
from urllib3 import PoolManager, Timeout

from twobrain_rec_server.domain.statuses import TrackRole

ATTEMPT_METADATA = "X-Amz-Meta-Graf-Upload-Attempt"
_UUID = r"[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}"
_ROLE = "|".join(TrackRole)
_NUMBER = r"[1-9][0-9]{0,18}"
_STRICT_KEY = re.compile(
    rf"organizations/{_UUID}/workspaces/{_UUID}/meetings/{_UUID}/(?:"
    rf"artifacts/media-revisions/{_UUID}/attempts/(?P<epoch>{_NUMBER})/{_NUMBER}/tracks/(?:{_ROLE})"
    rf"|sessions/{_UUID}/tracks/(?:{_ROLE})/parts/[0-9]{{8,10}}/calendar-attempts/"
    rf"(?P<part_epoch>{_NUMBER})/{_NUMBER})"
)
_LIST_XML = "{http://s3.amazonaws.com/doc/2006-03-01/}"


@dataclass(frozen=True, slots=True)
class StrictUploadCleanupTarget:
    client_with_pool: Callable[[PoolManager], Minio]
    bucket: str
    healthy: Callable[[PoolManager], bool]


# The deployment authority must hold exclusive key ownership and never-versioned bucket
# configuration for the whole lease, using dedicated cleanup credentials.
StrictUploadCleanupAdmission = Callable[
    [str, int, str, UUID], AbstractContextManager[StrictUploadCleanupTarget | None]
]


def _remaining(deadline: float, cancelled: Event) -> float:
    if cancelled.is_set():
        raise TimeoutError("Strict upload cleanup caller stopped")
    remaining = deadline - monotonic()
    if remaining <= 0:
        raise TimeoutError("Strict upload cleanup deadline elapsed")
    return remaining


class _CleanupPool(PoolManager):
    def __init__(self, deadline: float, cancelled: Event) -> None:
        super().__init__()
        self.deadline = deadline
        self.cancelled = cancelled

    def urlopen(self, method, url, redirect=False, **kw):
        kw.update(retries=False, timeout=Timeout(total=_remaining(self.deadline, self.cancelled)))
        return super().urlopen(method, url, redirect=False, **kw)


def strict_upload_key_matches_epoch(key: str, epoch: int) -> bool:
    match = _STRICT_KEY.fullmatch(key)
    return bool(match and (match["epoch"] or match["part_epoch"]) == str(epoch))


async def find_strict_multipart_for_cleanup(
    target: StrictUploadCleanupTarget,
    *,
    key: str,
    deadline: float,
) -> str | None:
    """Read the one complete page using a dedicated list-only credential."""
    cancelled = Event()

    def find() -> str | None:
        _remaining(deadline, cancelled)
        with _CleanupPool(deadline, cancelled) as http:
            client = target.client_with_pool(http)
            if client._http is not http or not client._base_url.region or not target.healthy(http):
                return None
            _remaining(deadline, cancelled)
            response = client._execute(
                "GET", target.bucket,
                query_params={"uploads": "", "prefix": key, "max-uploads": "100", "encoding-type": "url"},
                no_body_trace=True,
            )
            root = ElementTree.fromstring(response.data)
            # A truncated page cannot prove uniqueness. Do not use the SDK cursor:
            # the pinned parser drops NextUploadIdMarker from its public field.
            if (
                root.tag != _LIST_XML + "ListMultipartUploadsResult"
                or root.findtext(_LIST_XML + "Bucket") != target.bucket
                or root.findtext(_LIST_XML + "EncodingType") != "url"
                or [node.text for node in root.findall(_LIST_XML + "IsTruncated")] != ["false"]
            ):
                return None
            matches = []
            for entry in root.findall(_LIST_XML + "Upload"):
                keys = entry.findall(_LIST_XML + "Key")
                ids = entry.findall(_LIST_XML + "UploadId")
                if len(keys) != 1 or len(ids) != 1 or len(keys[0]) or len(ids[0]):
                    return None
                key_text, upload_id = keys[0].text, ids[0].text
                if (
                    not key_text or not upload_id or len(upload_id) > 1024
                    or any(not 33 <= ord(char) <= 126 for char in upload_id)
                ):
                    return None
                name = unquote_plus(key_text)
                if not name.startswith(key):
                    return None
                if name == key:
                    matches.append(upload_id)
            if len(matches) != 1 or not target.healthy(http):
                return None
            _remaining(deadline, cancelled)
            return matches[0]

    try:
        return await to_thread.run_sync(find)
    except CancelledError:
        cancelled.set()
        raise


async def purge_strict_upload_attempt(
    admission: StrictUploadCleanupAdmission,
    *,
    scope: str,
    epoch: int,
    key: str,
    upload_id: str,
    attempt_id: UUID,
    deadline: float,
) -> bool:
    if not scope or not upload_id or not strict_upload_key_matches_epoch(key, epoch):
        return False

    cancelled = Event()

    def purge() -> bool:
        def call(operation, /, *args, **kwargs):
            _remaining(deadline, cancelled)
            return operation(*args, **kwargs)

        _remaining(deadline, cancelled)
        # A timed-out caller must not release the storage lease while its thread is in I/O.
        with (
            admission(scope, epoch, key, attempt_id) as target,
            _CleanupPool(deadline, cancelled) as http,
        ):
            if target is None:
                return False
            client = target.client_with_pool(http)
            if client._http is not http or not call(target.healthy, http):
                return False
            bucket = target.bucket
            try:
                call(client._abort_multipart_upload, bucket, key, upload_id)
            except S3Error as exc:
                if exc.code != "NoSuchUpload":
                    raise
            try:
                call(client._list_parts, bucket, key, upload_id, max_parts=1)
            except S3Error as exc:
                if exc.code != "NoSuchUpload":
                    raise
            else:
                return False

            def stat():
                try:
                    return call(client.stat_object, bucket, key)
                except S3Error as exc:
                    if exc.code not in {"NoSuchKey", "NoSuchObject"}:
                        raise
                    return None

            obj = stat()
            if obj is not None and (obj.metadata or {}).get(ATTEMPT_METADATA) != str(attempt_id):
                return False
            if not call(target.healthy, http):
                return False
            call(client.remove_object, bucket, key)
            verified = stat() is None and call(target.healthy, http)
            _remaining(deadline, cancelled)
            return verified

    try:
        return await to_thread.run_sync(purge)
    except CancelledError:
        cancelled.set()
        raise
