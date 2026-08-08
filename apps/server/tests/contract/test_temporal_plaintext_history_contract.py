from __future__ import annotations

import json
from copy import deepcopy

import pytest

from twobrain_rec_server.workflows.outcome_generation_workflow import (
    SERIALIZED_PAYLOAD_BYTES,
    TRANSCRIPT_CHUNK_BYTES,
    TRANSCRIPT_MAX_BYTES,
    TranscriptSnapshotError,
    split_plaintext_transcript,
    validate_plaintext_snapshot,
)


def test_complete_plaintext_transcript_is_chunked_and_reconstructed_exactly() -> None:
    transcript = ("Спикер: проверяем полный открытый текст 🚀\n" * 15_000).rstrip()
    metadata, chunks = split_plaintext_transcript(
        transcript,
        candidate_id="candidate",
        source_result_id="result",
    )
    assert len(chunks) > 1
    assert max(len(chunk["transcript_utf8"].encode("utf-8")) for chunk in chunks) <= (
        TRANSCRIPT_CHUNK_BYTES
    )
    assert validate_plaintext_snapshot(metadata, chunks) == transcript
    assert all("transcript_utf8" in chunk for chunk in chunks)


def test_snapshot_rejects_order_duplicate_hash_and_identity_changes() -> None:
    metadata, chunks = split_plaintext_transcript(
        "текст" * 60_000,
        candidate_id="candidate",
        source_result_id="result",
    )
    reversed_chunks = list(reversed(chunks))
    with pytest.raises(TranscriptSnapshotError, match="order"):
        validate_plaintext_snapshot(metadata, reversed_chunks)
    changed = deepcopy(chunks)
    changed[-1]["transcript_utf8"] += "подмена"
    with pytest.raises(TranscriptSnapshotError, match="size|hash"):
        validate_plaintext_snapshot(metadata, changed)
    changed = deepcopy(chunks)
    changed[0]["candidate_id"] = "other"
    with pytest.raises(TranscriptSnapshotError, match="identity"):
        validate_plaintext_snapshot(metadata, changed)


def test_snapshot_ceiling_fails_before_any_model_call() -> None:
    with pytest.raises(TranscriptSnapshotError, match="oversize"):
        split_plaintext_transcript(
            "x" * (TRANSCRIPT_MAX_BYTES + 1),
            candidate_id="candidate",
            source_result_id="result",
        )
    assert TRANSCRIPT_CHUNK_BYTES < SERIALIZED_PAYLOAD_BYTES


def test_json_escaping_reduces_chunks_instead_of_rejecting_valid_snapshot() -> None:
    transcript = "\\" * TRANSCRIPT_CHUNK_BYTES
    metadata, chunks = split_plaintext_transcript(
        transcript,
        candidate_id="candidate",
        source_result_id="result",
    )

    assert len(chunks) > 1
    assert validate_plaintext_snapshot(metadata, chunks) == transcript
    assert all(
        len(json.dumps(chunk, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        <= SERIALIZED_PAYLOAD_BYTES
        for chunk in chunks
    )
