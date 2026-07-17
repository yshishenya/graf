from __future__ import annotations

from uuid import UUID

import pytest

from tests.fixtures.recording_sync import revision_aware_recording_fixture
from twobrain_rec_server.domain.statuses import MediaRevisionSourceKind
from twobrain_rec_server.ingest.media_revisions import (
    MediaRevisionFingerprintConflict,
    authoritative_track_roles,
    ensure_media_revision_fingerprint_is_immutable,
    source_fingerprint_sha256,
    track_sha256_by_role,
)


def test_track_sha256_by_role_uses_transport_roles() -> None:
    fixture = revision_aware_recording_fixture("fingerprint-roles-001")

    assert track_sha256_by_role(fixture.expected_tracks) == fixture.track_sha256_by_role


def test_accepted_media_revision_fingerprint_is_immutable() -> None:
    fixture = revision_aware_recording_fixture("fingerprint-immutable-001")

    ensure_media_revision_fingerprint_is_immutable(
        existing_manifest_sha256=fixture.manifest_sha256,
        existing_track_sha256_by_role=fixture.track_sha256_by_role,
        new_manifest_sha256=fixture.manifest_sha256,
        new_track_sha256_by_role=fixture.track_sha256_by_role,
    )
    with pytest.raises(MediaRevisionFingerprintConflict):
        ensure_media_revision_fingerprint_is_immutable(
            existing_manifest_sha256=fixture.manifest_sha256,
            existing_track_sha256_by_role=fixture.track_sha256_by_role,
            new_manifest_sha256=fixture.manifest_sha256,
            new_track_sha256_by_role=fixture.track_sha256_by_role | {"microphone": "c" * 64},
        )

    with pytest.raises(MediaRevisionFingerprintConflict):
        ensure_media_revision_fingerprint_is_immutable(
            existing_manifest_sha256=fixture.manifest_sha256,
            existing_track_sha256_by_role=fixture.track_sha256_by_role,
            new_manifest_sha256="b" * 64,
            new_track_sha256_by_role=fixture.track_sha256_by_role,
        )


def test_v5_mixed_revision_uses_only_media_as_authoritative_source() -> None:
    digests = {
        "manifest": "a" * 64,
        "media": "b" * 64,
        "playback": "c" * 64,
    }

    assert authoritative_track_roles(MediaRevisionSourceKind.INITIAL_MIXED_RECORDING) == ("media",)
    original = source_fingerprint_sha256(
        media_revision_id=UUID("00000000-0000-0000-0000-000000000106"),
        source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING,
        manifest_sha256=digests["manifest"],
        track_sha256_by_role=digests,
        duration_seconds=60,
    )
    changed_playback = source_fingerprint_sha256(
        media_revision_id=UUID("00000000-0000-0000-0000-000000000106"),
        source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING,
        manifest_sha256=digests["manifest"],
        track_sha256_by_role=digests | {"playback": "d" * 64},
        duration_seconds=60,
    )
    changed_media = source_fingerprint_sha256(
        media_revision_id=UUID("00000000-0000-0000-0000-000000000106"),
        source_kind=MediaRevisionSourceKind.INITIAL_MIXED_RECORDING,
        manifest_sha256=digests["manifest"],
        track_sha256_by_role=digests | {"media": "e" * 64},
        duration_seconds=60,
    )

    assert original == changed_playback
    assert original != changed_media
