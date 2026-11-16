from contextlib import contextmanager
from hashlib import sha256
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from socket import SOCK_STREAM, getaddrinfo
from threading import Event, Thread
from time import monotonic
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from minio import Minio
from minio.error import MinioException
from urllib3.exceptions import ProtocolError

from twobrain_rec_server.storage.strict_upload_writer import (
    PART_BYTES,
    StrictMultipartWrite,
    StrictUploadWriteError,
    StrictUploadWriteTarget,
)

_BUCKET = "test-bucket"
_KEY = (
    f"organizations/{uuid4()}/workspaces/{uuid4()}/meetings/{uuid4()}/"
    f"artifacts/media-revisions/{uuid4()}/attempts/2/7/tracks/media"
)
_UPLOAD_ID = "synthetic+id="
_ETAG = "1" * 32


@contextmanager
def _endpoint(mode="normal"):
    calls = []
    attempt_id = uuid4()
    cancelled = Event()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, *args):
            pass

        def respond(self, body=b"", *, status=200, **headers):
            self.send_response(status)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Content-Type", "application/xml")
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def xml(self, tag, extra):
            return (
                f'<{tag} xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
                f"<Bucket>{_BUCKET}</Bucket><Key>{_KEY}</Key>{extra}</{tag}>"
            ).encode()

        def do_POST(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query, keep_blank_values=True)
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            calls.append((self.command, url.path, query, dict(self.headers), body))
            if (mode == "lost_create" and query == {"uploads": [""]}) or (
                mode == "lost_complete" and query != {"uploads": [""]}
            ):
                self.close_connection = True
                return
            if query == {"uploads": [""]}:
                if mode == "redirect":
                    self.respond(status=307, Location=self.path)
                elif mode == "ambiguous_id":
                    self.respond(self.xml(
                        "InitiateMultipartUploadResult", "<UploadId>first</UploadId><UploadId>second</UploadId>",
                    ))
                else:
                    self.respond(self.xml("InitiateMultipartUploadResult", f"<UploadId>{_UPLOAD_ID}</UploadId>"))
            elif mode == "embedded_error":
                self.respond(self.xml("Error", "<Code>InternalError</Code>"))
            else:
                self.respond(self.xml("CompleteMultipartUploadResult", f'<ETag>"{_ETAG}"</ETag>'))

        def do_PUT(self):
            url = urlsplit(self.path)
            query = parse_qs(url.query, keep_blank_values=True)
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            calls.append((self.command, url.path, query, dict(self.headers), body))
            if mode == "cancel_after_part":
                cancelled.set()
            self.respond(ETag=f'"{_ETAG}"')

    with ThreadingHTTPServer(("127.0.0.1", 0), Handler) as server:
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        port = server.server_address[1]
        endpoint = f"127.0.0.1:{port}"
        target = StrictUploadWriteTarget(
            f"http://{endpoint}", getaddrinfo("127.0.0.1", port, type=SOCK_STREAM), _BUCKET,
            lambda pool: Minio(
                endpoint, secure=False, region="us-east-1", access_key="synthetic-test",
                secret_key="synthetic-test-key", http_client=pool,
            ),
        )
        try:
            yield StrictMultipartWrite(
                target, key=_KEY, epoch=2, attempt_id=attempt_id,
                deadline=monotonic() + 5, cancelled=cancelled,
            ), calls, attempt_id
        finally:
            server.shutdown()
            thread.join(timeout=1)


def test_writer_signs_one_create_two_bounded_parts_and_conditional_complete():
    data = b"a" * PART_BYTES + b"end"
    with _endpoint() as (writer, calls, attempt_id):
        assert writer.create() == _UPLOAD_ID
        with pytest.raises(StrictUploadWriteError, match="create_already_attempted"):
            writer.create()
        with pytest.raises(StrictUploadWriteError, match="id_not_admitted"):
            writer.transfer("different", BytesIO(data), byte_length=len(data), expected_sha256=sha256(data).hexdigest())
        writer.transfer(_UPLOAD_ID, BytesIO(data), byte_length=len(data), expected_sha256=sha256(data).hexdigest())
        with pytest.raises(StrictUploadWriteError, match="id_not_admitted"):
            writer.transfer(_UPLOAD_ID, BytesIO(data), byte_length=len(data), expected_sha256=sha256(data).hexdigest())

    create, first, last, complete = calls
    assert [call[0] for call in calls] == ["POST", "PUT", "PUT", "POST"]
    assert all(call[1] == f"/{_BUCKET}/{_KEY}" for call in calls)
    assert {name.lower(): value for name, value in create[3].items()}["x-amz-meta-graf-upload-attempt"] == str(attempt_id)
    assert first[2] == {"partNumber": ["1"], "uploadId": [_UPLOAD_ID]}
    assert last[2] == {"partNumber": ["2"], "uploadId": [_UPLOAD_ID]}
    assert len(first[4]) == PART_BYTES and last[4] == b"end"
    assert complete[2] == {"uploadId": [_UPLOAD_ID]}
    headers = {name.lower(): value for name, value in complete[3].items()}
    assert headers["if-none-match"] == "*"
    assert "if-none-match" in headers["authorization"].split("SignedHeaders=")[1].split(",")[0].split(";")


@pytest.mark.parametrize(("mode", "expected"), [
    ("redirect", MinioException),
    ("ambiguous_id", StrictUploadWriteError),
    ("lost_create", ProtocolError),
])
def test_create_uncertainty_does_not_send_data_or_retry(mode, expected):
    with _endpoint(mode) as (writer, calls, _):
        with pytest.raises(expected):
            writer.create()
        with pytest.raises(StrictUploadWriteError, match="create_already_attempted"):
            writer.create()
        with pytest.raises(StrictUploadWriteError, match="id_not_admitted"):
            writer.transfer(_UPLOAD_ID, BytesIO(b"x"), byte_length=1, expected_sha256=sha256(b"x").hexdigest())
        assert [call[2] for call in calls] == [{"uploads": [""]}]


@pytest.mark.parametrize(("mode", "digest", "expected", "count"), [
    ("normal", sha256(b"wrong").hexdigest(), "source_invalid", 2),
    ("cancel_after_part", sha256(b"x").hexdigest(), "stopped", 2),
    ("embedded_error", sha256(b"x").hexdigest(), "complete_unconfirmed", 3),
])
def test_transfer_failure_does_not_repeat_or_delete(mode, digest, expected, count):
    with _endpoint(mode) as (writer, calls, _):
        assert writer.create() == _UPLOAD_ID
        with pytest.raises(StrictUploadWriteError, match=expected):
            writer.transfer(_UPLOAD_ID, BytesIO(b"x"), byte_length=1, expected_sha256=digest)
        with pytest.raises(StrictUploadWriteError, match="id_not_admitted"):
            writer.transfer(_UPLOAD_ID, BytesIO(b"x"), byte_length=1, expected_sha256=digest)
        assert [call[0] for call in calls] == ["POST", "PUT", "POST"][:count]


def test_lost_complete_response_does_not_retry_or_delete():
    with _endpoint("lost_complete") as (writer, calls, _):
        upload_id = writer.create()
        with pytest.raises(ProtocolError):
            writer.transfer(upload_id, BytesIO(b"x"), byte_length=1, expected_sha256=sha256(b"x").hexdigest())
        with pytest.raises(StrictUploadWriteError, match="id_not_admitted"):
            writer.transfer(upload_id, BytesIO(b"x"), byte_length=1, expected_sha256=sha256(b"x").hexdigest())
        assert [call[0] for call in calls] == ["POST", "PUT", "POST"]
