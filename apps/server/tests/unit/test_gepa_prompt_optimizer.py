from __future__ import annotations

import asyncio
import json
import threading
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import UUID, uuid4

import pytest

from twobrain_rec_server.cli.langfuse_prompts import desired_prompts
from twobrain_rec_server.outcomes.prompt_optimization import (
    OPTIMIZATION_HISTORY_MAX_BYTES,
    CallReservation,
    DurableCheckpointCallback,
    ModelCall,
    OptimizationBudget,
    PinnedOptimizationContract,
    PromptOptimizationAdapter,
    PromptOptimizationError,
    SyntheticExample,
    SyntheticManifest,
    _run_thread_until_quiescent,
    _schedule_activity_heartbeat,
    calibrate_judge,
    pack_gepa_checkpoint,
    persist_prompt_optimization_history,
    restore_gepa_checkpoint,
    task_model_variables,
    validate_disjoint_manifests,
    validate_heldout_prompt_candidate_activity,
)
from twobrain_rec_server.outcomes.prompts import (
    JUDGE_VARIABLES,
    canonical_json,
    validate_prompt_snapshot,
)
from twobrain_rec_server.outcomes.templates import OUTCOME_CATEGORIES

RUN_ID = UUID("10000000-0000-0000-0000-000000000001")
NOW = datetime(2026, 7, 22, tzinfo=UTC)


@dataclass
class _LedgerRow:
    reservation: CallReservation
    lease_expires_at: datetime
    actual_tokens: int | None = None
    actual_cost: Decimal | None = None


class _FakeLedger:
    def __init__(self, *, lease_seconds: int = 60) -> None:
        self.lease_seconds = lease_seconds
        self._rows: dict[str, _LedgerRow] = {}
        self.expired_calls = 0
        self.expired_tokens = 0
        self.expired_cost = Decimal(0)

    def reserve(self, *, call_key, phase, activity_attempt, now, token_ceiling, cost_ceiling):
        current = self._rows.get(call_key)
        if current and current.reservation.status == "succeeded":
            return current.reservation
        if current and current.lease_expires_at > now:
            raise PromptOptimizationError("optimization_call_in_flight")
        if current:
            self.expired_calls += 1
            self.expired_tokens += current.reservation.reserved_tokens
            self.expired_cost += current.reservation.reserved_cost
        reservation = CallReservation(
            call_key=call_key,
            phase=phase,
            fence=uuid4(),
            status="reserved",
            reserved_tokens=token_ceiling,
            reserved_cost=cost_ceiling,
        )
        self._rows[call_key] = _LedgerRow(
            reservation=reservation,
            lease_expires_at=now + timedelta(seconds=self.lease_seconds),
        )
        return reservation

    def succeed(self, *, call_key, fence, result, actual_tokens, actual_cost) -> None:
        row = self._reserved(call_key, fence)
        row.reservation = CallReservation(
            call_key=call_key,
            phase=row.reservation.phase,
            fence=fence,
            status="succeeded",
            reserved_tokens=row.reservation.reserved_tokens,
            reserved_cost=row.reservation.reserved_cost,
            result=result,
        )
        row.actual_tokens = actual_tokens
        row.actual_cost = actual_cost

    def fail(self, *, call_key, fence) -> None:
        row = self._reserved(call_key, fence)
        row.reservation = CallReservation(
            call_key=call_key,
            phase=row.reservation.phase,
            fence=fence,
            status="ambiguous",
            reserved_tokens=row.reservation.reserved_tokens,
            reserved_cost=row.reservation.reserved_cost,
        )

    def charged_totals(self) -> tuple[int, int, Decimal]:
        charged = [row for row in self._rows.values() if row.reservation.status != "reserved"]
        tokens = self.expired_tokens + sum(
            row.actual_tokens
            if row.reservation.status == "succeeded" and row.actual_tokens is not None
            else row.reservation.reserved_tokens
            for row in charged
        )
        cost = self.expired_cost + sum(
            row.actual_cost
            if row.reservation.status == "succeeded" and row.actual_cost is not None
            else row.reservation.reserved_cost
            for row in charged
        )
        return self.expired_calls + len(charged), tokens, cost

    def _reserved(self, call_key: str, fence: UUID) -> _LedgerRow:
        row = self._rows.get(call_key)
        if not row or row.reservation.fence != fence or row.reservation.status != "reserved":
            raise PromptOptimizationError("optimization_activity_fenced")
        return row


@pytest.mark.anyio
async def test_worker_thread_heartbeat_is_scheduled_on_activity_loop() -> None:
    loop = asyncio.get_running_loop()
    delivered = asyncio.Event()
    heartbeats: list[dict[str, object]] = []

    def heartbeat(details: object) -> None:
        assert isinstance(details, dict)
        heartbeats.append(details)
        delivered.set()

    await asyncio.to_thread(
        _schedule_activity_heartbeat,
        loop,
        heartbeat,
        {"phase": "checkpoint", "revision": 4},
    )
    await asyncio.wait_for(delivered.wait(), timeout=1)

    assert heartbeats == [{"phase": "checkpoint", "revision": 4}]


@pytest.mark.anyio
async def test_cancelled_worker_thread_quiesces_before_terminal_cleanup_or_purge() -> None:
    started = threading.Event()
    release = threading.Event()
    stop_requested = threading.Event()
    late_writes: list[str] = []
    terminal_events: list[str] = []
    purge_events: list[str] = []

    def blocked_model_or_checkpoint() -> None:
        started.set()
        assert release.wait(timeout=2)
        if not stop_requested.is_set():
            late_writes.append("write-after-cancel")

    def signal_stop_with_failed_marker_write() -> None:
        stop_requested.set()
        # A failed `gepa.stop` marker write must not let Temporal acknowledge
        # cancellation before the already-running thread reaches quiescence.
        raise OSError("stop marker unavailable")

    async def activity_then_terminal_cleanup() -> None:
        try:
            await _run_thread_until_quiescent(
                blocked_model_or_checkpoint,
                on_cancel=signal_stop_with_failed_marker_write,
            )
        except asyncio.CancelledError:
            # This models the workflow's terminal finalizer and the now-eligible
            # purge. Neither boundary may run while the activity thread is live.
            terminal_events.append("cancelled")
            purge_events.append("eligible")
            raise

    task = asyncio.create_task(activity_then_terminal_cleanup())
    assert await asyncio.to_thread(started.wait, 1)
    task.cancel()
    await asyncio.sleep(0)

    assert stop_requested.is_set()
    assert not task.done()
    assert terminal_events == []
    assert purge_events == []

    release.set()
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(task, timeout=1)

    assert terminal_events == ["cancelled"]
    assert purge_events == ["eligible"]
    assert late_writes == []


def test_model_result_returned_after_cancel_is_fenced_before_observation() -> None:
    cancelled = [False]
    observations: list[dict[str, object]] = []
    ledger = _FakeLedger()

    def executor(**_kwargs) -> ModelCall:
        cancelled[0] = True
        return ModelCall(
            request={"model": "blocked-provider"},
            raw_response={"late": True},
            validated_result={},
            input_tokens=1,
            output_tokens=1,
            cost=Decimal("0.01"),
        )

    adapter = PromptOptimizationAdapter(
        run_id=RUN_ID,
        contract=_contract(),
        ledger=ledger,
        executor=executor,
        observer=lambda **value: observations.append(value),
        budget=OptimizationBudget(
            max_calls=20,
            max_tokens=1000,
            max_cost=Decimal("10"),
            deadline_at=NOW + timedelta(hours=1),
        ),
        calibrations={
            name: calibrate_judge(
                prompt_name=name,
                expected=["pass", "fail"],
                actual=["pass", "fail"],
                threshold=0.9,
                operator_approved=True,
            )
            for name in JUDGE_VARIABLES
        },
        now=lambda: NOW,
        cancelled=lambda: cancelled[0],
    )

    with pytest.raises(PromptOptimizationError, match="optimization_cancelled"):
        adapter._call(
            phase="task",
            snapshot=adapter.contract.source,
            prompt_text=canonical_json(adapter.contract.source.prompt),
            variables=task_model_variables(_example("train").transcript_json),
            example_id="cancelled-provider-call",
        )

    assert observations == []
    assert {row.reservation.status for row in ledger._rows.values()} == {"ambiguous"}


def _snapshot(name: str):
    prompt_type, prompt, config = desired_prompts()[name]
    return validate_prompt_snapshot(
        name=name,
        version=1,
        prompt_type=prompt_type,
        prompt=prompt,
        config=config,
    )


def _contract() -> PinnedOptimizationContract:
    return PinnedOptimizationContract(
        source=_snapshot("graf/meeting-outcome/auto"),
        reflection=_snapshot("graf/prompt-optimization/reflection"),
        judges={name: _snapshot(name) for name in JUDGE_VARIABLES},
    )


def _example(split: str) -> SyntheticExample:
    return SyntheticExample(
        id=f"{split}-1",
        transcript_json='[{"text":"Synthetic only"}]',
        segment_ids=frozenset(),
        required_categories=tuple(OUTCOME_CATEGORIES),
    )


def test_synthetic_splits_are_immutable_disjoint_and_checkpoints_are_verified() -> None:
    train = SyntheticManifest.create(
        ref="synthetic://suite/v1/train", split="train", version="v1", examples=[_example("train")]
    )
    development = SyntheticManifest.create(
        ref="synthetic://suite/v1/dev",
        split="development",
        version="v1",
        examples=[_example("dev")],
    )
    heldout = SyntheticManifest.create(
        ref="synthetic://suite/v1/heldout",
        split="heldout",
        version="v1",
        examples=[_example("heldout")],
    )
    validate_disjoint_manifests(train, development, heldout)
    hashes = {item.split: item.sha256 for item in (train, development, heldout)}
    with TemporaryDirectory() as source_dir, TemporaryDirectory() as target_dir:
        state_path = Path(source_dir) / "gepa_state.bin"
        state_path.write_bytes(b"server-generated-gepa-state")
        archive_key, archive, archive_hash = pack_gepa_checkpoint(
            run_id=RUN_ID,
            revision=1,
            run_dir=source_dir,
            manifest_hashes=hashes,
        )
        restore_gepa_checkpoint(
            run_id=RUN_ID,
            key=archive_key,
            payload=archive,
            expected_hash=archive_hash,
            manifest_hashes=hashes,
            run_dir=target_dir,
        )
        assert (Path(target_dir) / "gepa_state.bin").read_bytes() == state_path.read_bytes()


def test_fenced_ledger_reuses_success_and_charges_expired_ambiguity() -> None:
    ledger = _FakeLedger(lease_seconds=1)
    first = ledger.reserve(
        call_key="call",
        phase="task",
        activity_attempt=1,
        now=NOW,
        token_ceiling=100,
        cost_ceiling=Decimal("1"),
    )
    second = ledger.reserve(
        call_key="call",
        phase="task",
        activity_attempt=2,
        now=NOW + timedelta(seconds=2),
        token_ceiling=100,
        cost_ceiling=Decimal("1"),
    )
    with pytest.raises(PromptOptimizationError, match="optimization_activity_fenced"):
        ledger.succeed(
            call_key="call",
            fence=first.fence,
            result="stale",
            actual_tokens=1,
            actual_cost=Decimal("0.1"),
        )
    result = ModelCall(request={}, raw_response={}, validated_result={})
    ledger.succeed(
        call_key="call",
        fence=second.fence,
        result=result,
        actual_tokens=10,
        actual_cost=Decimal("0.1"),
    )
    reused = ledger.reserve(
        call_key="call",
        phase="task",
        activity_attempt=3,
        now=NOW + timedelta(seconds=3),
        token_ceiling=100,
        cost_ceiling=Decimal("1"),
    )
    assert reused.result is result
    assert ledger.charged_totals() == (2, 110, Decimal("1.1"))


def test_adapter_uses_strict_shared_validation_and_content_observations() -> None:
    calls: list[dict[str, object]] = []

    def executor(**kwargs):
        if kwargs["phase"] == "task":
            result = {
                "category_states": {category: "not_found" for category in OUTCOME_CATEGORIES},
                "items": [],
            }
        elif kwargs["phase"] == "reflection":
            result = f"```{canonical_json(_contract().source.prompt)}```"
        else:
            result = {"score": 1, "verdict": "pass", "feedback": "supported"}
        return ModelCall(
            request={"variables": dict(kwargs["variables"])},
            raw_response={"content": result},
            validated_result=result,
            input_tokens=1,
            output_tokens=1,
            cost=Decimal("0.01"),
            actual_model="provider/model-v2",
            actual_provider="provider",
            token_usage={"input": 1, "output": 1},
            cost_details={"total": 0.01},
        )

    adapter = PromptOptimizationAdapter(
        run_id=RUN_ID,
        contract=_contract(),
        ledger=_FakeLedger(),
        executor=executor,
        observer=lambda **value: calls.append(value),
        budget=OptimizationBudget(
            max_calls=20,
            max_tokens=1000,
            max_cost=Decimal("10"),
            deadline_at=NOW + timedelta(hours=1),
        ),
        calibrations={
            name: calibrate_judge(
                prompt_name=name,
                expected=["pass", "fail"],
                actual=["pass", "fail"],
                threshold=0.9,
                operator_approved=True,
            )
            for name in JUDGE_VARIABLES
        },
        now=lambda: NOW,
    )
    evaluation = adapter.evaluate(
        [_example("train")],
        {"outcome_prompt": canonical_json(_contract().source.prompt)},
        capture_traces=True,
    )
    assert evaluation.scores == [1.0]
    assert len(calls) == 4
    assert all(call["request"] and call["raw_response"] for call in calls)
    assert all(call["actual_model"] == "provider/model-v2" for call in calls)
    assert all(call["actual_provider"] == "provider" for call in calls)
    assert all(call["token_usage"] == {"input": 1, "output": 1} for call in calls)
    proposal = adapter.propose_new_texts(
        {"outcome_prompt": canonical_json(_contract().source.prompt)},
        adapter.make_reflective_dataset(
            {"outcome_prompt": canonical_json(_contract().source.prompt)},
            evaluation,
            ["outcome_prompt"],
        ),
        ["outcome_prompt"],
    )
    assert proposal["outcome_prompt"] == canonical_json(_contract().source.prompt)


def test_adapter_does_not_reuse_judges_when_candidate_output_changes() -> None:
    contract = _contract()
    candidate_a = canonical_json(contract.source.prompt)
    candidate_b_value = [dict(message) for message in contract.source.prompt]
    candidate_b_value[0]["content"] += " Candidate B."
    candidate_b = canonical_json(candidate_b_value)
    executed_phases: list[str] = []
    observed_keys: list[str] = []

    def executor(**kwargs):
        phase = kwargs["phase"]
        executed_phases.append(phase)
        if phase == "task":
            state = "not_inferable" if "Candidate B." in kwargs["prompt_text"] else "not_found"
            result = {
                "category_states": {
                    category: state if category == "summary" else "not_found"
                    for category in OUTCOME_CATEGORIES
                },
                "items": [],
            }
        else:
            changed = "not_inferable" in kwargs["variables"]["candidate_outcome_json"]
            result = {
                "score": 0 if changed else 1,
                "verdict": "fail" if changed else "pass",
                "feedback": "changed" if changed else "supported",
            }
        return ModelCall(
            request={},
            raw_response={},
            validated_result=result,
            input_tokens=1,
            output_tokens=1,
            cost=Decimal("0.01"),
        )

    adapter = PromptOptimizationAdapter(
        run_id=RUN_ID,
        contract=contract,
        ledger=_FakeLedger(),
        executor=executor,
        observer=lambda **value: observed_keys.append(str(value["call_key"])),
        budget=OptimizationBudget(
            max_calls=20,
            max_tokens=100_000,
            max_cost=Decimal("10"),
            deadline_at=NOW + timedelta(hours=1),
        ),
        calibrations={
            name: calibrate_judge(
                prompt_name=name,
                expected=["pass", "fail"],
                actual=["pass", "fail"],
                threshold=0.9,
                operator_approved=True,
            )
            for name in JUDGE_VARIABLES
        },
        now=lambda: NOW,
    )

    first = adapter.evaluate([_example("train")], {"outcome_prompt": candidate_a})
    second = adapter.evaluate([_example("train")], {"outcome_prompt": candidate_b})

    assert first.scores == [1.0]
    assert second.scores == [0.0]
    assert len(executed_phases) == 8
    assert len(set(observed_keys)) == 8


def test_task_call_resume_key_includes_every_effective_projected_variable() -> None:
    executions: list[dict[str, str]] = []

    def executor(**kwargs):
        executions.append(dict(kwargs["variables"]))
        return ModelCall(
            request={"variables": dict(kwargs["variables"])},
            raw_response={},
            validated_result={},
            input_tokens=1,
            output_tokens=1,
            cost=Decimal("0.01"),
        )

    contract = _contract()
    adapter = PromptOptimizationAdapter(
        run_id=RUN_ID,
        contract=contract,
        ledger=_FakeLedger(),
        executor=executor,
        observer=lambda **_value: None,
        budget=OptimizationBudget(
            max_calls=20,
            max_tokens=100_000,
            max_cost=Decimal("10"),
            deadline_at=NOW + timedelta(hours=1),
        ),
        calibrations={
            name: calibrate_judge(
                prompt_name=name,
                expected=["pass", "fail"],
                actual=["pass", "fail"],
                threshold=0.9,
                operator_approved=True,
            )
            for name in JUDGE_VARIABLES
        },
        now=lambda: NOW,
    )
    prompt_text = canonical_json(contract.source.prompt)
    russian = task_model_variables('[{"text":"Synthetic only"}]')
    english = {**russian, "output_language": "en"}

    adapter._call(
        phase="task",
        snapshot=contract.source,
        prompt_text=prompt_text,
        variables=russian,
        example_id="resume-1",
    )
    adapter._call(
        phase="task",
        snapshot=contract.source,
        prompt_text=prompt_text,
        variables=english,
        example_id="resume-1",
    )
    adapter._call(
        phase="task",
        snapshot=contract.source,
        prompt_text=prompt_text,
        variables=russian,
        example_id="resume-1",
    )

    assert executions == [russian, english]


def test_durable_checkpoint_callback_uses_each_gepa_state_save_boundary() -> None:
    persisted: list[tuple[str, int]] = []
    callback = DurableCheckpointCallback(
        lambda run_dir, iteration: persisted.append((run_dir, iteration))
    )

    callback.on_state_saved({"run_dir": "/tmp/synthetic-gepa", "iteration": 4})

    assert persisted == [("/tmp/synthetic-gepa", 4)]


def test_temporal_history_chunks_retain_complete_plaintext_synthetic_content() -> None:
    objects: dict[str, bytes] = {}

    class Storage:
        def put_stream(self, key, stream, length) -> None:
            payload = stream.read()
            assert len(payload) == length
            objects[key] = payload

    manifest = SyntheticManifest.create(
        ref="synthetic://suite/v1/train",
        split="train",
        version="v1",
        examples=[_example("train")],
    )
    observation = {
        "actual_model": "provider/model-v2",
        "actual_provider": "provider",
        "call_key": "call-key",
        "cost_details": {"total": 0.01},
        "phase": "task",
        "raw_response": {"content": "full synthetic response"},
        "request": {"messages": [{"content": "full synthetic request"}]},
        "snapshot": _contract().source,
        "token_usage": {"input_tokens": 4, "output_tokens": 3},
        "validated_result": {"items": []},
    }

    descriptor = persist_prompt_optimization_history(
        Storage(),
        run_id=RUN_ID,
        phase="evolution",
        datasets=(manifest,),
        observations=(observation,),
        optimizer_state={"candidates": ["complete candidate"], "iteration": 3},
    )

    plaintext = "".join(
        json.loads(objects[item["key"]])["transcript_utf8"]
        for item in descriptor["chunks"]
    )
    restored = json.loads(plaintext)
    assert restored["datasets"][0]["examples"][0]["transcript_json"] == (
        '[{"text":"Synthetic only"}]'
    )
    assert restored["model_calls"][0]["request"] == observation["request"]
    assert restored["model_calls"][0]["raw_response"] == observation["raw_response"]
    assert restored["optimizer_state"]["candidates"] == ["complete candidate"]


def test_temporal_history_fails_closed_above_fixed_snapshot_ceiling() -> None:
    class Storage:
        def put_stream(self, *_args) -> None:
            raise AssertionError("oversized history must fail before storage")

    with pytest.raises(PromptOptimizationError, match="optimization_history_oversize"):
        persist_prompt_optimization_history(
            Storage(),
            run_id=RUN_ID,
            phase="evolution",
            datasets=(),
            observations=(),
            optimizer_state={"oversized": "x" * (OPTIMIZATION_HISTORY_MAX_BYTES + 1)},
        )


def test_heldout_history_excludes_evolution_calls_near_snapshot_ceiling() -> None:
    import inspect

    class Storage:
        def put_stream(self, _key, stream, length) -> None:
            assert len(stream.read()) == length

    base_observation = {
        "actual_model": "provider/model-v2",
        "actual_provider": "provider",
        "cost_details": {"total": 0.01},
        "phase": "task",
        "request": {"messages": [{"content": "heldout"}]},
        "snapshot": _contract().source,
        "token_usage": {"input_tokens": 4, "output_tokens": 3},
        "validated_result": {"items": []},
    }
    heldout_call = {
        **base_observation,
        "call_key": "heldout-call",
        "raw_response": {"content": "heldout response"},
    }
    evolution_calls = tuple(
        {
            **base_observation,
            "call_key": f"evolution-{index}",
            "raw_response": {"content": "e" * 20_000},
        }
        for index in range(20)
    )
    optimizer_state = {
        "near_ceiling": "x" * (OPTIMIZATION_HISTORY_MAX_BYTES - 262_144)
    }

    persist_prompt_optimization_history(
        Storage(),
        run_id=RUN_ID,
        phase="heldout",
        datasets=(),
        observations=(heldout_call,),
        optimizer_state=optimizer_state,
    )
    with pytest.raises(PromptOptimizationError, match="optimization_history_oversize"):
        persist_prompt_optimization_history(
            Storage(),
            run_id=RUN_ID,
            phase="heldout",
            datasets=(),
            observations=(*evolution_calls, heldout_call),
            optimizer_state=optimizer_state,
        )

    source = inspect.getsource(validate_heldout_prompt_candidate_activity)
    assert "history_observations(call_keys=observed_call_keys)" in source
