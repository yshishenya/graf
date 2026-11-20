import asyncio
from contextlib import contextmanager
from threading import Event
from time import monotonic
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import quote_plus
from uuid import uuid4

import pytest
from minio import Minio
from minio.error import S3Error
from urllib3.response import HTTPResponse

from twobrain_rec_server.storage.strict_upload_cleanup import (
    ATTEMPT_METADATA,
    StrictUploadCleanupTarget,
    find_strict_multipart_for_cleanup,
    purge_strict_upload_attempt,
)


@pytest.mark.parametrize(
    ("names", "complete", "upload_id", "expected"),
    [
        (("", "/prefix-sibling"), "false", "id", "id-0"),
        (("/prefix-sibling",), "false", "id", None),
        (("", ""), "false", "id", None),
        (("",), "true", "id", None),
        (("",), "", "id", None),
        (("",), "false", " ", None),
        (("",), "false", "id<unexpected/>", None),
    ],
)
async def test_multipart_discovery_requires_one_exact_match_in_complete_page(
    names, complete, upload_id, expected
) -> None:
    key = "synthetic/exact/key"
    uploads = "".join(
        f"<Upload><Key>{quote_plus(key + suffix)}</Key><UploadId>{upload_id}-{i}</UploadId></Upload>"
        for i, suffix in enumerate(names)
    )
    client = Mock(spec=Minio)
    client._base_url = SimpleNamespace(region="us-east-1")
    client._execute.return_value = HTTPResponse(body=(
        '<ListMultipartUploadsResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
        f"<Bucket>isolated</Bucket><EncodingType>url</EncodingType>"
        f"<IsTruncated>{complete}</IsTruncated>{uploads}</ListMultipartUploadsResult>"
    ).encode())

    def with_pool(pool):
        client._http = pool
        return client

    target = StrictUploadCleanupTarget(with_pool, "isolated", lambda pool: True)
    assert await find_strict_multipart_for_cleanup(
        target, key=key, deadline=monotonic() + 5
    ) == expected
    client._execute.assert_called_once_with(
        "GET", "isolated",
        query_params={"uploads": "", "prefix": key, "max-uploads": "100", "encoding-type": "url"},
        no_body_trace=True,
    )
    client._abort_multipart_upload.assert_not_called()
    client.remove_object.assert_not_called()


def s3_error(code: str, status: int) -> S3Error:
    return S3Error(HTTPResponse(status=status), code, None, None, None, None)


@pytest.mark.parametrize(
    ("failure", "delete_sent"),
    [
        ("no-admission", False),
        ("abort-response-lost", False),
        ("upload-still-present", False),
        ("head-unavailable", False),
        ("health-lost-before-delete", False),
        ("delete-response-lost", True),
        ("object-still-present", True),
        ("health-lost-after-delete", True),
    ],
)
async def test_unverified_cleanup_never_reports_success(failure, delete_sent) -> None:
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"artifacts/media-revisions/{uuid4()}/attempts/1/2/tracks/media"
    )
    attempt = uuid4()
    client = Mock(spec=Minio)
    client._list_parts.side_effect = s3_error("NoSuchUpload", 404)
    own = SimpleNamespace(metadata={ATTEMPT_METADATA: str(attempt)})
    client.stat_object.side_effect = [own, s3_error("NoSuchKey", 404)]
    healthy = Mock(return_value=True)
    if failure == "abort-response-lost":
        client._abort_multipart_upload.side_effect = TimeoutError
    elif failure == "upload-still-present":
        client._list_parts.side_effect = None
    elif failure == "head-unavailable":
        client.stat_object.side_effect = s3_error("XMinioReadQuorum", 503)
    elif failure == "health-lost-before-delete":
        healthy.side_effect = [True, False]
    elif failure == "delete-response-lost":
        client.remove_object.side_effect = TimeoutError
    elif failure == "object-still-present":
        client.stat_object.side_effect = [own, own]
    elif failure == "health-lost-after-delete":
        healthy.side_effect = [True, True, False]

    @contextmanager
    def admit(scope, epoch, candidate_key, candidate_attempt):
        assert (scope, epoch, candidate_key, candidate_attempt) == ("scope", 1, key, attempt)

        def client_with_pool(pool):
            client._http = pool
            return client

        yield (
            None
            if failure == "no-admission"
            else StrictUploadCleanupTarget(client_with_pool, "isolated", healthy)
        )

    def purge():
        return purge_strict_upload_attempt(
            admit,
            scope="scope",
            epoch=1,
            key=key,
            upload_id="exact-id",
            attempt_id=attempt,
            deadline=monotonic() + 5,
        )

    if failure.endswith("response-lost"):
        with pytest.raises(TimeoutError):
            await purge()
    elif failure == "head-unavailable":
        with pytest.raises(S3Error, match="XMinioReadQuorum"):
            await purge()
    else:
        assert await purge() is False
    if failure == "no-admission":
        assert not client.mock_calls
    else:
        client._abort_multipart_upload.assert_called_once_with("isolated", key, "exact-id")
    if delete_sent:
        client.remove_object.assert_called_once_with("isolated", key)
    else:
        client.remove_object.assert_not_called()


async def test_timeout_holds_admission_until_inflight_abort_stops() -> None:
    key = (
        f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
        f"sessions/{uuid4()}/tracks/system/parts/00000001/calendar-attempts/1/2"
    )
    entered_abort, release_abort, lease_exited = Event(), Event(), Event()
    client = Mock(spec=Minio)

    def abort(*args):
        entered_abort.set()
        assert release_abort.wait(5)

    def client_with_pool(pool):
        client._http = pool
        return client

    client._abort_multipart_upload.side_effect = abort

    @contextmanager
    def admit(*args):
        try:
            yield StrictUploadCleanupTarget(client_with_pool, "isolated", lambda pool: True)
        finally:
            lease_exited.set()

    task = asyncio.create_task(
        purge_strict_upload_attempt(
            admit,
            scope="scope",
            epoch=1,
            key=key,
            upload_id="exact-id",
            attempt_id=uuid4(),
            deadline=monotonic() + 5,
        )
    )
    try:
        assert await asyncio.to_thread(entered_abort.wait, 2)
        with pytest.raises(TimeoutError):
            await asyncio.wait_for(task, timeout=0.02)
        assert not lease_exited.is_set()
    finally:
        release_abort.set()
    assert await asyncio.to_thread(lease_exited.wait, 2)
    client._list_parts.assert_not_called()
    client.stat_object.assert_not_called()
    client.remove_object.assert_not_called()
