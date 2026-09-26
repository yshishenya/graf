import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from twobrain_rec_server.mediascribe.client import MediaScribeClient
from twobrain_rec_server.processing.store import (
    processing_request_fingerprint,
    processing_source_is_retired,
)


@pytest.mark.parametrize("external_id", [None, "known-provider-job"])
def test_revisionless_source_only_allows_a_known_provider_id(external_id):
    db = AsyncMock()
    job = (
        SimpleNamespace(external_job_id=external_id, request_mode="dual_track")
        if external_id
        else None
    )
    assert asyncio.run(
        processing_source_is_retired(
            db,
            workspace_id=uuid4(),
            meeting_id=uuid4(),
            media_revision_id=None,
            job=job,
        )
    ) is (external_id is None)
    db.scalar.assert_not_awaited()


def test_removed_sender_is_not_callable() -> None:
    assert not hasattr(MediaScribeClient, "submit_dual_track")


def test_existing_single_request_fingerprint_is_byte_compatible() -> None:
    # Frozen pre-F275 digest, including null mic/incoming keys, not a digest
    # recomputed from the current implementation's serialization.
    assert (
        processing_request_fingerprint(
            request_mode="single_track",
            source_fingerprint="revision-source",
            source_artifact=SimpleNamespace(
                sha256="a" * 64, byte_length=364, codec="wav-pcm-s16le"
            ),
            diarize=True,
            summarize=False,
            speaker_count_mode=None,
            num_speakers=None,
        )
        == "63a65549e3ff0dbe75c23db07606f5e2c0546e74d403eb989163bbc6620ed80e"
    )
