from io import BytesIO

import pytest

from tests.fakes.fake_minio import FakeMinioStorage


def test_fake_minio_enforces_exact_declared_stream_length() -> None:
    storage = FakeMinioStorage()

    with pytest.raises(ValueError, match="stream length mismatch"):
        storage.put_stream("too-short", BytesIO(b"ab"), 3)

    with pytest.raises(ValueError, match="stream longer than declared length"):
        storage.put_stream("too-long", BytesIO(b"abcd"), 3)

    storage.put_stream("exact", BytesIO(b"abc"), 3)
    assert storage.objects["exact"] == b"abc"


def test_fake_minio_supports_deterministic_put_failure() -> None:
    storage = FakeMinioStorage(fail_put=True)

    with pytest.raises(RuntimeError, match="configured fake storage failure"):
        storage.put_stream("object", BytesIO(b"abc"), 3)
