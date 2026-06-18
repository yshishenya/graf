from __future__ import annotations

import pytest

from tests.fixtures.recording_sync import revision_aware_recording_fixture
from twobrain_rec_server.ingest.media_revisions import (
    MediaRevisionFingerprintConflict,
    ensure_media_revision_fingerprint_is_immutable,
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
            new_manifest_sha256="b" * 64,
            new_track_sha256_by_role=fixture.track_sha256_by_role,
        )

    with pytest.raises(MediaRevisionFingerprintConflict):
        ensure_media_revision_fingerprint_is_immutable(
            existing_manifest_sha256=fixture.manifest_sha256,
            existing_track_sha256_by_role=fixture.track_sha256_by_role,
            new_manifest_sha256=fixture.manifest_sha256,
            new_track_sha256_by_role=fixture.track_sha256_by_role | {"microphone": "c" * 64},
        )
