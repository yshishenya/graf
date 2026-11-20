import asyncio
import fcntl
import json
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from hashlib import sha256
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Event
from time import monotonic
from uuid import uuid4

import pytest

from tests.fakes.auth_contexts import tenant_scope
from twobrain_rec_server.api.schemas import TrackDescriptor
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest import strict_upload
from twobrain_rec_server.ingest.store import UploadPartRecord, UploadSessionRecord
from twobrain_rec_server.storage.strict_upload_writer import StrictUploadWriteError


@pytest.mark.parametrize(("scenario", "reads", "error"), [
    ("ok", [4, 8], None),
    ("gap", [], "protected_upload_track_parts_invalid"),
    ("ordinary_key", [], "protected_upload_track_parts_invalid"),
    ("oversize", [], "protected_upload_track_parts_invalid"),
    ("truncated_part", [4, 8], "protected_upload_track_part_mismatch"),
    ("corrupt_part", [4, 8], "protected_upload_track_part_mismatch"),
    ("wrong_track_hash", [4, 8], "protected_upload_track_digest_mismatch"),
    ("recovery_changed", [4, 8], "protected_upload_recovery_unknown"),
    ("cancelled", [4, 8], None),
    ("cancel_local_copy", [4], None),
])
async def test_assemble_strict_track_only_exposes_verified_stream(tmp_path, monkeypatch, scenario, reads, error):
    scope = tenant_scope()
    session = UploadSessionRecord(
        uuid4(), uuid4(), scope.workspace_id, scope.organization_id, scope.device_id, scope.user_id,
        UploadSessionStatus.UPLOADING, datetime.now(UTC) + timedelta(minutes=1),
        media_revision_id=uuid4(), calendar_match_attempt_id=uuid4(),
        expected_track_sizes={TrackRole.MEDIA: 5},
    )
    role = TrackRole.MEDIA
    payloads = {4: b"ab", 8: b"cde"}
    for number, offset in [(8, 2), (4, 0)]:
        data = payloads[number]
        obj = strict_upload.StrictUploadObject(
            scope.workspace_id, session.meeting_id, session.media_revision_id, session.id, role, number,
        )
        session.parts[role, number] = UploadPartRecord(
            role, number, offset, len(data), sha256(data).hexdigest(), obj.key(scope.organization_id, 3, number), b"",
        )
    if scenario == "gap":
        session.parts[role, 8] = replace(session.parts[role, 8], byte_offset=3)
    elif scenario == "ordinary_key":
        session.parts[role, 8] = replace(session.parts[role, 8], object_key="ordinary")

    track = TrackDescriptor(
        track_role=role, codec="wav", sample_rate_hz=48_000, channel_count=1, duration_seconds=1,
        byte_length=5, sha256=sha256(b"wrong" if scenario == "wrong_track_hash" else b"abcde").hexdigest(),
    )
    recovery = uuid4()
    recovery_path = tmp_path / "recovery"
    lock_path = tmp_path / "recovery.lock"
    lock_path.touch()

    def write_recovery(identifier):
        recovery_path.write_text(json.dumps({
            "schema": 1, "scope": "test-scope", "state": "reconciled", "recovery_id": str(identifier),
        }))

    write_recovery(recovery)
    settings = Settings(
        strict_storage_scope="test-scope",
        strict_storage_recovery_id=recovery,
        strict_storage_recovery_file=recovery_path,
        max_track_bytes=4 if scenario == "oversize" else 5,
    )
    seen = []
    storage = object()

    async def download(db, *, part, destination, **context):
        assert context["session"] is session and context["storage"] is storage
        assert context["recovery"] == str(recovery) and context["deletion_epoch"] == 2
        number = part.part_number
        seen.append(number)
        data = payloads[number]
        if number == 8:
            if scenario == "truncated_part":
                data = data[:-1]
            elif scenario == "corrupt_part":
                data = b"bad"
            elif scenario == "recovery_changed":
                write_recovery(uuid4())
            elif scenario == "cancelled":
                destination.write_bytes(data[:1])
                raise asyncio.CancelledError
        destination.write_bytes(data)
        return len(data)

    monkeypatch.setattr(strict_upload, "download_strict_part", download)
    monkeypatch.setattr(strict_upload, "TemporaryDirectory", partial(TemporaryDirectory, dir=tmp_path))
    operation = strict_upload.assemble_strict_track(
        None, settings=settings, tenant_scope=scope, session=session, track=track, storage=storage,
        recovery=str(recovery), deletion_epoch=2, deadline=monotonic() + 10,
    )
    if scenario == "cancel_local_copy":
        opened = asyncio.Event()
        release = Event()
        loop = asyncio.get_running_loop()
        real_open = Path.open

        def pause_copy(path, *args, **kwargs):
            if path.name == "part" and args == ("rb",):
                loop.call_soon_threadsafe(opened.set)
                assert release.wait(5)
            return real_open(path, *args, **kwargs)

        async def consume():
            async with operation:
                pytest.fail("cancelled track was exposed to the writer")

        monkeypatch.setattr(Path, "open", pause_copy)
        task = asyncio.create_task(consume())
        try:
            await asyncio.wait_for(opened.wait(), timeout=5)
            task.cancel()
            await asyncio.sleep(0)
            task.cancel()
            await asyncio.sleep(0)
            assert not task.done()
            assert list(tmp_path.glob("graf-strict-track-*/part"))
        finally:
            release.set()
        with pytest.raises(asyncio.CancelledError):
            await task
    elif scenario == "ok":
        async with operation as body:
            assert body.tell() == 0 and body.read() == b"abcde"
            with lock_path.open("rb") as lock, pytest.raises(BlockingIOError):
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        assert body.closed
    else:
        with pytest.raises(asyncio.CancelledError if scenario == "cancelled" else StrictUploadWriteError, match=error):
            async with operation:
                pytest.fail("invalid track was exposed to the writer")
    assert seen == reads
    assert {entry.name for entry in tmp_path.iterdir()} == {"recovery", "recovery.lock"}
