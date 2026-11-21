import asyncio
from hashlib import sha256
from uuid import uuid4

import pytest

from tests.fakes.fake_minio import FakeMinioStorage
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
from twobrain_rec_server.ingest import store as store_module
from twobrain_rec_server.ingest.parts import accept_part
from twobrain_rec_server.ingest.ranges import (
    accepted_bytes_by_track,
    missing_ranges_for_expected_sizes,
)
from twobrain_rec_server.ingest.store import InMemoryIngestStore


def test_changed_part_size_cannot_reuse_accepted_part_number(monkeypatch) -> None:
    """Real acceptance rules preserve ACK; this is not successful native resume."""
    store = InMemoryIngestStore()
    monkeypatch.setattr(store_module, "store", store)
    settings = Settings(
        _env_file=None,
        max_recording_duration_seconds=60,
        max_upload_part_bytes=4 * 1024 * 1024,
        max_track_bytes=2 * 1024 * 1024,
        max_package_bytes=2 * 1024 * 1024,
        upload_session_ttl_seconds=3600,
    )
    scope = TenantScope(uuid4(), uuid4(), uuid4(), uuid4())
    storage = FakeMinioStorage()
    media = deterministic_wav_bytes(960_044)
    prefix = media[:65_536]
    meeting = store.create_or_get_meeting(
        settings=settings,
        organization_id=scope.organization_id,
        workspace_id=scope.workspace_id,
        user_id=scope.user_id,
        device_id=scope.device_id,
        local_recording_id="generated-f200-unaligned-resume",
        duration_seconds=30,
        title=None,
        title_source="legacy_unknown",
    )
    expected_sizes = {TrackRole.MEDIA: len(media)}
    session = store.create_upload_session(
        settings=settings, meeting=meeting, expected_track_sizes=expected_sizes
    )

    async def exercise() -> None:
        first = await accept_part(
            settings=settings,
            tenant_scope=scope,
            storage=storage,
            session_id=session.id,
            track_role=TrackRole.MEDIA,
            part_number=0,
            byte_offset=0,
            content_sha256=sha256(prefix).hexdigest(),
            data=prefix,
        )
        assert first.byte_offset == 0 and first.byte_length == len(prefix)
        assert first.sha256 == sha256(prefix).hexdigest()
        assert storage.objects == {first.object_key: prefix}
        assert accepted_bytes_by_track(session) == {TrackRole.MEDIA: len(prefix)}
        missing = missing_ranges_for_expected_sizes(session, expected_sizes)
        assert missing == {TrackRole.MEDIA: [(len(prefix), len(media))]}
        before_parts = dict(session.parts)
        before_objects = dict(storage.objects)

        start, end = missing[TrackRole.MEDIA][0]
        # Reproduce the current client formula, not a native client execution.
        part_size = 4 * 1024 * 1024
        next_part_number = start // part_size
        assert next_part_number == first.part_number == 0
        tail = media[start : min(end, start + part_size)]
        assert len(tail) == 894_508
        with pytest.raises(ProblemDetail) as rejected:
            await accept_part(
                settings=settings,
                tenant_scope=scope,
                storage=storage,
                session_id=session.id,
                track_role=TrackRole.MEDIA,
                part_number=next_part_number,
                byte_offset=start,
                content_sha256=sha256(tail).hexdigest(),
                data=tail,
            )
        assert rejected.value.status == 409 and rejected.value.code == "range_conflict"
        assert session.parts == before_parts and session.parts[(TrackRole.MEDIA, 0)] is first
        assert (first.byte_offset, first.byte_length, first.sha256) == (
            0, len(prefix), sha256(prefix).hexdigest()
        )
        assert storage.objects == before_objects and not storage.deleted_keys
        assert storage.objects[first.object_key] == prefix
        assert accepted_bytes_by_track(session) == {TrackRole.MEDIA: len(prefix)}
        assert missing_ranges_for_expected_sizes(session, expected_sizes) == missing
        assert session.status == UploadSessionStatus.UPLOADING and session.finalized_at is None
        assert store.audit_events[-1].event_type == "part_conflict"
        assert len(store.meetings) == len(store.sessions) == 1

    asyncio.run(exercise())
