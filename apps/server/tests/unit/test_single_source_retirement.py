from types import SimpleNamespace

from twobrain_rec_server.mediascribe.client import MediaScribeClient
from twobrain_rec_server.processing.store import processing_request_fingerprint


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
