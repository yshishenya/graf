from __future__ import annotations

import json
from datetime import timedelta
from hashlib import sha256
from string import ascii_letters, digits
from typing import Any

TRANSCRIPT_CHUNK_BYTES = 196_608
SERIALIZED_PAYLOAD_BYTES = 262_144
TRANSCRIPT_MAX_BYTES = 8_388_608
_SAFE_FAILURE_CODE_CHARS = frozenset(ascii_letters + digits + "_:-.")


def _safe_failure_code(exc: BaseException) -> str:
    """Keep only bounded machine codes when projecting a workflow failure."""
    value = exc.args[0] if exc.args and isinstance(exc.args[0], str) else ""
    if 0 < len(value) <= 120 and set(value) <= _SAFE_FAILURE_CODE_CHARS:
        return value
    return "summary_generation_retries_exhausted"


class TranscriptSnapshotError(ValueError):
    pass


def split_plaintext_transcript(
    transcript: str,
    *,
    candidate_id: str,
    source_result_id: str,
    max_chunk_bytes: int = TRANSCRIPT_CHUNK_BYTES,
    max_snapshot_bytes: int = TRANSCRIPT_MAX_BYTES,
    max_serialized_bytes: int = SERIALIZED_PAYLOAD_BYTES,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    encoded = transcript.encode("utf-8")
    if len(encoded) > max_snapshot_bytes:
        raise TranscriptSnapshotError("outcome_transcript_oversize")
    digest = sha256(encoded).hexdigest()
    texts = _serialized_safe_utf8_chunks(
        encoded,
        candidate_id=candidate_id,
        source_result_id=source_result_id,
        snapshot_hash=digest,
        max_chunk_bytes=max_chunk_bytes,
        max_serialized_bytes=max_serialized_bytes,
    )
    chunk_count = len(texts)
    chunks: list[dict[str, Any]] = []
    for index, text in enumerate(texts):
        chunk = {
            "candidate_id": candidate_id,
            "source_result_id": source_result_id,
            "snapshot_hash": digest,
            "chunk_index": index,
            "chunk_count": chunk_count,
            "transcript_utf8": text,
        }
        if len(_temporal_json_bytes(chunk)) > max_serialized_bytes:
            raise TranscriptSnapshotError("outcome_transcript_chunk_serialized_oversize")
        chunks.append(chunk)
    metadata = {
        "candidate_id": candidate_id,
        "source_result_id": source_result_id,
        "snapshot_hash": digest,
        "chunk_count": chunk_count,
        "transcript_bytes": len(encoded),
    }
    return metadata, chunks


def validate_plaintext_snapshot(
    metadata: dict[str, Any],
    chunks: list[dict[str, Any]],
    *,
    max_chunk_bytes: int = TRANSCRIPT_CHUNK_BYTES,
    max_snapshot_bytes: int = TRANSCRIPT_MAX_BYTES,
    max_serialized_bytes: int = SERIALIZED_PAYLOAD_BYTES,
) -> str:
    expected_count = metadata.get("chunk_count")
    if not isinstance(expected_count, int) or expected_count != len(chunks):
        raise TranscriptSnapshotError("outcome_transcript_chunk_count_invalid")
    if [chunk.get("chunk_index") for chunk in chunks] != list(range(expected_count)):
        raise TranscriptSnapshotError("outcome_transcript_chunk_order_invalid")
    identities = {
        (
            chunk.get("candidate_id"),
            chunk.get("source_result_id"),
            chunk.get("snapshot_hash"),
            chunk.get("chunk_count"),
        )
        for chunk in chunks
    }
    expected_identity = {
        (
            metadata.get("candidate_id"),
            metadata.get("source_result_id"),
            metadata.get("snapshot_hash"),
            expected_count,
        )
    }
    if identities != expected_identity:
        raise TranscriptSnapshotError("outcome_transcript_chunk_identity_invalid")
    texts: list[str] = []
    for chunk in chunks:
        text = chunk.get("transcript_utf8")
        if not isinstance(text, str):
            raise TranscriptSnapshotError("outcome_transcript_chunk_utf8_invalid")
        if len(text.encode("utf-8")) > max_chunk_bytes:
            raise TranscriptSnapshotError("outcome_transcript_chunk_oversize")
        if len(_temporal_json_bytes(chunk)) > max_serialized_bytes:
            raise TranscriptSnapshotError("outcome_transcript_chunk_serialized_oversize")
        texts.append(text)
    transcript = "".join(texts)
    encoded = transcript.encode("utf-8")
    if len(encoded) != metadata.get("transcript_bytes") or len(encoded) > max_snapshot_bytes:
        raise TranscriptSnapshotError("outcome_transcript_size_invalid")
    if sha256(encoded).hexdigest() != metadata.get("snapshot_hash"):
        raise TranscriptSnapshotError("outcome_transcript_hash_invalid")
    return transcript


def _serialized_safe_utf8_chunks(
    encoded: bytes,
    *,
    candidate_id: str,
    source_result_id: str,
    snapshot_hash: str,
    max_chunk_bytes: int,
    max_serialized_bytes: int,
) -> list[str]:
    if not encoded:
        return [""]
    texts: list[str] = []
    start = 0
    # One UTF-8 byte per chunk is the largest possible count/index width. Using
    # that width while fitting makes the later real metadata strictly no larger.
    conservative_position = len(encoded)
    while start < len(encoded):
        requested = min(max_chunk_bytes, len(encoded) - start)
        while requested > 0:
            end = start + requested
            while end > start:
                try:
                    text = encoded[start:end].decode("utf-8")
                    break
                except UnicodeDecodeError as exc:
                    end = start + exc.start if exc.start > 0 else end - 1
            else:
                requested //= 2
                continue
            consumed = len(text.encode("utf-8"))
            provisional = {
                "candidate_id": candidate_id,
                "source_result_id": source_result_id,
                "snapshot_hash": snapshot_hash,
                "chunk_index": conservative_position,
                "chunk_count": conservative_position,
                "transcript_utf8": text,
            }
            if consumed > 0 and len(_temporal_json_bytes(provisional)) <= max_serialized_bytes:
                texts.append(text)
                start += consumed
                break
            requested //= 2
        else:
            raise TranscriptSnapshotError("outcome_transcript_chunk_serialized_oversize")
    return texts


def _temporal_json_bytes(value: object) -> bytes:
    # Temporal's default JSON payload adds metadata outside this encoded body;
    # the 64-KiB margin between 192 and 256 KiB covers that fixed envelope.
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )


def outcome_generation_retry_policy():
    from temporalio.common import RetryPolicy

    return RetryPolicy(
        initial_interval=timedelta(seconds=10),
        backoff_coefficient=2,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=6,
        non_retryable_error_types=[
            "OutcomeGenerationTerminalError",
            "TranscriptSnapshotError",
        ],
    )


def outcome_observability_retry_policy():
    from temporalio.common import RetryPolicy

    # Generation is already committed before this activity starts. Keep the
    # observability delivery durable without replaying model inference and
    # without adding a timer/activity pair to workflow history every five minutes.
    return RetryPolicy(
        initial_interval=timedelta(seconds=10),
        backoff_coefficient=2,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=0,
        non_retryable_error_types=["OutcomeGenerationTerminalError"],
    )


try:
    from temporalio import workflow
    from temporalio.workflow import ParentClosePolicy
except Exception:  # pragma: no cover - narrow docs/unit environment
    workflow = None


if workflow is not None:

    @workflow.defn
    class OutcomeObservabilityReconcilerWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            cycles = 0
            while True:
                state = await workflow.execute_activity(
                    "publish_outcome_observability_activity",
                    payload,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_observability_retry_policy(),
                )
                if state["candidate_terminal"] and int(state["pending_count"]) == 0:
                    return state
                cycles += 1
                if cycles >= 1_000:
                    workflow.continue_as_new(payload)
                await workflow.sleep(timedelta(seconds=15))

    @workflow.defn
    class OutcomeGenerationWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            reconciler_enabled = workflow.patched("outcome-observability-reconciler-v1")
            try:
                if reconciler_enabled:
                    info = workflow.info()
                    await workflow.start_child_workflow(
                        OutcomeObservabilityReconcilerWorkflow.run,
                        {
                            **payload,
                            "generation_workflow_id": info.workflow_id,
                            "generation_workflow_run_id": info.run_id,
                        },
                        # Parent retries get a new run ID while an abandoned
                        # reconciler may still be draining. Keep child IDs
                        # unique per parent run; the publish activity is durable
                        # and idempotent on the candidate/call locks.
                        id=f"outcome-observability/{payload['candidate_id']}/{info.run_id}",
                        parent_close_policy=ParentClosePolicy.ABANDON,
                    )
                resolved = await workflow.execute_activity(
                    "resolve_outcome_prompt_config_activity",
                    payload,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_generation_retry_policy(),
                )
                metadata = await workflow.execute_activity(
                    "snapshot_outcome_transcript_metadata_activity",
                    payload,
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_generation_retry_policy(),
                )
                chunks: list[dict[str, Any]] = []
                for chunk_index in range(int(metadata["chunk_count"])):
                    chunk = await workflow.execute_activity(
                        "snapshot_outcome_transcript_chunk_activity",
                        {**payload, "chunk_index": chunk_index},
                        start_to_close_timeout=timedelta(minutes=2),
                        retry_policy=outcome_generation_retry_policy(),
                    )
                    chunks.append(chunk)
                validate_plaintext_snapshot(metadata, chunks)
                generated = await workflow.execute_activity(
                    "execute_outcome_generation_activity",
                    {
                        **payload,
                        "prompt_hash": resolved["prompt_hash"],
                        "snapshot_hash": metadata["snapshot_hash"],
                        "chunk_count": metadata["chunk_count"],
                    },
                    start_to_close_timeout=timedelta(minutes=5),
                    retry_policy=outcome_generation_retry_policy(),
                )
            except TranscriptSnapshotError as exc:
                # This validation runs inside the deterministic workflow, not
                # inside an activity wrapper. Preserve the bounded terminal
                # code instead of projecting a malformed snapshot as a
                # retryable provider failure.
                await workflow.execute_activity(
                    "finalize_outcome_generation_failure_activity",
                    {**payload, "failure_code": str(exc)},
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_generation_retry_policy(),
                )
                raise
            except Exception as exc:
                failure_code = _safe_failure_code(exc)
                await workflow.execute_activity(
                    "finalize_outcome_generation_failure_activity",
                    {
                        **payload,
                        "failure_code": failure_code,
                        "failure_reason": failure_code,
                    },
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_generation_retry_policy(),
                )
                raise
            if not reconciler_enabled:
                await workflow.execute_activity(
                    "publish_outcome_observability_activity",
                    {**payload, "generation_call_id": generated["generation_call_id"]},
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=outcome_observability_retry_policy(),
                )
            return generated

else:

    class OutcomeGenerationWorkflow:
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            return payload

    class OutcomeObservabilityReconcilerWorkflow:
        async def run(self, payload: dict[str, Any]) -> dict[str, Any]:
            return payload
