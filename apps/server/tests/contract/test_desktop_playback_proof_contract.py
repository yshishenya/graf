from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from twobrain_rec_server.api.schemas import PlaybackPreparationState
from twobrain_rec_server.cabinet import egress
from twobrain_rec_server.cabinet.access import AccessDecision


def _meeting() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        workspace_id=uuid4(),
        deletion_state="none",
        deleted_at=None,
    )


def _revision() -> SimpleNamespace:
    return SimpleNamespace(
        id=uuid4(),
        local_media_revision_id=f"local-revision-{uuid4()}",
    )


def _access() -> AccessDecision:
    return AccessDecision(
        state="owner",
        label="Owner",
        reason=None,
        can_view=True,
        can_share=True,
        can_manage_team_visibility=True,
        can_download=True,
        can_export=True,
        role="owner",
    )


class _Storage:
    def __init__(
        self,
        *,
        data: bytes | None = None,
        size: int | None = None,
        fail_stat: Exception | None = None,
        fail_read: Exception | None = None,
        stat_delay: float = 0.0,
    ) -> None:
        self.data = data
        self.size = size if size is not None else (len(data) if data is not None else 0)
        self.fail_stat = fail_stat
        self.fail_read = fail_read
        self.stat_delay = stat_delay
        self.read_lengths: list[int] = []

    async def stat_object_async(self, object_key: str):
        if self.stat_delay:
            await asyncio.sleep(self.stat_delay)
        if self.fail_stat is not None:
            raise self.fail_stat
        return SimpleNamespace(size=self.size)

    def iter_object(self, object_key: str, *, offset: int = 0, length: int | None = None):
        self.read_lengths.append(length or 0)
        if self.fail_read is not None:
            raise self.fail_read
        payload = self.data if self.data is not None else b"x" * self.size
        end = len(payload) if length is None else min(offset + length, len(payload))
        return iter([payload[offset:end]])


def _patch_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    revision: SimpleNamespace,
    playback: PlaybackPreparationState,
    artifact: SimpleNamespace | None,
    archive_audio: bool,
) -> list[tuple[object, object]]:
    calls: list[tuple[object, object]] = []

    async def fake_latest(db, *, workspace_id, meeting_id):
        return revision

    async def fake_review(db, *, meeting, access, storage, revision):
        return playback

    async def fake_archive(db, *, workspace_id, meeting_id, media_revision_id):
        calls.append((meeting_id, media_revision_id))
        return archive_audio

    async def fake_artifact(db, *, meeting, revision):
        calls.append((meeting.id, revision.id))
        if artifact is None:
            raise egress.ReviewAudioBuildError("missing_playback_artifact")
        return artifact

    monkeypatch.setattr(egress, "_latest_accepted_media_revision", fake_latest)
    monkeypatch.setattr(egress, "review_playback_state", fake_review)
    monkeypatch.setattr(egress, "archive_audio_for_revision", fake_archive)
    monkeypatch.setattr(egress, "_stored_review_m4a_artifact", fake_artifact)
    return calls


def _artifact(storage: _Storage, *, byte_length: int | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        storage_object_key="meetings/test/meeting-review.m4a",
        byte_length=byte_length if byte_length is not None else storage.size,
    )


@pytest.mark.asyncio
async def test_ready_playback_with_verified_object_is_proven(monkeypatch) -> None:
    revision = _revision()
    storage = _Storage(data=b"a" * 32_768)
    calls = _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )
    meeting = _meeting()

    proof = await egress.desktop_playback_proof(
        object(), meeting=meeting, access=_access(), storage=storage
    )

    assert proof.state == "available"
    assert proof.can_play is True
    assert proof.reason_code == "canonical_ready"
    assert proof.object_verified is True
    assert proof.verified_at is not None
    assert proof.media_revision_id == revision.id
    assert proof.local_media_revision_id == revision.local_media_revision_id
    assert proof.local_media_revision_id != str(proof.media_revision_id)
    assert (meeting.id, revision.id) in calls
    assert 12 * 1024 <= storage.read_lengths[0] <= 64 * 1024


@pytest.mark.asyncio
async def test_missing_object_is_fail_closed(monkeypatch) -> None:
    revision = _revision()
    storage = _Storage(data=b"x" * 16)
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )
    storage.fail_stat = KeyError("missing")

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=storage
    )

    assert proof.state == "preparing"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert proof.reason_code == "canonical_artifact_missing"
    assert proof.verified_at is None


@pytest.mark.asyncio
async def test_size_mismatch_is_fail_closed(monkeypatch) -> None:
    revision = _revision()
    storage = _Storage(data=b"x" * 16)
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )
    storage.size = 17

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=storage
    )

    assert proof.state == "preparing"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert proof.reason_code == "canonical_artifact_missing"


@pytest.mark.asyncio
async def test_bounded_read_failure_is_fail_closed(monkeypatch) -> None:
    revision = _revision()
    storage = _Storage(data=b"x" * 16, fail_read=RuntimeError("read failed"))
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=storage
    )

    assert proof.state == "preparing"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert proof.reason_code == "reconciliation_pending"
    assert proof.automatic_recovery is True
    assert proof.media_revision_id == revision.id
    assert proof.local_media_revision_id == revision.local_media_revision_id


@pytest.mark.asyncio
async def test_storage_none_is_fail_closed(monkeypatch) -> None:
    revision = _revision()
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(_Storage(data=b"x" * 16)),
        archive_audio=True,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=None
    )

    assert proof.state == "preparing"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert proof.reason_code == "reconciliation_pending"


@pytest.mark.asyncio
async def test_stat_timeout_is_fail_closed(monkeypatch) -> None:
    revision = _revision()
    storage = _Storage(data=b"x" * 16, stat_delay=0.05)
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )

    proof = await egress.desktop_playback_proof(
        object(),
        meeting=_meeting(),
        access=_access(),
        storage=storage,
        timeout=0.001,
    )

    assert proof.state == "preparing"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert proof.reason_code == "reconciliation_pending"


@pytest.mark.asyncio
async def test_archive_audio_false_blocks_playback_proof(monkeypatch) -> None:
    revision = _revision()
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(_Storage(data=b"x" * 16)),
        archive_audio=False,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=_Storage(data=b"x" * 16)
    )

    assert proof.state == "unavailable"
    assert proof.can_play is False
    assert proof.reason_code == "audio_not_archived"
    assert proof.object_verified is False
    assert proof.media_revision_id == revision.id
    assert proof.local_media_revision_id == revision.local_media_revision_id


@pytest.mark.asyncio
async def test_terminal_and_deleting_states_are_preserved_without_verification(monkeypatch) -> None:
    revision = _revision()
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="unavailable", reason_code="corrupt_source", can_play=False
        ),
        artifact=None,
        archive_audio=True,
    )

    terminal = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=_Storage(data=b"x")
    )
    assert terminal.state == "unavailable"
    assert terminal.reason_code == "corrupt_source"
    assert terminal.automatic_recovery is False
    assert terminal.object_verified is False

    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="deleting", reason_code="meeting_deleting", can_play=False
        ),
        artifact=None,
        archive_audio=True,
    )
    deleting = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=_Storage(data=b"x")
    )
    assert deleting.state == "deleting"
    assert deleting.can_play is False
    assert deleting.media_revision_id == revision.id

    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="unavailable", reason_code="access_denied", can_play=False
        ),
        artifact=None,
        archive_audio=True,
    )
    denied = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=_Storage(data=b"x")
    )
    assert denied.state == "unavailable"
    assert denied.reason_code == "access_denied"
    assert denied.can_play is False
    assert denied.object_verified is False


@pytest.mark.asyncio
async def test_missing_playback_artifact_is_canonical_missing(monkeypatch) -> None:
    revision = _revision()
    _patch_dependencies(
        monkeypatch,
        revision=revision,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=None,
        archive_audio=True,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=_meeting(), access=_access(), storage=_Storage(data=b"x")
    )

    assert proof.state == "preparing"
    assert proof.reason_code == "canonical_artifact_missing"
    assert proof.automatic_recovery is True


@pytest.mark.asyncio
async def test_pinned_older_revision_is_used_for_archive_and_artifact_lookup(monkeypatch) -> None:
    older = _revision()
    newer = _revision()
    meeting = _meeting()
    storage = _Storage(data=b"x" * 4096)
    calls = _patch_dependencies(
        monkeypatch,
        revision=older,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(storage),
        archive_audio=True,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=meeting, access=_access(), storage=storage
    )

    assert proof.media_revision_id == older.id
    assert newer.id != older.id
    assert (meeting.id, older.id) in calls


@pytest.mark.asyncio
async def test_pinned_older_revision_archive_false_blocks_newer_archive_choice(monkeypatch) -> None:
    older = _revision()
    newer = _revision()
    meeting = _meeting()
    calls = _patch_dependencies(
        monkeypatch,
        revision=older,
        playback=PlaybackPreparationState(
            state="available", reason_code="canonical_ready", can_play=True
        ),
        artifact=_artifact(_Storage(data=b"x" * 4096)),
        archive_audio=False,
    )

    proof = await egress.desktop_playback_proof(
        object(), meeting=meeting, access=_access(), storage=_Storage(data=b"x" * 4096)
    )

    assert newer.id != older.id
    assert proof.media_revision_id == older.id
    assert proof.reason_code == "audio_not_archived"
    assert proof.can_play is False
    assert proof.object_verified is False
    assert (meeting.id, older.id) in calls
