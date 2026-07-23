from __future__ import annotations

import asyncio
import json
import os
import re
import stat
import tempfile
import threading
from collections.abc import Awaitable, Callable, Collection, Mapping, Sequence
from contextlib import asynccontextmanager, suppress
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Protocol
from uuid import UUID, uuid4
from zipfile import ZIP_DEFLATED, ZipFile

from twobrain_rec_server.outcomes.prompts import (
    CONTROL_GATE_CONFIG_KEY,
    JUDGE_VARIABLES,
    PromptSnapshot,
    canonical_json,
    langfuse_prompt_payload,
    prompt_variables,
    validate_outcome_result,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES

OPTIMIZER_VERSION = "0.1.4"
ADAPTER_VERSION = "graf-gepa-v1"
CHECKPOINT_SCHEMA_VERSION = "graf-gepa-checkpoint-v1"
CHECKPOINT_PREFIX = "_system/prompt-optimization"
GEPA_CHECKPOINT_FILES = frozenset({"gepa_state.bin", "run_log.json", "candidates.json"})
MAX_CHECKPOINT_BYTES = 64 * 1024 * 1024
OPTIMIZATION_HISTORY_CHUNK_BYTES = 196_608
OPTIMIZATION_HISTORY_PAYLOAD_BYTES = 262_144
OPTIMIZATION_HISTORY_MAX_BYTES = 8_388_608
OPTIMIZATION_HISTORY_SCHEMA_VERSION = "graf-prompt-optimization-history-v1"
OPTIMIZATION_HISTORY_MATERIALIZATION_KEY = "temporal_history_materialization"
OPTIMIZATION_HISTORY_STAGING_KEY = "temporal_history_staging"
PROMPT_COMPONENT = "outcome_prompt"
JUDGE_NAMES = tuple(JUDGE_VARIABLES)
CALL_PHASES = (
    "task",
    "reflection",
    "judge_faithfulness",
    "judge_action_items",
    "judge_completeness",
)
TASK_MODEL_VARIABLE_KEYS = frozenset(
    {"transcript_json", "output_language", "detail_level", "template_sections_json"}
)


async def _run_thread_until_quiescent(
    function: Callable[..., Any],
    /,
    *args: object,
    on_cancel: Callable[[], None],
    complete_after_cancel: bool = False,
    cancellation_observed: threading.Event | None = None,
    **kwargs: object,
) -> Any:
    """Keep a cancelled activity alive until its current worker thread stops."""

    thread_task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    cancellation_requested = False
    while True:
        try:
            result = await asyncio.shield(thread_task)
        except asyncio.CancelledError:
            # ``to_thread`` cannot interrupt its thread. Re-signal the
            # cooperative stopper and wait for the bounded safe boundary before
            # Temporal may acknowledge activity cancellation.
            cancellation_requested = True
            if cancellation_observed is not None:
                cancellation_observed.set()
            with suppress(Exception):
                on_cancel()
            continue
        except Exception:
            if cancellation_requested and not complete_after_cancel:
                raise asyncio.CancelledError from None
            raise
        if cancellation_requested and not complete_after_cancel:
            raise asyncio.CancelledError
        return result


async def _complete_async_operation_until_quiescent(
    operation: Awaitable[Any],
    *,
    cancellation_observed: threading.Event | None = None,
    complete_after_cancel: bool,
) -> Any:
    """Finish one async commit-boundary operation before cancellation escapes."""

    operation_task = asyncio.ensure_future(operation)
    cancellation_requested = False
    while True:
        try:
            result = await asyncio.shield(operation_task)
        except asyncio.CancelledError:
            if operation_task.cancelled():
                raise
            cancellation_requested = True
            if cancellation_observed is not None:
                cancellation_observed.set()
            continue
        except Exception:
            # A failed commit must remain retryable even when cancellation raced
            # it; reporting cancellation here could strand an external mutation.
            raise
        if cancellation_requested and not complete_after_cancel:
            raise asyncio.CancelledError
        return result


async def _commit_database_until_quiescent(
    db: Any,
    *,
    cancellation_observed: threading.Event | None = None,
    complete_after_cancel: bool,
) -> None:
    await _complete_async_operation_until_quiescent(
        db.commit(),
        cancellation_observed=cancellation_observed,
        complete_after_cancel=complete_after_cancel,
    )


@asynccontextmanager
async def _quiescent_session_scope(
    session: Any,
    *,
    cancellation_observed: threading.Event | None = None,
    complete_after_cancel: bool,
):
    """Keep AsyncSession exit/rollback inside the activity commit boundary."""

    db = await session.__aenter__()
    try:
        yield db
    except BaseException as exc:
        await _complete_async_operation_until_quiescent(
            session.__aexit__(type(exc), exc, exc.__traceback__),
            cancellation_observed=cancellation_observed,
            complete_after_cancel=complete_after_cancel,
        )
        raise
    else:
        await _complete_async_operation_until_quiescent(
            session.__aexit__(None, None, None),
            cancellation_observed=cancellation_observed,
            complete_after_cancel=complete_after_cancel,
        )


def validate_history_materialization_certificate(
    value: object,
    *,
    phase: str,
) -> dict[str, object]:
    expected_keys = {"bytes", "chunk_count", "snapshot_hash", "status"}
    if phase not in {"evolution", "heldout"} or not isinstance(value, Mapping):
        raise PromptOptimizationError("optimization_history_materialization_invalid")
    byte_count = value.get("bytes")
    chunk_count = value.get("chunk_count")
    snapshot_hash = value.get("snapshot_hash")
    if (
        set(value) != expected_keys
        or value.get("status") != "complete"
        or not isinstance(byte_count, int)
        or isinstance(byte_count, bool)
        or not 1 <= byte_count <= OPTIMIZATION_HISTORY_MAX_BYTES
        or not isinstance(chunk_count, int)
        or isinstance(chunk_count, bool)
        or not 1 <= chunk_count <= OPTIMIZATION_HISTORY_MAX_BYTES
        or not isinstance(snapshot_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", snapshot_hash)
    ):
        raise PromptOptimizationError("optimization_history_materialization_invalid")
    return dict(value)


def optimization_trace_id(run_id: UUID) -> str:
    from langfuse import Langfuse

    return Langfuse.create_trace_id(seed=f"prompt-optimization/{run_id}")


def rollback_trace_id(run_id: UUID, rollback_version: int) -> str:
    from langfuse import Langfuse

    return Langfuse.create_trace_id(seed=f"prompt-rollback/{run_id}/{rollback_version}")


def optimization_terminal_observation_id(run_id: UUID) -> str:
    seed = f"prompt-optimization/{run_id}/terminal"
    return sha256(seed.encode("utf-8")).digest()[:8].hex()


class PromptOptimizationError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class PromptOptimizationReconciliationError(RuntimeError):
    """Retryable failure after an external prompt mutation may have started."""


@dataclass(frozen=True, slots=True)
class SyntheticExample:
    id: str
    transcript_json: str
    segment_ids: frozenset[str]
    required_categories: tuple[str, ...]
    human_labels: Mapping[str, Literal["pass", "fail"]] = field(default_factory=dict)
    forbidden_copy_fragments: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.id or len(self.id) > 120:
            raise ValueError("synthetic example id is invalid")
        if len(self.transcript_json.encode("utf-8")) > 262_144:
            raise ValueError("synthetic example is too large")
        if set(self.human_labels) - set(JUDGE_NAMES):
            raise ValueError("synthetic example has an unknown judge label")
        if any(label not in {"pass", "fail"} for label in self.human_labels.values()):
            raise ValueError("synthetic example has an invalid human label")
        if any(not fragment or len(fragment) > 240 for fragment in self.forbidden_copy_fragments):
            raise ValueError("synthetic forbidden-copy fragment is invalid")


@dataclass(frozen=True, slots=True)
class SyntheticManifest:
    ref: str
    split: Literal["train", "development", "heldout"]
    version: str
    examples: tuple[SyntheticExample, ...]
    sha256: str

    @classmethod
    def create(
        cls,
        *,
        ref: str,
        split: Literal["train", "development", "heldout"],
        version: str,
        examples: Sequence[SyntheticExample],
    ) -> SyntheticManifest:
        if not ref.startswith("synthetic://") or len(ref) > 500:
            raise ValueError("only immutable synthetic manifest references are accepted")
        if not version or len(version) > 120:
            raise ValueError("synthetic manifest version is invalid")
        frozen_examples = tuple(examples)
        if not frozen_examples or len({item.id for item in frozen_examples}) != len(
            frozen_examples
        ):
            raise ValueError("synthetic manifest examples must be non-empty and unique")
        payload = _manifest_payload(split=split, version=version, examples=frozen_examples)
        return cls(
            ref=ref,
            split=split,
            version=version,
            examples=frozen_examples,
            sha256=sha256(payload).hexdigest(),
        )

    def verify(self) -> None:
        payload = _manifest_payload(
            split=self.split,
            version=self.version,
            examples=self.examples,
        )
        if sha256(payload).hexdigest() != self.sha256:
            raise PromptOptimizationError("synthetic_manifest_hash_mismatch")


def validate_disjoint_manifests(
    train: SyntheticManifest,
    development: SyntheticManifest,
    heldout: SyntheticManifest,
) -> None:
    manifests = (train, development, heldout)
    if tuple(item.split for item in manifests) != ("train", "development", "heldout"):
        raise PromptOptimizationError("synthetic_manifest_split_mismatch")
    for manifest in manifests:
        manifest.verify()
    ids = [set(item.id for item in manifest.examples) for manifest in manifests]
    if ids[0] & ids[1] or ids[0] & ids[2] or ids[1] & ids[2]:
        raise PromptOptimizationError("synthetic_manifest_split_overlap")


@dataclass(frozen=True, slots=True)
class OptimizationBudget:
    max_calls: int
    max_tokens: int
    max_cost: Decimal
    deadline_at: datetime

    def __post_init__(self) -> None:
        if self.max_calls < 1 or self.max_tokens < 1 or self.max_cost < 0:
            raise ValueError("optimization budget is invalid")
        if self.deadline_at.tzinfo is None:
            raise ValueError("optimization deadline must be timezone-aware")


@dataclass(frozen=True, slots=True)
class CallReservation:
    call_key: str
    phase: str
    fence: UUID
    status: Literal["reserved", "succeeded", "ambiguous"]
    reserved_tokens: int
    reserved_cost: Decimal
    result: object | None = None


class FencedCallLedger(Protocol):
    def reserve(
        self,
        *,
        call_key: str,
        phase: str,
        activity_attempt: int,
        now: datetime,
        token_ceiling: int,
        cost_ceiling: Decimal,
    ) -> CallReservation: ...

    def succeed(
        self,
        *,
        call_key: str,
        fence: UUID,
        result: object,
        actual_tokens: int | None,
        actual_cost: Decimal | None,
    ) -> None: ...

    def fail(self, *, call_key: str, fence: UUID) -> None: ...

    def charged_totals(self) -> tuple[int, int, Decimal]: ...


@dataclass(frozen=True, slots=True)
class PersistedCallReservation:
    call_key: str
    fence: UUID
    status: Literal["reserved", "succeeded"]
    result_artifact_ref: str | None = None


async def reserve_persisted_call(
    db: Any,
    *,
    run_id: UUID,
    call_key: str,
    phase: str,
    prompt_version: int,
    config_hash: str,
    model_route: str,
    token_ceiling: int,
    cost_ceiling: Decimal,
    activity_attempt: int,
    now: datetime,
    lease_seconds: int = 120,
) -> PersistedCallReservation:
    from sqlalchemy import select

    from twobrain_rec_server.db.models import (
        PromptOptimizationCallLedger,
        PromptOptimizationRun,
    )

    if phase not in CALL_PHASES or token_ceiling < 1 or cost_ceiling < 0:
        raise ValueError("optimization reservation is invalid")
    run = await db.scalar(
        select(PromptOptimizationRun).where(PromptOptimizationRun.id == run_id).with_for_update()
    )
    if run is None or run.deployment_scope != "global":
        raise PromptOptimizationError("optimization_run_not_found")
    if run.status not in {"queued", "running", "paused"}:
        raise PromptOptimizationError("optimization_run_not_active")
    if now >= run.deadline_at:
        raise PromptOptimizationError("optimization_deadline_exceeded")
    rows = list(
        (
            await db.scalars(
                select(PromptOptimizationCallLedger)
                .where(PromptOptimizationCallLedger.run_id == run_id)
                .with_for_update()
            )
        ).all()
    )
    current = next((row for row in rows if row.call_key == call_key), None)
    if current is not None and current.status == "succeeded":
        return PersistedCallReservation(
            call_key=call_key,
            fence=current.activity_fence,
            status="succeeded",
            result_artifact_ref=current.result_artifact_ref,
        )
    if current is not None and current.status == "reserved" and current.lease_expires_at > now:
        raise PromptOptimizationError("optimization_call_in_flight")
    budget = dict(run.budget or {})
    if current is not None and current.status in {"reserved", "ambiguous"}:
        budget["ambiguous_calls"] = int(budget.get("ambiguous_calls", 0)) + 1
        budget["ambiguous_tokens"] = int(budget.get("ambiguous_tokens", 0)) + int(
            current.reserved_token_ceiling
        )
        budget["ambiguous_cost"] = str(
            Decimal(str(budget.get("ambiguous_cost", "0"))) + Decimal(current.reserved_cost_ceiling)
        )
    charged_calls = int(budget.get("ambiguous_calls", 0))
    charged_tokens = int(budget.get("ambiguous_tokens", 0))
    charged_cost = Decimal(str(budget.get("ambiguous_cost", "0")))
    for row in rows:
        if row is current or row.status not in {"reserved", "succeeded", "ambiguous"}:
            continue
        charged_calls += 1
        charged_tokens += (
            (row.actual_input_tokens or 0) + (row.actual_output_tokens or 0)
            if row.status == "succeeded"
            and row.actual_input_tokens is not None
            and row.actual_output_tokens is not None
            else row.reserved_token_ceiling
        )
        charged_cost += (
            Decimal(row.actual_cost)
            if row.status == "succeeded" and row.actual_cost is not None
            else Decimal(row.reserved_cost_ceiling)
        )
    if (
        charged_calls + 1 > int(budget["max_calls"])
        or charged_tokens + token_ceiling > int(budget["max_tokens"])
        or charged_cost + cost_ceiling > Decimal(str(budget["max_cost"]))
    ):
        raise PromptOptimizationError("optimization_budget_exhausted")
    fence = uuid4()
    if current is None:
        current = PromptOptimizationCallLedger(run_id=run_id, call_key=call_key)
        db.add(current)
    current.phase = phase
    current.prompt_version = prompt_version
    current.config_hash = config_hash
    current.model_route = model_route
    current.reserved_token_ceiling = token_ceiling
    current.reserved_cost_ceiling = str(cost_ceiling)
    current.status = "reserved"
    current.result_artifact_ref = None
    current.actual_input_tokens = None
    current.actual_output_tokens = None
    current.actual_cost = None
    current.activity_attempt = activity_attempt
    current.activity_fence = fence
    current.lease_expires_at = now + timedelta(seconds=lease_seconds)
    current.completed_at = None
    run.budget = budget
    run.status = "running"
    await db.flush()
    return PersistedCallReservation(call_key=call_key, fence=fence, status="reserved")


async def complete_persisted_call(
    db: Any,
    *,
    run_id: UUID,
    call_key: str,
    fence: UUID,
    result_artifact_ref: str,
    input_tokens: int | None,
    output_tokens: int | None,
    actual_cost: Decimal | None,
    now: datetime,
) -> None:
    from sqlalchemy import select

    from twobrain_rec_server.db.models import PromptOptimizationCallLedger

    row = await db.scalar(
        select(PromptOptimizationCallLedger)
        .where(
            PromptOptimizationCallLedger.run_id == run_id,
            PromptOptimizationCallLedger.call_key == call_key,
        )
        .with_for_update()
    )
    if row is None or row.status != "reserved" or row.activity_fence != fence:
        raise PromptOptimizationError("optimization_activity_fenced")
    expected_prefix = f"{CHECKPOINT_PREFIX}/{run_id}/calls/"
    if not result_artifact_ref.startswith(expected_prefix) or len(result_artifact_ref) > 500:
        raise PromptOptimizationError("optimization_result_artifact_invalid")
    row.status = "succeeded"
    row.result_artifact_ref = result_artifact_ref
    row.actual_input_tokens = input_tokens
    row.actual_output_tokens = output_tokens
    row.actual_cost = str(actual_cost) if actual_cost is not None else None
    row.completed_at = now
    await db.flush()


async def mark_persisted_call_ambiguous(
    db: Any,
    *,
    run_id: UUID,
    call_key: str,
    fence: UUID,
    now: datetime,
) -> None:
    from sqlalchemy import select

    from twobrain_rec_server.db.models import PromptOptimizationCallLedger

    row = await db.scalar(
        select(PromptOptimizationCallLedger)
        .where(
            PromptOptimizationCallLedger.run_id == run_id,
            PromptOptimizationCallLedger.call_key == call_key,
        )
        .with_for_update()
    )
    if row is None or row.status != "reserved" or row.activity_fence != fence:
        raise PromptOptimizationError("optimization_activity_fenced")
    row.status = "ambiguous"
    row.completed_at = now
    await db.flush()


async def advance_checkpoint_pointer(
    db: Any,
    *,
    run_id: UUID,
    revision: int,
    key: str,
    checksum: str,
) -> None:
    from sqlalchemy import select

    from twobrain_rec_server.db.models import PromptOptimizationRun

    run = await db.scalar(
        select(PromptOptimizationRun).where(PromptOptimizationRun.id == run_id).with_for_update()
    )
    expected_prefix = f"{CHECKPOINT_PREFIX}/{run_id}/checkpoints/"
    if (
        run is None
        or revision < 1
        or (run.checkpoint_revision is not None and revision <= run.checkpoint_revision)
        or not key.startswith(expected_prefix)
        or len(checksum) != 64
    ):
        raise PromptOptimizationError("checkpoint_pointer_conflict")
    run.run_artifact_ref = key
    run.checkpoint_revision = revision
    run.checkpoint_hash = checksum
    run.checkpoint_schema_version = CHECKPOINT_SCHEMA_VERSION
    await db.flush()


@dataclass(frozen=True, slots=True)
class ModelCall:
    request: object
    raw_response: object
    validated_result: object
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: Decimal | None = None
    actual_model: str | None = None
    actual_provider: str | None = None
    token_usage: Mapping[str, object] | None = None
    cost_details: Mapping[str, object] | None = None


class OptimizationModelExecutor(Protocol):
    def __call__(
        self,
        *,
        phase: str,
        snapshot: PromptSnapshot,
        prompt_text: str,
        variables: Mapping[str, str],
    ) -> ModelCall: ...


class ObservationSink(Protocol):
    def __call__(
        self,
        *,
        phase: str,
        call_key: str,
        snapshot: PromptSnapshot,
        request: object,
        raw_response: object,
        validated_result: object,
        actual_model: str | None,
        actual_provider: str | None,
        token_usage: Mapping[str, object] | None,
        cost_details: Mapping[str, object] | None,
    ) -> None: ...


@dataclass(frozen=True, slots=True)
class PinnedOptimizationContract:
    source: PromptSnapshot
    reflection: PromptSnapshot
    judges: Mapping[str, PromptSnapshot]

    def __post_init__(self) -> None:
        if self.source.prompt_type != "chat" or not self.source.name.startswith(
            "graf/meeting-outcome/"
        ):
            raise ValueError("optimizer source prompt is invalid")
        if self.reflection.name != "graf/prompt-optimization/reflection":
            raise ValueError("optimizer reflection prompt is invalid")
        if set(self.judges) != set(JUDGE_NAMES):
            raise ValueError("optimizer must pin all three judges")


@dataclass(frozen=True, slots=True)
class JudgeCalibration:
    prompt_name: str
    valid_rows: int
    invalid_rows: int
    agreements: int
    threshold: float
    operator_approved: bool

    @property
    def agreement(self) -> float | None:
        return self.agreements / self.valid_rows if self.valid_rows else None

    @property
    def passed(self) -> bool:
        value = self.agreement
        return (
            value is not None
            and value >= self.threshold
            and self.invalid_rows == 0
            and self.operator_approved
        )


def calibrate_judge(
    *,
    prompt_name: str,
    expected: Sequence[str],
    actual: Sequence[str],
    threshold: float,
    operator_approved: bool,
) -> JudgeCalibration:
    if prompt_name not in JUDGE_NAMES or len(expected) != len(actual) or not 0 <= threshold <= 1:
        raise ValueError("judge calibration input is invalid")
    allowed = {"pass", "fail"}
    normalized = [
        (left.strip().lower(), right.strip().lower())
        for left, right in zip(expected, actual, strict=True)
    ]
    valid = [(left, right) for left, right in normalized if left in allowed and right in allowed]
    return JudgeCalibration(
        prompt_name=prompt_name,
        valid_rows=len(valid),
        invalid_rows=len(normalized) - len(valid),
        agreements=sum(left == right for left, right in valid),
        threshold=threshold,
        operator_approved=operator_approved,
    )


def required_control_prompt_gate(
    snapshot: PromptSnapshot,
    *,
    expected_gate: Literal["judge", "reflection"],
) -> dict[str, object]:
    gate = snapshot.config.get(CONTROL_GATE_CONFIG_KEY)
    if not isinstance(gate, Mapping) or gate.get("gate") != expected_gate:
        raise PromptOptimizationError("control_prompt_gate_missing")
    return dict(gate)


def required_judge_calibration(snapshot: PromptSnapshot) -> tuple[JudgeCalibration, dict[str, object]]:
    if snapshot.name not in JUDGE_NAMES:
        raise PromptOptimizationError("judge_calibration_gate_missing")
    gate = required_control_prompt_gate(snapshot, expected_gate="judge")
    valid_rows = int(gate["valid_rows"])
    agreement = float(gate["agreement"])
    calibration = JudgeCalibration(
        prompt_name=snapshot.name,
        valid_rows=valid_rows,
        invalid_rows=0,
        agreements=round(agreement * valid_rows),
        threshold=float(gate["agreement_threshold"]),
        operator_approved=gate.get("operator_approved") is True,
    )
    if not calibration.passed:
        raise PromptOptimizationError("judge_calibration_gate_failed")
    return calibration, dict(gate)


@dataclass(frozen=True, slots=True)
class OptimizationTrajectory:
    example_id: str
    transcript_json: str
    output: object
    feedback: tuple[str, ...]
    score: float
    forbidden_copy_fragments: tuple[str, ...] = ()


class DurableCheckpointCallback:
    """Publish the GEPA state file after each library-owned state-save boundary."""

    def __init__(self, persist: Callable[[str, int], None]) -> None:
        self._persist = persist

    def on_state_saved(self, event: Mapping[str, object]) -> None:
        run_dir = event.get("run_dir")
        iteration = event.get("iteration")
        if not isinstance(run_dir, str) or not isinstance(iteration, int):
            raise PromptOptimizationError("checkpoint_state_missing")
        self._persist(run_dir, iteration)


class _SilentGEPALogger:
    def log(self, _message: str) -> None:
        # Raw candidates belong only in the checkpoint and explicit call observations.
        return


class PromptOptimizationAdapter:
    """Thin GEPA 0.1.4 adapter over GRAF's pinned model/validation path."""

    def __init__(
        self,
        *,
        run_id: UUID,
        contract: PinnedOptimizationContract,
        ledger: FencedCallLedger,
        executor: OptimizationModelExecutor,
        observer: ObservationSink,
        budget: OptimizationBudget,
        calibrations: Mapping[str, JudgeCalibration],
        activity_attempt: int = 1,
        now: Callable[[], datetime] = lambda: datetime.now(UTC),
        cancelled: Callable[[], bool] = lambda: False,
    ) -> None:
        if set(calibrations) != set(JUDGE_NAMES) or not all(
            item.passed for item in calibrations.values()
        ):
            raise PromptOptimizationError("judge_calibration_gate_failed")
        self.run_id = run_id
        self.contract = contract
        self.ledger = ledger
        self.executor = executor
        self.observer = observer
        self.budget = budget
        self.activity_attempt = activity_attempt
        self._now = now
        self._cancelled = cancelled
        self._call_sequence = 0

    def evaluate(
        self,
        batch: list[SyntheticExample],
        candidate: dict[str, str],
        capture_traces: bool = False,
    ) -> Any:
        from gepa.core.adapter import EvaluationBatch

        prompt_text = _single_candidate(candidate)
        validate_candidate_prompt(self.contract.source, prompt_text)
        outputs: list[object] = []
        scores: list[float] = []
        trajectories: list[OptimizationTrajectory] | None = [] if capture_traces else None
        for example in batch:
            _, validated = self._call_with_validation_retry(
                phase="task",
                snapshot=self.contract.source,
                prompt_text=prompt_text,
                variables=task_model_variables(example.transcript_json),
                example_id=example.id,
                validator=lambda value,
                allowed_categories=example.required_categories,
                allowed_segment_ids=frozenset(example.segment_ids): validate_outcome_result(
                    value,
                    allowed_categories=allowed_categories,
                    allowed_segment_ids=set(allowed_segment_ids),
                ),
            )
            judge_scores: list[float] = []
            feedback: list[str] = []
            for judge_name, phase in zip(
                JUDGE_NAMES,
                CALL_PHASES[2:],
                strict=True,
            ):
                variables = {
                    "source_segments_json": example.transcript_json,
                    "candidate_outcome_json": canonical_json(validated),
                }
                if judge_name.endswith("completeness"):
                    variables["required_categories_json"] = canonical_json(
                        list(example.required_categories)
                    )
                _, judge_result = self._call_with_validation_retry(
                    phase=phase,
                    snapshot=self.contract.judges[judge_name],
                    prompt_text="",
                    variables=variables,
                    example_id=example.id,
                    validator=validate_judge_result,
                )
                judge_scores.append(float(judge_result["score"]))
                feedback.append(str(judge_result["feedback"]))
            score = min(judge_scores)
            outputs.append(validated)
            scores.append(score)
            if trajectories is not None:
                trajectories.append(
                    OptimizationTrajectory(
                        example_id=example.id,
                        transcript_json=example.transcript_json,
                        output=validated,
                        feedback=tuple(feedback),
                        score=score,
                        forbidden_copy_fragments=example.forbidden_copy_fragments,
                    )
                )
        return EvaluationBatch(
            outputs=outputs,
            scores=scores,
            trajectories=trajectories,
            objective_scores=None,
            num_metric_calls=len(batch) * 4,
        )

    def _call_with_validation_retry(
        self,
        *,
        phase: str,
        snapshot: PromptSnapshot,
        prompt_text: str,
        variables: Mapping[str, str],
        example_id: str,
        validator: Callable[[object], Any],
    ) -> tuple[ModelCall, Any]:
        """Retry one provider result when the closed semantic contract rejects it.

        LiteLLM deliberately does not replay provider calls. A malformed structured
        result is still retained in the ledger for debugging, then one bounded
        validation retry uses a distinct idempotency key so the second response is
        independently observable and budgeted.
        """

        for attempt in range(2):
            call = self._call(
                phase=phase,
                snapshot=snapshot,
                prompt_text=prompt_text,
                variables=variables,
                example_id=(
                    example_id
                    if attempt == 0
                    else f"{example_id}:validation-retry-{attempt}"
                ),
            )
            try:
                return call, validator(call.validated_result)
            except (ValueError, PromptOptimizationError):
                if attempt == 1:
                    raise
        raise AssertionError("validation retry loop exhausted")

    def make_reflective_dataset(
        self,
        candidate: dict[str, str],
        eval_batch: Any,
        components_to_update: list[str],
    ) -> Mapping[str, Sequence[Mapping[str, Any]]]:
        if components_to_update != [PROMPT_COMPONENT] or eval_batch.trajectories is None:
            raise PromptOptimizationError("reflection_component_invalid")
        return {
            PROMPT_COMPONENT: [
                {
                    "Inputs": {"transcript_json": item.transcript_json},
                    "Generated Outputs": item.output,
                    "Feedback": "\n".join(item.feedback),
                    "Forbidden Copy Fragments": list(item.forbidden_copy_fragments),
                    "score": item.score,
                }
                for item in eval_batch.trajectories
            ]
        }

    def propose_new_texts(
        self,
        candidate: dict[str, str],
        reflective_dataset: Mapping[str, Sequence[Mapping[str, Any]]],
        components_to_update: list[str],
    ) -> dict[str, str]:
        current = _single_candidate(candidate)
        if components_to_update != [PROMPT_COMPONENT]:
            raise PromptOptimizationError("reflection_component_invalid")
        call = self._call(
            phase="reflection",
            snapshot=self.contract.reflection,
            prompt_text=current,
            variables={
                "curr_param": current,
                "side_info": canonical_json(reflective_dataset[PROMPT_COMPONENT]),
            },
            example_id=f"reflection-{self._call_sequence + 1}",
        )
        proposal = parse_reflection_proposal(str(call.validated_result))
        validate_candidate_prompt(
            self.contract.source,
            proposal,
            forbidden_fragments={
                fragment
                for item in reflective_dataset[PROMPT_COMPONENT]
                for fragment in item.get("Forbidden Copy Fragments", [])
                if isinstance(fragment, str)
            },
        )
        return {PROMPT_COMPONENT: proposal}

    def _call(
        self,
        *,
        phase: str,
        snapshot: PromptSnapshot,
        prompt_text: str,
        variables: Mapping[str, str],
        example_id: str,
    ) -> ModelCall:
        now = self._now()
        self._check_budget(now)
        self._call_sequence += 1
        call_key = optimization_call_key(
            run_id=self.run_id,
            phase=phase,
            example_id=example_id,
            candidate_text=prompt_text,
            variables=variables,
            snapshot=snapshot,
        )
        max_tokens = int(snapshot.config["max_completion_tokens"])
        reservation = self.ledger.reserve(
            call_key=call_key,
            phase=phase,
            activity_attempt=self.activity_attempt,
            now=now,
            token_ceiling=max_tokens,
            # Reserve a conservative equal share per possible call. Reserving the
            # entire run ceiling for each call would make every second call fail.
            cost_ceiling=self.budget.max_cost / self.budget.max_calls,
        )
        if reservation.status == "succeeded":
            if not isinstance(reservation.result, ModelCall):
                raise PromptOptimizationError("optimization_ledger_result_invalid")
            self.observer(
                phase=phase,
                call_key=call_key,
                snapshot=snapshot,
                request=reservation.result.request,
                raw_response=reservation.result.raw_response,
                validated_result=reservation.result.validated_result,
                actual_model=reservation.result.actual_model,
                actual_provider=reservation.result.actual_provider,
                token_usage=reservation.result.token_usage,
                cost_details=reservation.result.cost_details,
            )
            return reservation.result
        try:
            result = self.executor(
                phase=phase,
                snapshot=snapshot,
                prompt_text=prompt_text,
                variables=variables,
            )
            # Provider calls are bounded but not interruptible. Never publish a
            # result returned after the cooperative cancellation signal.
            if self._cancelled():
                raise PromptOptimizationError("optimization_cancelled")
            tokens = (
                result.input_tokens + result.output_tokens
                if result.input_tokens is not None and result.output_tokens is not None
                else None
            )
            self.ledger.succeed(
                call_key=call_key,
                fence=reservation.fence,
                result=result,
                actual_tokens=tokens,
                actual_cost=result.cost,
            )
        except Exception:
            self.ledger.fail(call_key=call_key, fence=reservation.fence)
            raise
        self.observer(
            phase=phase,
            call_key=call_key,
            snapshot=snapshot,
            request=result.request,
            raw_response=result.raw_response,
            validated_result=result.validated_result,
            actual_model=result.actual_model,
            actual_provider=result.actual_provider,
            token_usage=result.token_usage,
            cost_details=result.cost_details,
        )
        return result

    def _check_budget(self, now: datetime) -> None:
        if self._cancelled():
            raise PromptOptimizationError("optimization_cancelled")
        if now >= self.budget.deadline_at:
            raise PromptOptimizationError("optimization_deadline_exceeded")
        calls, tokens, cost = self.ledger.charged_totals()
        if (
            calls >= self.budget.max_calls
            or tokens >= self.budget.max_tokens
            or cost >= self.budget.max_cost
        ):
            raise PromptOptimizationError("optimization_budget_exhausted")


@dataclass(frozen=True, slots=True)
class OptimizationCandidate:
    prompt_text: str
    prompt_hash: str
    source_config_hash: str
    development_score: float
    heldout_scores: Mapping[str, float] = field(default_factory=dict)
    hard_gates_passed: bool = False
    promoted: bool = False


def run_gepa_optimization(
    *,
    adapter: PromptOptimizationAdapter,
    source_prompt_text: str,
    train: SyntheticManifest,
    development: SyntheticManifest,
    run_dir: str,
    max_metric_calls: int,
    callbacks: Sequence[object] = (),
) -> OptimizationCandidate:
    import gepa

    if max_metric_calls < 1:
        raise ValueError("max_metric_calls must be positive")
    result = gepa.optimize(
        seed_candidate={PROMPT_COMPONENT: source_prompt_text},
        trainset=list(train.examples),
        valset=list(development.examples),
        adapter=adapter,
        max_metric_calls=max_metric_calls,
        run_dir=run_dir,
        logger=_SilentGEPALogger(),
        callbacks=list(callbacks),
        cache_evaluation=False,
        display_progress_bar=False,
        raise_on_exception=True,
        seed=0,
    )
    candidate = result.best_candidate
    text = _single_candidate(candidate)
    validate_candidate_prompt(adapter.contract.source, text)
    return OptimizationCandidate(
        prompt_text=text,
        prompt_hash=sha256(text.encode("utf-8")).hexdigest(),
        source_config_hash=prompt_config_hash(adapter.contract.source.config),
        development_score=float(result.val_aggregate_scores[result.best_idx]),
    )


def validate_heldout_candidate(
    *,
    adapter: PromptOptimizationAdapter,
    candidate: OptimizationCandidate,
    heldout: SyntheticManifest,
    minimum_metric_score: float,
) -> OptimizationCandidate:
    heldout.verify()
    evaluation = adapter.evaluate(
        list(heldout.examples),
        {PROMPT_COMPONENT: candidate.prompt_text},
        capture_traces=False,
    )
    score = sum(evaluation.scores) / len(evaluation.scores)
    passed = score >= minimum_metric_score
    return OptimizationCandidate(
        prompt_text=candidate.prompt_text,
        prompt_hash=candidate.prompt_hash,
        source_config_hash=candidate.source_config_hash,
        development_score=candidate.development_score,
        heldout_scores={"minimum_judge_score": score},
        hard_gates_passed=passed,
        promoted=False,
    )


def validate_candidate_prompt(
    source: PromptSnapshot,
    prompt_text: str,
    *,
    forbidden_fragments: Sequence[str] = (),
) -> PromptSnapshot:
    if not prompt_text.strip() or len(prompt_text.encode("utf-8")) > 65_536:
        raise PromptOptimizationError("candidate_prompt_invalid")
    source_text = canonical_json(source.prompt)
    try:
        source_variables = set(prompt_variables(source_text))
        candidate_variables = set(prompt_variables(prompt_text))
    except ValueError as exc:
        raise PromptOptimizationError("candidate_variables_changed") from exc
    if candidate_variables != source_variables:
        raise PromptOptimizationError("candidate_variables_changed")
    if any(marker in prompt_text.lower() for marker in ("api_key", "authorization:", "sk-lf-")):
        raise PromptOptimizationError("candidate_privacy_gate_failed")
    if any(fragment.casefold() in prompt_text.casefold() for fragment in forbidden_fragments):
        raise PromptOptimizationError("candidate_anti_copy_gate_failed")
    # Candidate text is the complete chat prompt JSON so the existing closed validator remains authoritative.
    try:
        parsed = json.loads(prompt_text)
    except json.JSONDecodeError as exc:
        raise PromptOptimizationError("candidate_prompt_invalid") from exc
    return validate_prompt_snapshot(
        name=source.name,
        version=source.version,
        prompt_type=source.prompt_type,
        prompt=parsed,
        config=source.config,
        source=source.source,
    )


def parse_reflection_proposal(value: str) -> str:
    if not value.startswith("```") or not value.endswith("```") or value.count("```") != 2:
        raise PromptOptimizationError("reflection_proposal_invalid")
    proposal = value[3:-3]
    if not proposal or proposal.startswith("\n") or proposal.endswith("\n"):
        raise PromptOptimizationError("reflection_proposal_invalid")
    return proposal


def validate_judge_result(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != {"score", "verdict", "feedback"}:
        raise PromptOptimizationError("judge_result_invalid")
    score = value["score"]
    verdict = value["verdict"]
    feedback = value["feedback"]
    if isinstance(score, bool) or not isinstance(score, (int, float)) or not 0 <= score <= 1:
        raise PromptOptimizationError("judge_result_invalid")
    if verdict not in {"pass", "fail"} or not isinstance(feedback, str) or len(feedback) > 4000:
        raise PromptOptimizationError("judge_result_invalid")
    if (verdict == "pass") != (score >= 0.5):
        raise PromptOptimizationError("judge_verdict_inconsistent")
    return {"score": float(score), "verdict": verdict, "feedback": feedback}


def optimization_call_key(
    *,
    run_id: UUID,
    phase: str,
    example_id: str,
    candidate_text: str,
    variables: Mapping[str, str],
    snapshot: PromptSnapshot,
) -> str:
    if phase not in CALL_PHASES:
        raise ValueError("optimization phase is invalid")
    payload = {
        "candidate_hash": sha256(candidate_text.encode("utf-8")).hexdigest(),
        "config_hash": prompt_config_hash(snapshot.config),
        "example_id": example_id,
        "phase": phase,
        "prompt_name": snapshot.name,
        "prompt_version": snapshot.version,
        "run_id": str(run_id),
        "variables_hash": sha256(canonical_json(dict(variables)).encode("utf-8")).hexdigest(),
    }
    return sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def task_model_variables(transcript_json: str) -> dict[str, str]:
    return {
        "transcript_json": transcript_json,
        "output_language": "ru",
        "detail_level": "standard",
        "template_sections_json": canonical_json(list(OUTCOME_CATEGORIES)),
    }


def checkpoint_key(run_id: UUID, revision: int) -> str:
    if revision < 1:
        raise ValueError("checkpoint revision must be positive")
    return f"{CHECKPOINT_PREFIX}/{run_id}/checkpoints/{revision:08d}.json"


def pack_gepa_checkpoint(
    *,
    run_id: UUID,
    revision: int,
    run_dir: str | Path,
    manifest_hashes: Mapping[str, str],
) -> tuple[str, bytes, str]:
    directory = Path(run_dir)
    state_path = directory / "gepa_state.bin"
    if not state_path.exists():
        raise PromptOptimizationError("checkpoint_state_missing")
    metadata = {
        "adapter_version": ADAPTER_VERSION,
        "manifest_hashes": dict(manifest_hashes),
        "optimizer_version": OPTIMIZER_VERSION,
        "run_id": str(run_id),
        "schema_version": CHECKPOINT_SCHEMA_VERSION,
    }
    buffer = BytesIO()
    with ZipFile(buffer, "w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("checkpoint.json", canonical_json(metadata))
        for name in sorted(GEPA_CHECKPOINT_FILES):
            path = directory / name
            if not path.exists():
                continue
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_CHECKPOINT_BYTES:
                raise PromptOptimizationError("checkpoint_file_invalid")
            archive.writestr(name, path.read_bytes())
    payload = buffer.getvalue()
    if len(payload) > MAX_CHECKPOINT_BYTES:
        raise PromptOptimizationError("checkpoint_too_large")
    return (
        checkpoint_key(run_id, revision).removesuffix(".json") + ".zip",
        payload,
        sha256(payload).hexdigest(),
    )


def restore_gepa_checkpoint(
    *,
    run_id: UUID,
    key: str,
    payload: bytes,
    expected_hash: str,
    manifest_hashes: Mapping[str, str],
    run_dir: str | Path,
) -> None:
    prefix = f"{CHECKPOINT_PREFIX}/{run_id}/checkpoints/"
    if (
        not key.startswith(prefix)
        or not key.endswith(".zip")
        or len(payload) > MAX_CHECKPOINT_BYTES
        or sha256(payload).hexdigest() != expected_hash
    ):
        raise PromptOptimizationError("checkpoint_integrity_failed")
    destination = Path(run_dir)
    destination.mkdir(parents=True, exist_ok=True)
    if any(destination.iterdir()):
        raise PromptOptimizationError("checkpoint_restore_directory_not_empty")
    with ZipFile(BytesIO(payload), "r") as archive:
        names = set(archive.namelist())
        if "checkpoint.json" not in names or not names <= GEPA_CHECKPOINT_FILES | {
            "checkpoint.json"
        }:
            raise PromptOptimizationError("checkpoint_archive_invalid")
        if sum(item.file_size for item in archive.infolist()) > MAX_CHECKPOINT_BYTES:
            raise PromptOptimizationError("checkpoint_too_large")
        metadata = json.loads(archive.read("checkpoint.json"))
        if metadata != {
            "adapter_version": ADAPTER_VERSION,
            "manifest_hashes": dict(manifest_hashes),
            "optimizer_version": OPTIMIZER_VERSION,
            "run_id": str(run_id),
            "schema_version": CHECKPOINT_SCHEMA_VERSION,
        }:
            raise PromptOptimizationError("checkpoint_contract_mismatch")
        if "gepa_state.bin" not in names:
            raise PromptOptimizationError("checkpoint_state_missing")
        for name in sorted(names - {"checkpoint.json"}):
            target = destination / name
            descriptor = os.open(
                target,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
            )
            try:
                view = memoryview(archive.read(name))
                while view:
                    view = view[os.write(descriptor, view) :]
                os.fsync(descriptor)
            finally:
                os.close(descriptor)


def prompt_config_hash(config: Mapping[str, object]) -> str:
    return sha256(canonical_json(config).encode("utf-8")).hexdigest()


def publish_unlabelled_candidate(
    client: Any,
    *,
    source: PromptSnapshot,
    candidate_prompt: object,
    idempotency_tag: str | None = None,
) -> PromptSnapshot:
    tags = ["graf", "recording-workflows", "gepa-0.1.4"]
    if idempotency_tag is not None:
        tags.append(idempotency_tag)
    created = client.create_prompt(
        name=source.name,
        prompt=langfuse_prompt_payload(candidate_prompt),
        labels=[],
        tags=tags,
        type=source.prompt_type,
        config=source.config,
        commit_message="GEPA 0.1.4 synthetic candidate; requires operator approval",
    )
    fetched = client.get_prompt(
        source.name,
        version=int(created.version),
        type=source.prompt_type,
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    snapshot = validate_prompt_snapshot(
        name=source.name,
        version=int(fetched.version),
        prompt_type=source.prompt_type,
        prompt=fetched.prompt,
        config=fetched.config or {},
    )
    if snapshot.config != source.config or snapshot.prompt != candidate_prompt:
        raise PromptOptimizationError("candidate_readback_mismatch")
    if "production" in set(getattr(fetched, "labels", ())):
        raise PromptOptimizationError("candidate_was_auto_promoted")
    return snapshot


def publish_or_recover_unlabelled_candidate(
    client: Any,
    *,
    source: PromptSnapshot,
    candidate_prompt: object,
    idempotency_tag: str,
) -> PromptSnapshot:
    """Recover a Langfuse create that succeeded before the DB commit was lost."""

    listed = client.api.prompts.list(
        name=source.name,
        tag=idempotency_tag,
        page=1,
        limit=100,
    )
    recovered: list[PromptSnapshot] = []
    tagged_version_seen = False
    for item in listed.data:
        if str(item.name) != source.name:
            continue
        for version in item.versions:
            tagged_version_seen = True
            fetched = client.get_prompt(
                source.name,
                version=int(version),
                type=source.prompt_type,
                cache_ttl_seconds=0,
                max_retries=0,
                fetch_timeout_seconds=10,
            )
            snapshot = validate_prompt_snapshot(
                name=source.name,
                version=int(fetched.version),
                prompt_type=source.prompt_type,
                prompt=fetched.prompt,
                config=fetched.config or {},
            )
            if (
                "production" not in set(getattr(fetched, "labels", ()))
                and snapshot.prompt == candidate_prompt
                and snapshot.config == source.config
            ):
                recovered.append(snapshot)
    if len(recovered) > 1:
        raise PromptOptimizationError("candidate_idempotency_conflict")
    if recovered:
        return recovered[0]
    if tagged_version_seen:
        raise PromptOptimizationError("candidate_idempotency_conflict")
    return publish_unlabelled_candidate(
        client,
        source=source,
        candidate_prompt=candidate_prompt,
        idempotency_tag=idempotency_tag,
    )


def load_persisted_candidate_result(
    client: Any,
    *,
    source: PromptSnapshot,
    candidate_prompt: object,
    candidate_version: int,
    candidate_hash: str,
    candidate_config_hash: str,
) -> PromptSnapshot:
    """Rebuild an activity result after its completion was lost."""

    fetched = client.get_prompt(
        source.name,
        version=candidate_version,
        type=source.prompt_type,
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    snapshot = validate_prompt_snapshot(
        name=source.name,
        version=int(fetched.version),
        prompt_type=source.prompt_type,
        prompt=fetched.prompt,
        config=fetched.config or {},
    )
    if (
        "production" in set(getattr(fetched, "labels", ()))
        or snapshot.prompt != candidate_prompt
        or snapshot.config != source.config
        or snapshot.canonical_hash != candidate_hash
        or prompt_config_hash(snapshot.config) != candidate_config_hash
    ):
        raise PromptOptimizationError("candidate_persisted_result_mismatch")
    return snapshot


def validate_control_prompt_gate(
    *,
    candidate: PromptSnapshot,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    """Validate operator-supplied offline evidence without exporting calibration content."""
    common_keys = {"evaluator_version", "operator_actor_id", "operator_approved"}
    if not isinstance(evidence.get("evaluator_version"), str) or not re.fullmatch(
        r"[A-Za-z0-9._-]{1,64}", str(evidence["evaluator_version"])
    ):
        raise PromptOptimizationError("control_prompt_evaluator_version_invalid")
    if not isinstance(evidence.get("operator_actor_id"), str) or not str(
        evidence["operator_actor_id"]
    ).strip():
        raise PromptOptimizationError("control_prompt_operator_invalid")
    if evidence.get("operator_approved") is not True:
        raise PromptOptimizationError("control_prompt_operator_approval_required")
    if candidate.name == "graf/prompt-optimization/reflection":
        required = common_keys | {
            "native_parser_smoke_passed",
            "variable_preservation_passed",
            "anti_copy_regression_passed",
            "bounded_cost_smoke_passed",
        }
        if set(evidence) != required or not all(
            evidence.get(name) is True for name in required - common_keys
        ):
            raise PromptOptimizationError("reflection_control_prompt_gate_failed")
        return {
            "evaluator_version": evidence["evaluator_version"],
            "gate": "reflection",
            "operator_actor_id": evidence["operator_actor_id"],
            "passed": True,
        }
    if candidate.name not in JUDGE_NAMES:
        raise PromptOptimizationError("control_prompt_name_invalid")
    required = common_keys | {
        "calibration_manifest_hash",
        "expected_labels",
        "actual_labels",
        "agreement_threshold",
        "invalid_output_count",
        "bounded_cost_smoke_passed",
    }
    if set(evidence) != required:
        raise PromptOptimizationError("judge_control_prompt_gate_failed")
    manifest_hash = evidence["calibration_manifest_hash"]
    expected = evidence["expected_labels"]
    actual = evidence["actual_labels"]
    threshold = evidence["agreement_threshold"]
    invalid_outputs = evidence["invalid_output_count"]
    if (
        not isinstance(manifest_hash, str)
        or not re.fullmatch(r"[0-9a-f]{64}", manifest_hash)
        or not isinstance(expected, list)
        or not isinstance(actual, list)
        or len(expected) < 10
        or not isinstance(threshold, (int, float))
        or isinstance(threshold, bool)
        or float(threshold) < 0.9
        or not isinstance(invalid_outputs, int)
        or isinstance(invalid_outputs, bool)
        or invalid_outputs != 0
        or evidence["bounded_cost_smoke_passed"] is not True
    ):
        raise PromptOptimizationError("judge_control_prompt_gate_failed")
    calibration = calibrate_judge(
        prompt_name=candidate.name,
        expected=[str(value) for value in expected],
        actual=[str(value) for value in actual],
        threshold=float(threshold),
        operator_approved=True,
    )
    if not calibration.passed:
        raise PromptOptimizationError("judge_control_prompt_gate_failed")
    return {
        "agreement": calibration.agreement,
        "agreement_threshold": float(threshold),
        "calibration_manifest_hash": manifest_hash,
        "evaluator_version": evidence["evaluator_version"],
        "gate": "judge",
        "operator_actor_id": evidence["operator_actor_id"],
        "passed": True,
        "valid_rows": calibration.valid_rows,
    }


def control_gate_evidence_hash(evidence: Mapping[str, object]) -> str:
    return sha256(canonical_json(evidence).encode("utf-8")).hexdigest()


def promote_control_prompt(
    client: Any,
    *,
    prompt_name: str,
    prompt_type: Literal["chat", "text"],
    candidate_version: int,
    expected_source_version: int | None,
    evidence: Mapping[str, object],
    protected_label_capability_verified: bool,
    snapshot_storage: Any | None = None,
) -> tuple[PromptSnapshot, dict[str, object]]:
    fetched = client.get_prompt(
        prompt_name,
        version=candidate_version,
        type=prompt_type,
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    candidate = validate_prompt_snapshot(
        name=prompt_name,
        version=int(fetched.version),
        prompt_type=prompt_type,
        prompt=fetched.prompt,
        config=fetched.config or {},
    )
    aggregate = validate_control_prompt_gate(candidate=candidate, evidence=evidence)
    evidence_hash = control_gate_evidence_hash(evidence)
    gated_config = dict(candidate.config)
    gated_config[CONTROL_GATE_CONFIG_KEY] = {
        **aggregate,
        "evidence_hash": evidence_hash,
        "gate_version": 1,
        "operator_approved": True,
    }
    gated = client.create_prompt(
        name=prompt_name,
        prompt=langfuse_prompt_payload(candidate.prompt),
        labels=[],
        tags=["graf", "recording-workflows", "control-gate-v1"],
        type=prompt_type,
        config=gated_config,
        commit_message=(
            f"Validated control gate for candidate v{candidate_version}; "
            f"evidence {evidence_hash}"
        ),
    )
    promoted = move_production_label(
        client,
        prompt_name=prompt_name,
        prompt_type=prompt_type,
        expected_source_version=expected_source_version,
        target_version=int(gated.version),
        protected_label_capability_verified=protected_label_capability_verified,
        snapshot_storage=snapshot_storage,
    )
    if (
        promoted.prompt != candidate.prompt
        or promoted.config.get(CONTROL_GATE_CONFIG_KEY) != gated_config[CONTROL_GATE_CONFIG_KEY]
    ):
        raise PromptOptimizationError("control_prompt_promotion_postverify_failed")
    return promoted, aggregate


def move_production_label(
    client: Any,
    *,
    prompt_name: str,
    prompt_type: Literal["chat", "text"],
    expected_source_version: int | None,
    target_version: int,
    protected_label_capability_verified: bool,
    snapshot_storage: Any | None = None,
) -> PromptSnapshot:
    if not protected_label_capability_verified:
        raise PromptOptimizationError("protected_label_capability_unavailable")
    try:
        current = client.get_prompt(
            prompt_name,
            label="production",
            type=prompt_type,
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
    except Exception as exc:
        from langfuse.api.commons.errors.not_found_error import NotFoundError

        if expected_source_version is not None or not isinstance(exc, NotFoundError):
            raise
        current = None
    target = client.get_prompt(
        prompt_name,
        version=target_version,
        type=prompt_type,
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    target_snapshot = validate_prompt_snapshot(
        name=prompt_name,
        version=int(target.version),
        prompt_type=prompt_type,
        prompt=target.prompt,
        config=target.config or {},
    )
    current_version = int(current.version) if current is not None else None
    if current_version not in {expected_source_version, target_version}:
        raise PromptOptimizationError("production_source_conflict")
    try:
        # The target state is an idempotent retry after a label mutation
        # succeeded but post-verification, snapshot export, or the Activity
        # completion was lost.
        if current_version != target_version:
            client.update_prompt(
                name=prompt_name,
                version=target_version,
                new_labels=["production"],
            )
        client.clear_prompt_cache()
        verified = client.get_prompt(
            prompt_name,
            label="production",
            type=prompt_type,
            cache_ttl_seconds=0,
            max_retries=0,
            fetch_timeout_seconds=10,
        )
        if int(verified.version) != target_version:
            raise ValueError("production label does not point at the target")
        snapshot = validate_prompt_snapshot(
            name=prompt_name,
            version=int(verified.version),
            prompt_type=prompt_type,
            prompt=verified.prompt,
            config=verified.config or {},
        )
        if (
            snapshot.prompt != target_snapshot.prompt
            or snapshot.config != target_snapshot.config
        ):
            raise ValueError("production target content changed")
        if snapshot_storage is not None:
            persist_verified_promoted_snapshot(snapshot_storage, snapshot)
        return snapshot
    except Exception as exc:
        raise PromptOptimizationReconciliationError(
            "production_label_reconciliation_required"
        ) from exc


def promoted_snapshot_object_key(prompt_name: str) -> str:
    digest = sha256(prompt_name.encode("utf-8")).hexdigest()
    return f"_system/prompts/verified-production/{digest}.json"


def build_verified_promoted_snapshot(snapshot: PromptSnapshot) -> tuple[str, bytes, str]:
    payload = {
        "canonical_hash": snapshot.canonical_hash,
        "config": snapshot.config,
        "name": snapshot.name,
        "prompt": snapshot.prompt,
        "prompt_type": snapshot.prompt_type,
        "schema_version": "graf-verified-prompt-v1",
        "version": snapshot.version,
    }
    encoded = canonical_json(payload).encode("utf-8")
    return promoted_snapshot_object_key(snapshot.name), encoded, sha256(encoded).hexdigest()


def persist_verified_promoted_snapshot(storage: Any, snapshot: PromptSnapshot) -> str:
    key, payload, _ = build_verified_promoted_snapshot(snapshot)
    storage.put_stream(key, BytesIO(payload), len(payload))
    verified = load_verified_promoted_snapshot(storage, prompt_name=snapshot.name)
    if verified.canonical_hash != snapshot.canonical_hash or verified.version != snapshot.version:
        raise PromptOptimizationError("promoted_snapshot_export_postverify_failed")
    return key


def load_verified_promoted_snapshot(storage: Any, *, prompt_name: str) -> PromptSnapshot:
    key = promoted_snapshot_object_key(prompt_name)
    payload = storage.get_bytes(key)
    if len(payload) > 131_072:
        raise PromptOptimizationError("promoted_snapshot_export_invalid")
    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptOptimizationError("promoted_snapshot_export_invalid") from exc
    if (
        not isinstance(data, dict)
        or set(data)
        != {
            "canonical_hash",
            "config",
            "name",
            "prompt",
            "prompt_type",
            "schema_version",
            "version",
        }
        or data["schema_version"] != "graf-verified-prompt-v1"
        or data["name"] != prompt_name
    ):
        raise PromptOptimizationError("promoted_snapshot_export_invalid")
    snapshot = validate_prompt_snapshot(
        name=prompt_name,
        version=data["version"],
        prompt_type=data["prompt_type"],
        prompt=data["prompt"],
        config=data["config"],
        source="verified_promoted_snapshot",
    )
    if snapshot.canonical_hash != data["canonical_hash"]:
        raise PromptOptimizationError("promoted_snapshot_export_hash_mismatch")
    return snapshot


def _single_candidate(candidate: Mapping[str, str] | str) -> str:
    if isinstance(candidate, str):
        return candidate
    if set(candidate) != {PROMPT_COMPONENT} or not isinstance(candidate[PROMPT_COMPONENT], str):
        raise PromptOptimizationError("optimizer_candidate_invalid")
    return candidate[PROMPT_COMPONENT]


def _manifest_payload(
    *,
    split: str,
    version: str,
    examples: Sequence[SyntheticExample],
) -> bytes:
    return canonical_json(
        {
            "examples": [
                {
                    "forbidden_copy_fragments": list(item.forbidden_copy_fragments),
                    "human_labels": dict(item.human_labels),
                    "id": item.id,
                    "required_categories": list(item.required_categories),
                    "segment_ids": sorted(item.segment_ids),
                    "transcript_json": item.transcript_json,
                }
                for item in examples
            ],
            "split": split,
            "version": version,
        }
    ).encode("utf-8")


def _manifest_history_payload(manifest: SyntheticManifest) -> dict[str, object]:
    return json.loads(
        _manifest_payload(
            split=manifest.split,
            version=manifest.version,
            examples=manifest.examples,
        )
    )


def _json_safe_optimizer_state(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (UUID, Decimal)):
        return str(value)
    if isinstance(value, Mapping):
        converted: dict[str, object] = {}
        for key, item in value.items():
            safe_key = key if isinstance(key, str) else canonical_json(
                _json_safe_optimizer_state(key)
            )
            converted[safe_key] = _json_safe_optimizer_state(item)
        return converted
    if isinstance(value, (list, tuple)):
        return [_json_safe_optimizer_state(item) for item in value]
    if isinstance(value, (set, frozenset)):
        converted = [_json_safe_optimizer_state(item) for item in value]
        return sorted(converted, key=canonical_json)
    raise PromptOptimizationError("optimizer_state_not_json_serializable")


def _gepa_plaintext_state(run_dir: str | Path) -> dict[str, object]:
    from gepa.core.state import GEPAState

    state = GEPAState.load(str(run_dir))
    converted = _json_safe_optimizer_state(state.__dict__)
    if not isinstance(converted, dict):
        raise PromptOptimizationError("optimizer_state_not_json_serializable")
    return converted


def _history_observation_payload(value: Mapping[str, object]) -> dict[str, object]:
    snapshot = value.get("snapshot")
    if not isinstance(snapshot, PromptSnapshot):
        raise PromptOptimizationError("optimization_history_observation_invalid")
    return {
        "actual_model": value.get("actual_model"),
        "actual_provider": value.get("actual_provider"),
        "call_key": value["call_key"],
        "cost_details": value.get("cost_details"),
        "phase": value["phase"],
        "prompt": _snapshot_payload(snapshot),
        "raw_response": value["raw_response"],
        "request": value["request"],
        "token_usage": value.get("token_usage"),
        "validated_result": value["validated_result"],
    }


async def mark_prompt_optimization_history_staging_started(
    settings: Any,
    *,
    run_id: UUID,
    phase: Literal["evolution", "heldout"],
) -> None:
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database

    engine, sessionmaker = create_prompt_optimization_database(settings)
    try:
        async with sessionmaker() as db:
            run = await db.get(PromptOptimizationRun, run_id, with_for_update=True)
            if run is None:
                raise PromptOptimizationError("optimization_run_not_found")
            budget = dict(run.budget or {})
            staging = dict(budget.get(OPTIMIZATION_HISTORY_STAGING_KEY, {}))
            materialization = dict(
                budget.get(OPTIMIZATION_HISTORY_MATERIALIZATION_KEY, {})
            )
            if materialization.get(phase, {}).get("status") != "complete":
                staging[phase] = {"status": "started"}
                budget[OPTIMIZATION_HISTORY_STAGING_KEY] = staging
                run.budget = budget
                await db.commit()
    finally:
        await engine.dispose()


def persist_prompt_optimization_history(
    storage: Any,
    *,
    run_id: UUID,
    phase: Literal["evolution", "heldout"],
    datasets: Sequence[SyntheticManifest],
    observations: Sequence[Mapping[str, object]],
    optimizer_state: Mapping[str, object],
) -> dict[str, object]:
    from twobrain_rec_server.workflows.outcome_generation_workflow import (
        TranscriptSnapshotError,
        split_plaintext_transcript,
    )

    content = {
        "datasets": [_manifest_history_payload(manifest) for manifest in datasets],
        "model_calls": [_history_observation_payload(value) for value in observations],
        "optimizer_state": dict(optimizer_state),
        "phase": phase,
        "run_id": str(run_id),
        "schema_version": OPTIMIZATION_HISTORY_SCHEMA_VERSION,
    }
    plaintext = canonical_json(content)
    try:
        metadata, chunks = split_plaintext_transcript(
            plaintext,
            candidate_id=str(run_id),
            source_result_id=phase,
            max_chunk_bytes=OPTIMIZATION_HISTORY_CHUNK_BYTES,
            max_snapshot_bytes=OPTIMIZATION_HISTORY_MAX_BYTES,
            max_serialized_bytes=OPTIMIZATION_HISTORY_PAYLOAD_BYTES,
        )
    except TranscriptSnapshotError as exc:
        raise PromptOptimizationError("optimization_history_oversize") from exc
    prefix = f"{CHECKPOINT_PREFIX}/{run_id}/temporal-history/{phase}/{metadata['snapshot_hash']}"
    chunk_refs: list[dict[str, object]] = []
    for chunk in chunks:
        encoded = canonical_json(chunk).encode("utf-8")
        index = int(chunk["chunk_index"])
        key = f"{prefix}/{index:08d}.json"
        storage.put_stream(key, BytesIO(encoded), len(encoded))
        chunk_refs.append({"key": key, "sha256": sha256(encoded).hexdigest()})
    return {
        **metadata,
        "phase": phase,
        "schema_version": OPTIMIZATION_HISTORY_SCHEMA_VERSION,
        "chunks": chunk_refs,
    }


def _snapshot_payload(snapshot: PromptSnapshot) -> dict[str, object]:
    return {
        "name": snapshot.name,
        "version": snapshot.version,
        "prompt_type": snapshot.prompt_type,
        "prompt": snapshot.prompt,
        "config": snapshot.config,
        "source": snapshot.source,
        "canonical_hash": snapshot.canonical_hash,
    }


def _snapshot_from_payload(value: Mapping[str, object]) -> PromptSnapshot:
    snapshot = validate_prompt_snapshot(
        name=str(value["name"]),
        version=int(value["version"]),
        prompt_type=str(value["prompt_type"]),
        prompt=value["prompt"],
        config=value["config"],  # type: ignore[arg-type]
        source=str(value.get("source", "langfuse_production")),
    )
    if snapshot.canonical_hash != value.get("canonical_hash"):
        raise PromptOptimizationError("optimization_prompt_snapshot_mismatch")
    return snapshot


def _manifest_object_key(ref: str) -> str:
    if not ref.startswith("synthetic://"):
        raise PromptOptimizationError("synthetic_manifest_ref_invalid")
    suffix = ref.removeprefix("synthetic://").strip("/")
    if not suffix or ".." in suffix.split("/") or len(suffix) > 420:
        raise PromptOptimizationError("synthetic_manifest_ref_invalid")
    return f"{CHECKPOINT_PREFIX}/datasets/{suffix}.json"


def _load_manifest(storage: Any, *, ref: str, expected: object, split: str) -> SyntheticManifest:
    raw = storage.get_bytes(_manifest_object_key(ref))
    if len(raw) > 8 * 1024 * 1024:
        raise PromptOptimizationError("synthetic_manifest_too_large")
    try:
        value = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptOptimizationError("synthetic_manifest_invalid") from exc
    if (
        not isinstance(value, dict)
        or value.get("split") != split
        or not isinstance(value.get("examples"), list)
    ):
        raise PromptOptimizationError("synthetic_manifest_invalid")
    examples = []
    for row in value["examples"]:
        if not isinstance(row, dict):
            raise PromptOptimizationError("synthetic_manifest_invalid")
        examples.append(
            SyntheticExample(
                id=str(row["id"]),
                transcript_json=str(row["transcript_json"]),
                segment_ids=frozenset(str(item) for item in row["segment_ids"]),
                required_categories=tuple(str(item) for item in row["required_categories"]),
                human_labels=dict(row.get("human_labels", {})),
                forbidden_copy_fragments=tuple(row.get("forbidden_copy_fragments", ())),
            )
        )
    manifest = SyntheticManifest.create(
        ref=ref,
        split=split,  # type: ignore[arg-type]
        version=str(value["version"]),
        examples=examples,
    )
    expected_hash = expected.get("sha256") if isinstance(expected, Mapping) else expected
    expected_count = expected.get("count") if isinstance(expected, Mapping) else None
    if manifest.sha256 != expected_hash or (
        expected_count is not None and len(manifest.examples) != int(expected_count)
    ):
        raise PromptOptimizationError("synthetic_manifest_hash_mismatch")
    return manifest


class _PersistentLedgerBridge:
    def __init__(
        self,
        *,
        settings: Any,
        run_id: UUID,
        storage: Any,
        contract: PinnedOptimizationContract,
    ) -> None:
        self.settings = settings
        self.run_id = run_id
        self.storage = storage
        self.contract = contract

    def _snapshot(self, phase: str) -> PromptSnapshot:
        if phase == "task":
            return self.contract.source
        if phase == "reflection":
            return self.contract.reflection
        return self.contract.judges[JUDGE_NAMES[CALL_PHASES[2:].index(phase)]]

    def reserve(
        self,
        *,
        call_key: str,
        phase: str,
        activity_attempt: int,
        now: datetime,
        token_ceiling: int,
        cost_ceiling: Decimal,
    ) -> CallReservation:
        snapshot = self._snapshot(phase)

        async def operation() -> PersistedCallReservation:
            from twobrain_rec_server.db.session import create_prompt_optimization_database

            engine, sessionmaker = create_prompt_optimization_database(self.settings)
            try:
                async with sessionmaker() as db:
                    reservation = await reserve_persisted_call(
                        db,
                        run_id=self.run_id,
                        call_key=call_key,
                        phase=phase,
                        prompt_version=snapshot.version,
                        config_hash=prompt_config_hash(snapshot.config),
                        model_route=snapshot.model,
                        token_ceiling=token_ceiling,
                        cost_ceiling=cost_ceiling,
                        activity_attempt=activity_attempt,
                        now=now,
                    )
                    await db.commit()
                    return reservation
            finally:
                await engine.dispose()

        persisted = asyncio.run(operation())
        result = None
        if persisted.status == "succeeded":
            if persisted.result_artifact_ref is None:
                raise PromptOptimizationError("optimization_ledger_result_invalid")
            result = _model_call_from_bytes(self.storage.get_bytes(persisted.result_artifact_ref))
        return CallReservation(
            call_key=call_key,
            phase=phase,
            fence=persisted.fence,
            status=persisted.status,
            reserved_tokens=token_ceiling,
            reserved_cost=cost_ceiling,
            result=result,
        )

    def succeed(
        self,
        *,
        call_key: str,
        fence: UUID,
        result: object,
        actual_tokens: int | None,
        actual_cost: Decimal | None,
    ) -> None:
        if not isinstance(result, ModelCall):
            raise PromptOptimizationError("optimization_ledger_result_invalid")
        artifact_ref = f"{CHECKPOINT_PREFIX}/{self.run_id}/calls/{call_key}/{fence}.json"
        payload = _model_call_bytes(result)
        self.storage.put_stream(artifact_ref, BytesIO(payload), len(payload))

        async def operation() -> None:
            from twobrain_rec_server.db.session import create_prompt_optimization_database

            engine, sessionmaker = create_prompt_optimization_database(self.settings)
            try:
                async with sessionmaker() as db:
                    await complete_persisted_call(
                        db,
                        run_id=self.run_id,
                        call_key=call_key,
                        fence=fence,
                        result_artifact_ref=artifact_ref,
                        input_tokens=result.input_tokens,
                        output_tokens=result.output_tokens,
                        actual_cost=actual_cost,
                        now=datetime.now(UTC),
                    )
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(operation())

    def fail(self, *, call_key: str, fence: UUID) -> None:
        async def operation() -> None:
            from twobrain_rec_server.db.session import create_prompt_optimization_database

            engine, sessionmaker = create_prompt_optimization_database(self.settings)
            try:
                async with sessionmaker() as db:
                    await mark_persisted_call_ambiguous(
                        db,
                        run_id=self.run_id,
                        call_key=call_key,
                        fence=fence,
                        now=datetime.now(UTC),
                    )
                    await db.commit()
            finally:
                await engine.dispose()

        asyncio.run(operation())

    def charged_totals(self) -> tuple[int, int, Decimal]:
        # The PostgreSQL reserve transition locks the run and enforces projected totals.
        return 0, 0, Decimal(0)

    async def history_observations(
        self,
        *,
        call_keys: Collection[str] | None = None,
    ) -> list[dict[str, object]]:
        from sqlalchemy import select

        from twobrain_rec_server.db.models import PromptOptimizationCallLedger
        from twobrain_rec_server.db.session import create_prompt_optimization_database

        engine, sessionmaker = create_prompt_optimization_database(self.settings)
        try:
            async with sessionmaker() as db:
                query = select(PromptOptimizationCallLedger).where(
                    PromptOptimizationCallLedger.run_id == self.run_id,
                    PromptOptimizationCallLedger.status == "succeeded",
                )
                if call_keys is not None:
                    if not call_keys:
                        return []
                    query = query.where(
                        PromptOptimizationCallLedger.call_key.in_(sorted(call_keys))
                    )
                rows = list(
                    (
                        await db.scalars(
                            query.order_by(
                                PromptOptimizationCallLedger.created_at,
                                PromptOptimizationCallLedger.call_key,
                            )
                        )
                    ).all()
                )
        finally:
            await engine.dispose()
        observations: list[dict[str, object]] = []
        for row in rows:
            if not row.result_artifact_ref:
                raise PromptOptimizationError("optimization_ledger_result_invalid")
            result = _model_call_from_bytes(
                await asyncio.to_thread(self.storage.get_bytes, row.result_artifact_ref)
            )
            observations.append(
                {
                    "actual_model": result.actual_model,
                    "actual_provider": result.actual_provider,
                    "call_key": row.call_key,
                    "cost_details": result.cost_details,
                    "phase": row.phase,
                    "raw_response": result.raw_response,
                    "request": result.request,
                    "snapshot": self._snapshot(row.phase),
                    "token_usage": result.token_usage,
                    "validated_result": result.validated_result,
                }
            )
        return observations


def _model_call_bytes(value: ModelCall) -> bytes:
    return canonical_json(
        {
            "actual_cost": str(value.cost) if value.cost is not None else None,
            "actual_model": value.actual_model,
            "actual_provider": value.actual_provider,
            "cost_details": value.cost_details,
            "input_tokens": value.input_tokens,
            "output_tokens": value.output_tokens,
            "raw_response": value.raw_response,
            "request": value.request,
            "token_usage": value.token_usage,
            "validated_result": value.validated_result,
        }
    ).encode("utf-8")


def _model_call_from_bytes(payload: bytes) -> ModelCall:
    if len(payload) > 4 * 1024 * 1024:
        raise PromptOptimizationError("optimization_ledger_result_invalid")
    value = json.loads(payload)
    return ModelCall(
        request=value["request"],
        raw_response=value["raw_response"],
        validated_result=value["validated_result"],
        input_tokens=value["input_tokens"],
        output_tokens=value["output_tokens"],
        cost=Decimal(value["actual_cost"]) if value["actual_cost"] is not None else None,
        actual_model=value.get("actual_model"),
        actual_provider=value.get("actual_provider"),
        token_usage=value.get("token_usage"),
        cost_details=value.get("cost_details"),
    )


class _ProductionModelExecutor:
    def __init__(self, *, settings: Any) -> None:
        from twobrain_rec_server.outcomes.generator import LiteLLMGateway

        if settings.litellm_base_url is None or settings.litellm_api_key_file is None:
            raise PromptOptimizationError("litellm_not_configured")
        self.gateway = LiteLLMGateway(
            base_url=str(settings.litellm_base_url),
            api_key=settings.litellm_api_key_file.read_text(encoding="utf-8").strip(),
            timeout_seconds=settings.litellm_request_timeout_seconds,
        )

    def __call__(
        self,
        *,
        phase: str,
        snapshot: PromptSnapshot,
        prompt_text: str,
        variables: Mapping[str, str],
    ) -> ModelCall:
        effective = snapshot
        if phase == "task":
            effective = validate_candidate_prompt(snapshot, prompt_text)
            if set(variables) != TASK_MODEL_VARIABLE_KEYS:
                raise PromptOptimizationError("optimization_task_variables_invalid")
        messages = _compile_optimization_messages(effective, variables)
        result = asyncio.run(self.gateway.generate(snapshot=effective, messages=messages))
        usage = result.token_usage or {}
        return ModelCall(
            request=result.request,
            raw_response=result.raw_response,
            validated_result=result.parsed_content,
            input_tokens=_optional_int(usage.get("prompt_tokens") or usage.get("input_tokens")),
            output_tokens=_optional_int(
                usage.get("completion_tokens") or usage.get("output_tokens")
            ),
            cost=(
                Decimal(str(result.cost_details["total"]))
                if result.cost_details and result.cost_details.get("total") is not None
                else None
            ),
            actual_model=result.actual_model,
            actual_provider=result.actual_provider,
            token_usage=result.token_usage,
            cost_details=result.cost_details,
        )


def _compile_optimization_messages(
    snapshot: PromptSnapshot,
    variables: Mapping[str, str],
) -> list[dict[str, str]]:
    if snapshot.prompt_type == "text":
        if not isinstance(snapshot.prompt, str):
            raise PromptOptimizationError("optimization_prompt_invalid")
        content = snapshot.prompt
        for key, value in variables.items():
            content = content.replace(f"<{key}>", value)
        if "<curr_param>" in content or "<side_info>" in content:
            raise PromptOptimizationError("optimization_prompt_variables_unresolved")
        return [{"role": "user", "content": content}]
    if not isinstance(snapshot.prompt, list):
        raise PromptOptimizationError("optimization_prompt_invalid")
    messages = []
    for item in snapshot.prompt:
        if not isinstance(item, Mapping):
            raise PromptOptimizationError("optimization_prompt_invalid")
        content = str(item["content"])
        for key, value in variables.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        if "{{" in content or "}}" in content:
            raise PromptOptimizationError("optimization_prompt_variables_unresolved")
        messages.append({"role": str(item["role"]), "content": content})
    return messages


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) else None


def _contract_from_resolved(payload: Mapping[str, object]) -> PinnedOptimizationContract:
    return PinnedOptimizationContract(
        source=_snapshot_from_payload(payload["source_prompt"]),  # type: ignore[arg-type]
        reflection=_snapshot_from_payload(payload["reflection_prompt"]),  # type: ignore[arg-type]
        judges={
            name: _snapshot_from_payload(value)  # type: ignore[arg-type]
            for name, value in payload["judge_prompts"].items()  # type: ignore[union-attr]
        },
    )


def _calibrations_from_resolved(
    payload: Mapping[str, object],
    contract: PinnedOptimizationContract,
) -> dict[str, JudgeCalibration]:
    refs = {
        str(item["prompt_name"]): item
        for item in payload["judge_prompt_refs"]  # type: ignore[union-attr]
    }
    calibrations: dict[str, JudgeCalibration] = {}
    for name, snapshot in contract.judges.items():
        calibration, gate = required_judge_calibration(snapshot)
        if refs.get(name, {}).get("calibration_gate") != gate:
            raise PromptOptimizationError("judge_calibration_contract_changed")
        calibrations[name] = calibration
    return calibrations


async def resolve_prompt_optimization_contract_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )

    settings = get_settings()
    if not settings.prompt_optimization_enabled:
        raise PromptOptimizationError("prompt_optimization_disabled")
    run_id = UUID(str(payload["run_id"]))
    engine, sessionmaker = create_prompt_optimization_database(settings)
    try:
        async with sessionmaker() as db:
            run = await db.get(PromptOptimizationRun, run_id)
            if run is None or run.deployment_scope != "global":
                raise PromptOptimizationError("optimization_run_not_found")
            run_values = {
                "prompt_name": run.prompt_name,
                "source_prompt_version": run.source_prompt_version,
                "source_config_hash": run.source_config_hash,
                "reflection_prompt_name": run.reflection_prompt_name,
                "reflection_prompt_version": run.reflection_prompt_version,
                "reflection_config_hash": run.reflection_config_hash,
                "judge_prompt_refs": list(run.judge_prompt_refs),
                "dataset_refs": {
                    "train": run.train_dataset_ref,
                    "development": run.development_dataset_ref,
                    "heldout": run.heldout_dataset_ref,
                },
                "dataset_manifest_hashes": dict(run.dataset_manifest_hashes),
                "budget": dict(run.budget),
                "deadline_at": run.deadline_at.isoformat(),
                "rollback_prompt_version": run.rollback_prompt_version,
            }
    finally:
        await engine.dispose()
    client = create_langfuse_client(settings)
    try:
        source = _fetch_exact_snapshot(
            client,
            name=str(run_values["prompt_name"]),
            version=int(run_values["source_prompt_version"]),
            prompt_type="chat",
        )
        reflection = _fetch_exact_snapshot(
            client,
            name=str(run_values["reflection_prompt_name"]),
            version=int(run_values["reflection_prompt_version"]),
            prompt_type="text",
        )
        judges = {
            str(item["prompt_name"]): _fetch_exact_snapshot(
                client,
                name=str(item["prompt_name"]),
                version=int(item["prompt_version"]),
                prompt_type="chat",
            )
            for item in run_values["judge_prompt_refs"]
        }
    finally:
        shutdown_langfuse(client)
    if (
        prompt_config_hash(source.config) != run_values["source_config_hash"]
        or prompt_config_hash(reflection.config) != run_values["reflection_config_hash"]
        or reflection.config.get(CONTROL_GATE_CONFIG_KEY)
        != run_values["budget"].get("reflection_control_gate")
        or any(
            prompt_config_hash(judges[str(item["prompt_name"])].config) != item["config_hash"]
            for item in run_values["judge_prompt_refs"]
        )
        or any(
            judges[str(item["prompt_name"])].config.get(CONTROL_GATE_CONFIG_KEY)
            != item.get("calibration_gate")
            for item in run_values["judge_prompt_refs"]
        )
    ):
        raise PromptOptimizationError("optimization_prompt_contract_changed")
    return {
        **run_values,
        "source_prompt": _snapshot_payload(source),
        "reflection_prompt": _snapshot_payload(reflection),
        "judge_prompts": {name: _snapshot_payload(value) for name, value in judges.items()},
        "trace_id": optimization_trace_id(run_id),
    }


async def snapshot_prompt_optimization_history_chunk_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.storage.minio_client import get_storage

    run_id = UUID(str(payload["run_id"]))
    phase = str(payload["phase"])
    index = int(payload["chunk_index"])
    descriptor = payload.get("history")
    if (
        phase not in {"evolution", "heldout"}
        or not isinstance(descriptor, Mapping)
        or descriptor.get("schema_version") != OPTIMIZATION_HISTORY_SCHEMA_VERSION
        or descriptor.get("candidate_id") != str(run_id)
        or descriptor.get("source_result_id") != phase
        or descriptor.get("phase") != phase
        or descriptor.get("chunk_count") != len(descriptor.get("chunks", ()))
        or not 0 <= index < int(descriptor.get("chunk_count", -1))
    ):
        raise PromptOptimizationError("optimization_history_descriptor_invalid")
    chunk_ref = descriptor["chunks"][index]
    if not isinstance(chunk_ref, Mapping):
        raise PromptOptimizationError("optimization_history_descriptor_invalid")
    key = str(chunk_ref.get("key", ""))
    expected_prefix = f"{CHECKPOINT_PREFIX}/{run_id}/temporal-history/{phase}/"
    if not key.startswith(expected_prefix) or not key.endswith(f"/{index:08d}.json"):
        raise PromptOptimizationError("optimization_history_descriptor_invalid")
    encoded = await asyncio.to_thread(get_storage(get_settings()).get_bytes, key)
    if (
        len(encoded) > OPTIMIZATION_HISTORY_PAYLOAD_BYTES
        or sha256(encoded).hexdigest() != chunk_ref.get("sha256")
    ):
        raise PromptOptimizationError("optimization_history_chunk_integrity_failed")
    try:
        chunk = json.loads(encoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PromptOptimizationError("optimization_history_chunk_integrity_failed") from exc
    if (
        not isinstance(chunk, dict)
        or chunk.get("candidate_id") != str(run_id)
        or chunk.get("source_result_id") != phase
        or chunk.get("snapshot_hash") != descriptor.get("snapshot_hash")
        or chunk.get("chunk_index") != index
        or chunk.get("chunk_count") != descriptor.get("chunk_count")
        or not isinstance(chunk.get("transcript_utf8"), str)
    ):
        raise PromptOptimizationError("optimization_history_chunk_integrity_failed")
    # This complete plaintext chunk is intentionally the activity result so it is
    # retained in Temporal History. It contains synthetic optimizer content only.
    return chunk


async def finalize_prompt_optimization_history_materialization_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database

    run_id = UUID(str(payload["run_id"]))
    phase = str(payload["phase"])
    descriptor = payload.get("history")
    if (
        phase not in {"evolution", "heldout"}
        or not isinstance(descriptor, Mapping)
        or descriptor.get("schema_version") != OPTIMIZATION_HISTORY_SCHEMA_VERSION
        or descriptor.get("candidate_id") != str(run_id)
        or descriptor.get("source_result_id") != phase
        or descriptor.get("phase") != phase
        or not isinstance(descriptor.get("snapshot_hash"), str)
        or not isinstance(descriptor.get("chunk_count"), int)
        or descriptor.get("chunk_count") != len(descriptor.get("chunks", ()))
    ):
        raise PromptOptimizationError("optimization_history_descriptor_invalid")
    materialized = validate_history_materialization_certificate(
        {
            "bytes": descriptor.get("transcript_bytes"),
            "chunk_count": descriptor.get("chunk_count"),
            "snapshot_hash": descriptor.get("snapshot_hash"),
            "status": "complete",
        },
        phase=phase,
    )
    engine, sessionmaker = create_prompt_optimization_database(get_settings())
    try:
        async with sessionmaker() as db:
            run = await db.get(PromptOptimizationRun, run_id, with_for_update=True)
            if run is None:
                raise PromptOptimizationError("optimization_run_not_found")
            budget = dict(run.budget or {})
            state = dict(budget.get(OPTIMIZATION_HISTORY_MATERIALIZATION_KEY, {}))
            existing = state.get(phase)
            if existing is not None and existing != materialized:
                raise PromptOptimizationError("optimization_history_materialization_conflict")
            state[phase] = materialized
            budget[OPTIMIZATION_HISTORY_MATERIALIZATION_KEY] = state
            run.budget = budget
            await db.commit()
    finally:
        await engine.dispose()
    return {"phase": phase, **materialized}


async def run_gepa_prompt_optimization_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from temporalio import activity

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )
    from twobrain_rec_server.storage.minio_client import get_storage

    settings = get_settings()
    resolved = payload["resolved_contract"]
    if not isinstance(resolved, Mapping):
        raise PromptOptimizationError("optimization_contract_invalid")
    run_id = UUID(str(payload["run_id"]))
    storage = get_storage(settings)
    stop_requested = threading.Event()
    refs = resolved["dataset_refs"]
    hashes = resolved["dataset_manifest_hashes"]
    train = await _run_thread_until_quiescent(
        _load_manifest,
        storage,
        ref=refs["train"],
        expected=hashes["train"],
        split="train",
        on_cancel=stop_requested.set,
    )
    development = await _run_thread_until_quiescent(
        _load_manifest,
        storage,
        ref=refs["development"],
        expected=hashes["development"],
        split="development",
        on_cancel=stop_requested.set,
    )
    # Held-out content is deliberately unavailable in this activity.
    if {item.id for item in train.examples} & {item.id for item in development.examples}:
        raise PromptOptimizationError("synthetic_manifest_split_overlap")
    contract = _contract_from_resolved(resolved)
    observations: list[dict[str, object]] = []
    observed_call_keys: set[str] = set()
    langfuse = create_langfuse_client(settings)

    def observer(**value: object) -> None:
        call_key = str(value["call_key"])
        if call_key in observed_call_keys:
            return
        observed_call_keys.add(call_key)
        observations.append(dict(value))
        _publish_optimization_observation(langfuse, run_id=run_id, value=value)
        with suppress(Exception):
            activity.heartbeat({"phase": value["phase"], "call_key": value["call_key"]})

    budget_value = resolved["budget"]
    budget = OptimizationBudget(
        max_calls=int(budget_value["max_calls"]),
        max_tokens=int(budget_value["max_tokens"]),
        max_cost=Decimal(str(budget_value["max_cost"])),
        deadline_at=datetime.fromisoformat(str(resolved["deadline_at"])),
    )
    ledger = _PersistentLedgerBridge(
        settings=settings,
        run_id=run_id,
        storage=storage,
        contract=contract,
    )
    calibrations = _calibrations_from_resolved(resolved, contract)
    try:
        with tempfile.TemporaryDirectory(prefix=f"graf-gepa-{run_id}-") as run_dir:
            engine, sessionmaker = create_prompt_optimization_database(settings)
            try:
                async with sessionmaker() as db:
                    run = await db.get(PromptOptimizationRun, run_id)
                    if run and run.run_artifact_ref and run.checkpoint_hash:
                        checkpoint_payload = await _run_thread_until_quiescent(
                            storage.get_bytes,
                            run.run_artifact_ref,
                            on_cancel=stop_requested.set,
                        )
                        restore_gepa_checkpoint(
                            run_id=run_id,
                            key=run.run_artifact_ref,
                            payload=checkpoint_payload,
                            expected_hash=run.checkpoint_hash,
                            manifest_hashes={
                                "train": train.sha256,
                                "development": development.sha256,
                            },
                            run_dir=run_dir,
                        )
                    revision = (run.checkpoint_revision or 0) + 1 if run else 1
            finally:
                await engine.dispose()
            next_revision = [revision]
            checkpoint_failures: list[Exception] = []

            def persist_checkpoint(checkpoint_dir: str, iteration: int) -> None:
                current_revision = next_revision[0]
                try:
                    key, checkpoint_payload, checkpoint_hash = pack_gepa_checkpoint(
                        run_id=run_id,
                        revision=current_revision,
                        run_dir=checkpoint_dir,
                        manifest_hashes={
                            "train": train.sha256,
                            "development": development.sha256,
                        },
                    )
                    storage.put_stream(
                        key,
                        BytesIO(checkpoint_payload),
                        len(checkpoint_payload),
                    )

                    async def advance() -> None:
                        checkpoint_engine, checkpoint_sessionmaker = create_prompt_optimization_database(
                            settings
                        )
                        try:
                            async with checkpoint_sessionmaker() as db:
                                await advance_checkpoint_pointer(
                                    db,
                                    run_id=run_id,
                                    revision=current_revision,
                                    key=key,
                                    checksum=checkpoint_hash,
                                )
                                await db.commit()
                        finally:
                            await checkpoint_engine.dispose()

                    asyncio.run(advance())
                    next_revision[0] += 1
                    with suppress(Exception):
                        activity.heartbeat(
                            {
                                "phase": "checkpoint",
                                "iteration": iteration,
                                "revision": current_revision,
                            }
                        )
                except Exception as exc:
                    checkpoint_failures.append(exc)
                    # GEPA's callback dispatcher is observational and swallows
                    # exceptions. Its built-in FileStopper sees this marker and
                    # ends the run at the next safe boundary; we then fail closed.
                    Path(checkpoint_dir, "gepa.stop").touch()
                    raise

            adapter = PromptOptimizationAdapter(
                run_id=run_id,
                contract=contract,
                ledger=ledger,
                executor=_ProductionModelExecutor(settings=settings),
                observer=observer,
                budget=budget,
                calibrations=calibrations,
                activity_attempt=activity.info().attempt,
                cancelled=lambda: stop_requested.is_set() or activity.is_cancelled(),
            )

            def stop_gepa() -> None:
                stop_requested.set()
                Path(run_dir, "gepa.stop").touch()

            candidate = await _run_thread_until_quiescent(
                run_gepa_optimization,
                adapter=adapter,
                source_prompt_text=canonical_json(contract.source.prompt),
                train=train,
                development=development,
                run_dir=run_dir,
                max_metric_calls=budget.max_calls,
                callbacks=[DurableCheckpointCallback(persist_checkpoint)],
                on_cancel=stop_gepa,
            )
            if checkpoint_failures:
                raise PromptOptimizationError("checkpoint_persistence_failed") from checkpoint_failures[0]
            await _run_thread_until_quiescent(
                persist_checkpoint,
                run_dir,
                -1,
                on_cancel=stop_gepa,
            )
            optimizer_state = await _run_thread_until_quiescent(
                _gepa_plaintext_state,
                run_dir,
                on_cancel=stop_gepa,
            )
            history_observations = await ledger.history_observations()
            await mark_prompt_optimization_history_staging_started(
                settings,
                run_id=run_id,
                phase="evolution",
            )
            temporal_history = await _run_thread_until_quiescent(
                persist_prompt_optimization_history,
                storage,
                run_id=run_id,
                phase="evolution",
                datasets=(train, development),
                observations=history_observations,
                optimizer_state=optimizer_state,
                on_cancel=stop_gepa,
            )
    finally:
        shutdown_langfuse(langfuse)
    return {
        "prompt_text": candidate.prompt_text,
        "prompt_hash": candidate.prompt_hash,
        "source_config_hash": candidate.source_config_hash,
        "development_score": candidate.development_score,
        "observed_call_count": len(observations),
        "temporal_history": temporal_history,
    }


async def validate_heldout_prompt_candidate_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from temporalio import activity

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )
    from twobrain_rec_server.storage.minio_client import get_storage

    settings = get_settings()
    resolved = payload["resolved_contract"]
    optimized = payload["optimization_result"]
    if not isinstance(resolved, Mapping) or not isinstance(optimized, Mapping):
        raise PromptOptimizationError("optimization_contract_invalid")
    run_id = UUID(str(payload["run_id"]))
    storage = get_storage(settings)
    stop_requested = threading.Event()
    heldout = await _run_thread_until_quiescent(
        _load_manifest,
        storage,
        ref=resolved["dataset_refs"]["heldout"],
        expected=resolved["dataset_manifest_hashes"]["heldout"],
        split="heldout",
        on_cancel=stop_requested.set,
    )
    train = await _run_thread_until_quiescent(
        _load_manifest,
        storage,
        ref=resolved["dataset_refs"]["train"],
        expected=resolved["dataset_manifest_hashes"]["train"],
        split="train",
        on_cancel=stop_requested.set,
    )
    development = await _run_thread_until_quiescent(
        _load_manifest,
        storage,
        ref=resolved["dataset_refs"]["development"],
        expected=resolved["dataset_manifest_hashes"]["development"],
        split="development",
        on_cancel=stop_requested.set,
    )
    validate_disjoint_manifests(train, development, heldout)
    contract = _contract_from_resolved(resolved)
    observations: list[dict[str, object]] = []
    observed_call_keys: set[str] = set()
    langfuse = create_langfuse_client(settings)

    def observer(**value: object) -> None:
        call_key = str(value["call_key"])
        if call_key in observed_call_keys:
            return
        observed_call_keys.add(call_key)
        observations.append(dict(value))
        _publish_optimization_observation(langfuse, run_id=run_id, value=value)
        with suppress(Exception):
            activity.heartbeat({"phase": value["phase"], "call_key": value["call_key"]})

    ledger = _PersistentLedgerBridge(
        settings=settings,
        run_id=run_id,
        storage=storage,
        contract=contract,
    )
    adapter = PromptOptimizationAdapter(
        run_id=run_id,
        contract=contract,
        ledger=ledger,
        executor=_ProductionModelExecutor(settings=settings),
        observer=observer,
        budget=OptimizationBudget(
            max_calls=int(resolved["budget"]["max_calls"]),
            max_tokens=int(resolved["budget"]["max_tokens"]),
            max_cost=Decimal(str(resolved["budget"]["max_cost"])),
            deadline_at=datetime.fromisoformat(str(resolved["deadline_at"])),
        ),
        calibrations=_calibrations_from_resolved(resolved, contract),
        activity_attempt=activity.info().attempt,
        cancelled=lambda: stop_requested.is_set() or activity.is_cancelled(),
    )
    try:
        activity.heartbeat({"phase": "heldout_start"})
        result = await _run_thread_until_quiescent(
            validate_heldout_candidate,
            adapter=adapter,
            candidate=OptimizationCandidate(
                prompt_text=str(optimized["prompt_text"]),
                prompt_hash=str(optimized["prompt_hash"]),
                source_config_hash=str(optimized["source_config_hash"]),
                development_score=float(optimized["development_score"]),
            ),
            heldout=heldout,
            minimum_metric_score=0.9,
            on_cancel=stop_requested.set,
        )
        activity.heartbeat({"phase": "heldout_complete"})
    finally:
        shutdown_langfuse(langfuse)
    history_observations = await ledger.history_observations(call_keys=observed_call_keys)
    await mark_prompt_optimization_history_staging_started(
        settings,
        run_id=run_id,
        phase="heldout",
    )
    temporal_history = await _run_thread_until_quiescent(
        persist_prompt_optimization_history,
        storage,
        run_id=run_id,
        phase="heldout",
        datasets=(heldout,),
        observations=history_observations,
        optimizer_state={
            "candidate": {
                "development_score": result.development_score,
                "hard_gates_passed": result.hard_gates_passed,
                "heldout_scores": dict(result.heldout_scores),
                "prompt_hash": result.prompt_hash,
                "source_config_hash": result.source_config_hash,
            }
        },
        on_cancel=stop_requested.set,
    )
    return {
        "hard_gates_passed": result.hard_gates_passed,
        "heldout_scores": dict(result.heldout_scores),
        "observed_call_count": len(observations),
        "temporal_history": temporal_history,
    }


async def publish_prompt_candidate_activity(payload: dict[str, Any]) -> dict[str, object]:
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )

    settings = get_settings()
    run_id = UUID(str(payload["run_id"]))
    resolved = payload["resolved_contract"]
    optimized = payload["optimization_result"]
    heldout = payload["heldout_result"]
    if not heldout["hard_gates_passed"]:
        raise PromptOptimizationError("heldout_gate_failed")
    source = _snapshot_from_payload(resolved["source_prompt"])
    prompt = json.loads(str(optimized["prompt_text"]))
    approval_expires_at = datetime.fromisoformat(str(payload["approval_expires_at"]))
    cancellation_observed = threading.Event()
    idempotency_tag = f"graf-optimization-run-{run_id}"
    engine, sessionmaker = create_prompt_optimization_database(settings)
    client = create_langfuse_client(settings)
    try:
        async with _quiescent_session_scope(
            sessionmaker(),
            cancellation_observed=cancellation_observed,
            complete_after_cancel=False,
        ) as db:
            run = await db.get(PromptOptimizationRun, run_id, with_for_update=True)
            if run is None or run.source_prompt_version != source.version:
                raise PromptOptimizationError("production_source_conflict")
            persisted = (
                run.candidate_prompt_version,
                run.candidate_prompt_hash,
                run.candidate_config_hash,
                run.approval_expires_at,
            )
            if all(value is not None for value in persisted):
                candidate = await _run_thread_until_quiescent(
                    load_persisted_candidate_result,
                    client,
                    source=source,
                    candidate_prompt=prompt,
                    candidate_version=int(run.candidate_prompt_version),
                    candidate_hash=str(run.candidate_prompt_hash),
                    candidate_config_hash=str(run.candidate_config_hash),
                    on_cancel=lambda: None,
                )
                activity_result = {
                    "candidate_prompt_version": candidate.version,
                    "candidate_prompt_hash": candidate.canonical_hash,
                    "candidate_config_hash": prompt_config_hash(candidate.config),
                    "approval_expires_at": run.approval_expires_at.isoformat(),  # type: ignore[union-attr]
                }
            elif any(value is not None for value in persisted):
                raise PromptOptimizationError("candidate_persisted_result_incomplete")
            else:
                candidate = await _run_thread_until_quiescent(
                    publish_or_recover_unlabelled_candidate,
                    client,
                    source=source,
                    candidate_prompt=prompt,
                    idempotency_tag=idempotency_tag,
                    on_cancel=lambda: None,
                    complete_after_cancel=True,
                    cancellation_observed=cancellation_observed,
                )
                run.candidate_prompt_version = candidate.version
                run.candidate_prompt_hash = candidate.canonical_hash
                run.candidate_config_hash = prompt_config_hash(candidate.config)
                run.aggregate_scores = {
                    "development_score": optimized["development_score"],
                    "heldout_scores": heldout["heldout_scores"],
                    "hard_gates_passed": True,
                }
                run.approval_state = "awaiting_human"
                run.approval_expires_at = approval_expires_at
                run.status = "candidate"
                await _commit_database_until_quiescent(
                    db,
                    cancellation_observed=cancellation_observed,
                    complete_after_cancel=True,
                )
                activity_result = {
                    "candidate_prompt_version": candidate.version,
                    "candidate_prompt_hash": candidate.canonical_hash,
                    "candidate_config_hash": prompt_config_hash(candidate.config),
                    "approval_expires_at": approval_expires_at.isoformat(),
                }
    finally:
        shutdown_langfuse(client)
        await _complete_async_operation_until_quiescent(
            engine.dispose(),
            cancellation_observed=cancellation_observed,
            complete_after_cancel=False,
        )
    if cancellation_observed.is_set():
        # External candidate and its durable result are committed first. The
        # cancellation is then propagated so workflow terminal cleanup records
        # `cancelled` without ever creating a duplicate candidate on retry.
        raise asyncio.CancelledError
    return activity_result


async def authorize_prompt_optimization_action_activity(
    payload: dict[str, str],
) -> dict[str, str]:
    from sqlalchemy import select

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database

    action_id = UUID(payload["action_id"])
    decision = payload["decision"]
    engine, sessionmaker = create_prompt_optimization_database(get_settings())
    try:
        async with sessionmaker() as db:
            run = await db.scalar(
                select(PromptOptimizationRun)
                .where(PromptOptimizationRun.approval_action_id == action_id)
                .with_for_update()
            )
            now = datetime.now(UTC)
            if (
                run is None
                or run.status != "candidate"
                or run.approval_state != "awaiting_human"
                or run.approval_expires_at is None
                or now >= run.approval_expires_at
                or run.approved_by_actor_id is None
            ):
                return {"status": "denied"}
            run.approval_state = decision
            run.approved_at = now
            if decision == "rejected":
                run.status = "rejected"
            await db.commit()
            return {"status": "authorized"}
    finally:
        await engine.dispose()


async def promote_prompt_candidate_activity(payload: dict[str, Any]) -> dict[str, object]:
    from sqlalchemy import select, text

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )
    from twobrain_rec_server.storage.minio_client import get_storage

    settings = get_settings()
    run_id = UUID(str(payload["run_id"]))
    engine, sessionmaker = create_prompt_optimization_database(settings)
    client = create_langfuse_client(settings)
    try:
        async with _quiescent_session_scope(
            sessionmaker(),
            complete_after_cancel=True,
        ) as db:
            await db.execute(
                text("select pg_advisory_xact_lock(hashtextextended(:name, 0))"),
                {"name": str(payload["prompt_name"])},
            )
            run = await db.scalar(
                select(PromptOptimizationRun)
                .where(PromptOptimizationRun.id == run_id)
                .with_for_update()
            )
            if run is None or str(run.approval_action_id) != payload["approval_action_id"]:
                raise PromptOptimizationError("promotion_not_authorized")
            retrying_completed = run.status == "promoted"
            if not retrying_completed and (
                run.status != "candidate" or run.approval_state != "approved"
            ):
                raise PromptOptimizationError("promotion_not_authorized")
            if run.candidate_prompt_version is None or run.candidate_prompt_hash is None:
                raise PromptOptimizationError("candidate_persisted_result_incomplete")
            snapshot = await _run_thread_until_quiescent(
                move_production_label,
                client,
                prompt_name=run.prompt_name,
                prompt_type="chat",
                expected_source_version=(
                    run.candidate_prompt_version
                    if retrying_completed
                    else run.source_prompt_version
                ),
                target_version=run.candidate_prompt_version,
                protected_label_capability_verified=bool(
                    run.budget.get("protected_label_capability_verified")
                ),
                snapshot_storage=get_storage(settings),
                on_cancel=lambda: None,
                complete_after_cancel=True,
            )
            if snapshot.canonical_hash != run.candidate_prompt_hash:
                raise PromptOptimizationError("promoted_persisted_result_mismatch")
            if retrying_completed:
                return {
                    "status": "promoted",
                    "production_prompt_version": snapshot.version,
                }
            _publish_label_transition(
                client,
                trace_id=optimization_trace_id(run_id),
                run_id=run_id,
                operation="promotion",
                from_version=run.source_prompt_version,
                to_version=snapshot.version,
            )
            run.status = "promoted"
            run.candidate_prompt_hash = snapshot.canonical_hash
            await _commit_database_until_quiescent(
                db,
                complete_after_cancel=True,
            )
            return {"status": "promoted", "production_prompt_version": snapshot.version}
    finally:
        shutdown_langfuse(client)
        await _complete_async_operation_until_quiescent(
            engine.dispose(),
            complete_after_cancel=True,
        )


async def finalize_prompt_optimization_activity(payload: dict[str, Any]) -> dict[str, object]:
    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )

    run_id = UUID(str(payload["run_id"]))
    status = str(payload["status"])
    terminal_statuses = {"rejected", "expired", "failed", "cancelled", "completed"}
    if status not in terminal_statuses:
        raise PromptOptimizationError("optimization_terminal_status_invalid")
    settings = get_settings()
    engine, sessionmaker = create_prompt_optimization_database(settings)
    try:
        async with sessionmaker() as db:
            run = await db.get(PromptOptimizationRun, run_id, with_for_update=True)
            if run is None:
                raise PromptOptimizationError("optimization_run_not_found")
            if run.status == "promoted":
                return {"run_id": str(run_id), "status": run.status}
            if run.status not in terminal_statuses:
                run.status = status
                if payload.get("failure_code"):
                    run.failure_code = str(payload["failure_code"])
                run.approval_state = (
                    status if status in {"rejected", "expired"} else run.approval_state
                )
                if payload.get("aggregate_scores"):
                    run.aggregate_scores = dict(payload["aggregate_scores"])
            await db.commit()
            terminal = {
                "aggregate_scores": dict(run.aggregate_scores or {}),
                "failure_code": run.failure_code,
                "prompt_name": run.prompt_name,
                "status": run.status,
            }
    finally:
        await engine.dispose()
    client = create_langfuse_client(settings)
    try:
        _publish_optimization_terminal_observation(
            client,
            run_id=run_id,
            terminal=terminal,
        )
    finally:
        shutdown_langfuse(client)
    return {"run_id": str(run_id), "status": terminal["status"]}


async def authorize_prompt_rollback_action_activity(payload: dict[str, Any]) -> dict[str, str]:
    from sqlalchemy import select

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database

    engine, sessionmaker = create_prompt_optimization_database(get_settings())
    try:
        async with sessionmaker() as db:
            run = await db.scalar(
                select(PromptOptimizationRun)
                .where(
                    PromptOptimizationRun.id == UUID(str(payload["run_id"])),
                )
                .with_for_update()
            )
            action = dict(run.budget.get("rollback_action", {})) if run else {}
            if (
                run is None
                or run.status not in {"promoted", "rolled_back"}
                or action.get("action_id") != str(payload["action_id"])
                or action.get("consumed") not in {False, True}
                or not action.get("actor_id")
            ):
                return {"status": "denied"}
            if action["consumed"] is True:
                return {"status": "authorized"}
            action["consumed"] = True
            budget = dict(run.budget)
            budget["rollback_action"] = action
            run.budget = budget
            await db.commit()
            return {"status": "authorized"}
    finally:
        await engine.dispose()


async def rollback_prompt_production_label_activity(
    payload: dict[str, Any],
) -> dict[str, object]:
    from sqlalchemy import select, text

    from twobrain_rec_server.config import get_settings
    from twobrain_rec_server.db.models import PromptOptimizationRun
    from twobrain_rec_server.db.session import create_prompt_optimization_database
    from twobrain_rec_server.observability.langfuse import (
        create_langfuse_client,
        shutdown_langfuse,
    )
    from twobrain_rec_server.storage.minio_client import get_storage

    settings = get_settings()
    run_id = UUID(str(payload["run_id"]))
    engine, sessionmaker = create_prompt_optimization_database(settings)
    client = create_langfuse_client(settings)
    try:
        async with _quiescent_session_scope(
            sessionmaker(),
            complete_after_cancel=True,
        ) as db:
            await db.execute(
                text("select pg_advisory_xact_lock(hashtextextended(:name, 0))"),
                {"name": str(payload["prompt_name"])},
            )
            run = await db.scalar(
                select(PromptOptimizationRun)
                .where(PromptOptimizationRun.id == run_id)
                .with_for_update()
            )
            action = dict(run.budget.get("rollback_action", {})) if run else {}
            if (
                run is None
                or run.status not in {"promoted", "rolled_back"}
                or action.get("action_id") != str(payload["action_id"])
                or action.get("consumed") is not True
            ):
                raise PromptOptimizationError("rollback_not_authorized")
            retrying_completed = run.status == "rolled_back"
            snapshot = await _run_thread_until_quiescent(
                move_production_label,
                client,
                prompt_name=run.prompt_name,
                prompt_type="chat",
                expected_source_version=(
                    run.rollback_prompt_version
                    if retrying_completed
                    else run.candidate_prompt_version
                ),
                target_version=run.rollback_prompt_version,
                protected_label_capability_verified=bool(
                    run.budget.get("protected_label_capability_verified")
                ),
                snapshot_storage=get_storage(settings),
                on_cancel=lambda: None,
                complete_after_cancel=True,
            )
            transition_trace_id = rollback_trace_id(run_id, snapshot.version)
            if retrying_completed:
                return {
                    "status": "rolled_back",
                    "production_prompt_version": snapshot.version,
                    "linked_optimization_trace_id": optimization_trace_id(run_id),
                    "rollback_trace_id": transition_trace_id,
                }
            _publish_label_transition(
                client,
                trace_id=transition_trace_id,
                run_id=run_id,
                operation="rollback",
                from_version=run.candidate_prompt_version,
                to_version=snapshot.version,
                linked_trace_id=optimization_trace_id(run_id),
            )
            run.status = "rolled_back"
            await _commit_database_until_quiescent(
                db,
                complete_after_cancel=True,
            )
            return {
                "status": "rolled_back",
                "production_prompt_version": snapshot.version,
                "linked_optimization_trace_id": optimization_trace_id(run_id),
                "rollback_trace_id": transition_trace_id,
            }
    finally:
        shutdown_langfuse(client)
        await _complete_async_operation_until_quiescent(
            engine.dispose(),
            complete_after_cancel=True,
        )


def _fetch_exact_snapshot(
    client: Any,
    *,
    name: str,
    version: int,
    prompt_type: Literal["chat", "text"],
) -> PromptSnapshot:
    prompt = client.get_prompt(
        name,
        version=version,
        type=prompt_type,
        cache_ttl_seconds=0,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    return validate_prompt_snapshot(
        name=name,
        version=int(prompt.version),
        prompt_type=prompt_type,
        prompt=prompt.prompt,
        config=prompt.config or {},
    )


def _publish_optimization_observation(
    client: Any,
    *,
    run_id: UUID,
    value: Mapping[str, object],
) -> None:
    snapshot = value["snapshot"]
    phase = str(value["phase"])
    call_key = str(value["call_key"])
    from twobrain_rec_server.observability.langfuse import deterministic_observation_scope

    linked_prompt = client.get_prompt(
        snapshot.name,
        version=snapshot.version,
        type=snapshot.prompt_type,
        cache_ttl_seconds=60,
        max_retries=0,
        fetch_timeout_seconds=10,
    )
    usage_details = {
        str(key): value
        for key, value in (value.get("token_usage") or {}).items()
        if isinstance(value, int) and not isinstance(value, bool)
    }
    cost_details = {
        str(key): float(item)
        for key, item in (value.get("cost_details") or {}).items()
        if isinstance(item, (int, float)) and not isinstance(item, bool)
    }

    with deterministic_observation_scope(
        trace_id=optimization_trace_id(run_id),
        observation_id=sha256(call_key.encode()).digest()[:8].hex(),
    ):
        observation = client.start_observation(
            name=f"prompt-optimization-{phase}",
            as_type="generation",
            input=value["request"],
            output={
                "raw_response": value["raw_response"],
                "validated_result": value["validated_result"],
            },
            metadata={
                "run_id": str(run_id),
                "call_key": call_key,
                "phase": phase,
                "prompt_name": snapshot.name,
                "prompt_version": snapshot.version,
                "actual_model": value.get("actual_model"),
                "actual_provider": value.get("actual_provider"),
                "config_hash": prompt_config_hash(snapshot.config),
                "optimizer_version": OPTIMIZER_VERSION,
            },
            model=str(value.get("actual_model") or snapshot.model),
            model_parameters={
                "temperature": snapshot.config["temperature"],
                "max_completion_tokens": snapshot.config["max_completion_tokens"],
            },
            prompt=linked_prompt,
            usage_details=usage_details or None,
            cost_details=cost_details or None,
        )
        observation.end()
    client.flush()


def _publish_optimization_terminal_observation(
    client: Any,
    *,
    run_id: UUID,
    terminal: Mapping[str, object],
) -> None:
    from twobrain_rec_server.observability.langfuse import deterministic_observation_scope

    status = str(terminal["status"])
    if status not in {"rejected", "expired", "failed", "cancelled", "completed"}:
        raise PromptOptimizationError("optimization_terminal_status_invalid")
    with deterministic_observation_scope(
        trace_id=optimization_trace_id(run_id),
        observation_id=optimization_terminal_observation_id(run_id),
    ):
        observation = client.start_observation(
            name="prompt-optimization-terminal",
            as_type="span",
            input={"run_id": str(run_id)},
            output=dict(terminal),
            metadata={
                "run_id": str(run_id),
                "status": status,
                "terminal": True,
            },
        )
        observation.end()
    client.flush()


def _publish_label_transition(
    client: Any,
    *,
    trace_id: str,
    run_id: UUID,
    operation: Literal["promotion", "rollback"],
    from_version: int | None,
    to_version: int,
    linked_trace_id: str | None = None,
) -> None:
    value = {
        "run_id": str(run_id),
        "operation": operation,
        "from_version": from_version,
        "to_version": to_version,
        "linked_trace_id": linked_trace_id,
    }
    from twobrain_rec_server.observability.langfuse import deterministic_observation_scope

    with deterministic_observation_scope(
        trace_id=trace_id,
        observation_id=sha256(f"{operation}/{run_id}/{to_version}".encode()).digest()[:8].hex(),
    ):
        observation = client.start_observation(
            name=f"prompt-{operation}",
            as_type="span",
            input=value,
            output={"status": "verified", **value},
            metadata=value,
        )
        observation.end()
    client.flush()
