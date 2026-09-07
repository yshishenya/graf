"""Isolated PostgreSQL regressions for optimizer inference and delivery fences."""

import asyncio
import json
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest

from tests.fixtures.meeting_protocol import extraction_result, protocol_result
from tests.fixtures.prompt_optimization import (
    ReceiptStorage,
    SyntheticLangfuse,
    maintenance_factory,
)
from tests.unit.test_gepa_prompt_optimizer import _contract, _example, _synthetic_segments
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import PromptOptimizationCallLedger, PromptOptimizationRun
from twobrain_rec_server.outcomes import prompt_optimization as optimizer
from twobrain_rec_server.outcomes.prompts import canonical_json


def synthetic_run():
    return PromptOptimizationRun(
        id=uuid4(), initiated_by_actor_id="synthetic-operator", prompt_name="graf/meeting-outcome/auto",
        source_prompt_version=1, source_config_hash="a" * 64,
        train_dataset_ref="synthetic://train", development_dataset_ref="synthetic://dev",
        heldout_dataset_ref="synthetic://heldout", optimizer_version="synthetic", adapter_version="synthetic",
        reflection_prompt_name="graf/prompt-optimization/reflection", reflection_prompt_version=1,
        reflection_config_hash="b" * 64, budget={"max_calls": 100, "max_tokens": 100000, "max_cost": "100"},
        deadline_at=datetime.now(UTC) + timedelta(hours=1), workflow_id=str(uuid4()),
        rollback_prompt_version=1, status="running",
    )


@pytest.mark.parametrize("phase", optimizer.CALL_PHASES)
def test_expired_reservation_is_persisted_ambiguous_never_replaced(client, phase):
    async def run_test():
        sessions = client.app_state["sessionmaker"]
        run = synthetic_run()
        now = datetime.now(UTC)
        args = dict(run_id=run.id, call_key="a" * 64, phase=phase, prompt_version=1,
                    config_hash="b" * 64, model_route="synthetic", token_ceiling=100,
                    cost_ceiling=Decimal("1"), activity_attempt=1, now=now, lease_seconds=1)
        async with sessions() as db:
            db.add(run)
            await db.commit()
            first = await optimizer.reserve_persisted_call(db, **args)
            await db.commit()
        async with sessions() as db:
            second = await optimizer.reserve_persisted_call(db, **{**args, "now": now + timedelta(seconds=2)})
            await db.commit()
        assert second.status == "ambiguous"
        assert second.fence == first.fence
        async with sessions() as db:
            row = await db.get(PromptOptimizationCallLedger, (run.id, args["call_key"]))
            assert row.status == "ambiguous" and row.activity_fence == first.fence
            third = await optimizer.reserve_persisted_call(db, **{**args, "now": now + timedelta(seconds=3)})
            assert third.status == "ambiguous" and third.fence == first.fence
    asyncio.run(run_test())


@pytest.fixture
def delivery_case(client, monkeypatch, tmp_path):
    from twobrain_rec_server.db import session

    sessions = client.app_state["sessionmaker"]
    factory = maintenance_factory(sessions)
    monkeypatch.setattr(session, "create_prompt_optimization_database", factory)
    key = tmp_path / "synthetic-key"
    key.write_text("synthetic-only")
    settings = Settings(
        langfuse_project_id="synthetic-project", prompt_optimization_enabled=True,
        temporal_address="synthetic.invalid:7233", litellm_base_url="https://synthetic.invalid",
        litellm_api_key_file=key, langfuse_base_url="https://synthetic.invalid",
        langfuse_public_key_file=key, langfuse_secret_key_file=key,
        prompt_optimization_database_url=sessions.kw["bind"].url.set(username="twobrain_rec_maintenance").render_as_string(hide_password=False),
        prompt_optimization_postgres_password_file=key,
    )
    run = synthetic_run()

    async def setup():
        async with sessions() as db:
            db.add(run)
            await db.commit()
    asyncio.run(setup())
    contract = _contract()
    storage = ReceiptStorage(tmp_path)
    langfuse = SyntheticLangfuse(contract)
    ledger = optimizer._PersistentLedgerBridge(settings=settings, run_id=run.id, storage=storage, contract=contract)
    yield SimpleNamespace(ledger=ledger, sessions=sessions, settings=settings, run=run,
                          storage=storage, langfuse=langfuse, contract=contract, factory=factory)
    langfuse.http.close()


def reserve(case, *, now=None, call_key="a" * 64, phase="task"):
    return case.ledger.reserve(call_key=call_key, phase=phase, activity_attempt=1,
                               now=now or datetime.now(UTC), token_ceiling=100, cost_ceiling=Decimal("1"))


def succeed(case):
    reservation = reserve(case)
    call = optimizer.ModelCall(
        request={"model": case.contract.source.model, "messages": [{"role": "user", "content": "Synthetic only"}]},
        raw_response={"choices": []}, validated_result=protocol_result(_synthetic_segments()),
        input_tokens=1, output_tokens=1, actual_model="actual/synthetic",
    )
    case.ledger.succeed(call_key=reservation.call_key, fence=reservation.fence, result=call,
                        actual_tokens=2, actual_cost=None)
    return reservation, call


def publish(case, reservation):
    case.ledger.publish_observation(case.langfuse, call_key=reservation.call_key, fence=reservation.fence)


def checkpoint(case, reservation):
    return json.loads(case.storage.get_bytes(case.ledger._observation_key(reservation.call_key, reservation.fence)))


def row_state(case, reservation):
    async def read():
        async with case.sessions() as db:
            return await db.get(PromptOptimizationCallLedger, (case.run.id, reservation.call_key))
    return asyncio.run(read())


def test_bridge_commits_expired_ambiguity_before_raising(delivery_case):
    case = delivery_case
    now = datetime.now(UTC)
    first = reserve(case, now=now)
    with pytest.raises(optimizer.PromptOptimizationError, match="optimization_call_ambiguous"):
        reserve(case, now=now + timedelta(minutes=3))
    row = row_state(case, first)
    assert row.status == "ambiguous" and row.activity_fence == first.fence
    assert not case.storage.events and not case.langfuse.sent


def test_pending_to_ambiguous_is_read_back_before_send_then_exact_sdk_confirmation(delivery_case):
    case = delivery_case
    first, _ = succeed(case)
    case.langfuse.before_send = lambda: _assert_state(case, first, "ambiguous")
    publish(case, first)
    assert checkpoint(case, first)["state"] == "confirmed"
    assert len(case.langfuse.sent) == len(case.langfuse.reads) == 1
    before = list(case.storage.events)
    case.ledger.contract = None  # observation-only historical replay never asks for a root
    publish(case, first)
    assert len(case.langfuse.sent) == len(case.langfuse.reads) == 1
    assert all(event[0] == "read" for event in case.storage.events[len(before):])


def _assert_state(case, reservation, state):
    assert checkpoint(case, reservation)["state"] == state


def test_flush_without_visibility_does_not_confirm_or_resend(delivery_case):
    case = delivery_case
    first, _ = succeed(case)
    case.langfuse.visible = False
    for _ in range(2):
        with pytest.raises(optimizer.PromptOptimizationError, match="optimization_observation_unconfirmed"):
            publish(case, first)
        assert checkpoint(case, first)["state"] == "ambiguous"
    assert len(case.langfuse.sent) == 1
    case.langfuse.visible = True
    case.ledger.contract = None
    case.langfuse.preflight_error = AssertionError("replay must not fetch a prompt")
    publish(case, first)
    assert checkpoint(case, first)["state"] == "confirmed"
    assert len(case.langfuse.sent) == 1


@pytest.mark.parametrize("failure", ["preflight_error", "send_error", "flush_error"])
def test_known_preflight_failure_vs_ambiguous_emission(delivery_case, failure):
    case = delivery_case
    first, _ = succeed(case)
    setattr(case.langfuse, failure, RuntimeError("synthetic private error"))
    with pytest.raises(optimizer.PromptOptimizationError, match="^optimization_observation_unresolved$"):
        publish(case, first)
    assert checkpoint(case, first)["state"] == ("pending" if failure == "preflight_error" else "ambiguous")
    setattr(case.langfuse, failure, None)
    publish(case, first)
    assert checkpoint(case, first)["state"] == "confirmed"
    assert len(case.langfuse.sent) == 1


@pytest.mark.parametrize("failure", ["before_put", "after_put", "after_read"])
def test_uncertain_checkpoint_storage_never_sends(delivery_case, failure):
    case = delivery_case
    first, _ = succeed(case)

    def fail(key, value):
        if key.endswith(".observation.json") and json.loads(value)["state"] == "ambiguous":
            raise OSError("synthetic storage uncertainty")
    setattr(case.storage, failure, fail)
    with pytest.raises(optimizer.PromptOptimizationError, match="optimization_observation_unresolved"):
        publish(case, first)
    assert not case.langfuse.sent
    setattr(case.storage, failure, lambda *_: None)
    if checkpoint(case, first)["state"] == "ambiguous":
        with pytest.raises(optimizer.PromptOptimizationError, match="unconfirmed"):
            publish(case, first)
        assert not case.langfuse.sent


@pytest.mark.parametrize("field", ["run_id", "call_key", "fence", "receipt_sha256", "trace_id", "observation_id", "schema_version", "extra", "state"])
def test_checkpoint_binding_and_schema_are_closed(delivery_case, field):
    case = delivery_case
    first, _ = succeed(case)
    value = checkpoint(case, first)
    value[field] = True if field == "schema_version" else "tampered"
    case.storage.replace(case.ledger._observation_key(first.call_key, first.fence), canonical_json(value).encode())
    with pytest.raises(optimizer.PromptOptimizationError, match="checkpoint_invalid"):
        publish(case, first)
    assert not case.langfuse.sent


def test_receipt_digest_is_anchored_in_ledger_and_succeeded_receipt_is_immutable(delivery_case):
    case = delivery_case
    first, call = succeed(case)
    row = row_state(case, first)
    original = case.storage.get_bytes(row.result_artifact_ref)
    with pytest.raises(optimizer.PromptOptimizationError, match="activity_fenced"):
        case.ledger.succeed(call_key=first.call_key, fence=first.fence,
                           result=replace(call, validated_result={"changed": True}), actual_tokens=2, actual_cost=None)
    assert case.storage.get_bytes(row.result_artifact_ref) == original
    case.storage.replace(row.result_artifact_ref, original + b" ")
    with pytest.raises(optimizer.PromptOptimizationError, match="receipt_hash_mismatch"):
        publish(case, first)
    assert not case.langfuse.sent


@pytest.mark.parametrize("stage", ["pending", "confirm"])
def test_stale_fence_cannot_change_checkpoint(delivery_case, stage):
    case = delivery_case
    first, _ = succeed(case)

    def replace_fence():
        async def update():
            async with case.sessions() as db:
                row = await db.get(PromptOptimizationCallLedger, (case.run.id, first.call_key))
                row.activity_fence = uuid4()
                await db.commit()
        asyncio.run(update())
    if stage == "pending":
        replace_fence()
    else:
        case.langfuse.before_read = replace_fence
    with pytest.raises(optimizer.PromptOptimizationError, match="activity_fenced"):
        publish(case, first)
    assert checkpoint(case, first)["state"] == ("pending" if stage == "pending" else "ambiguous")


def test_checkpoint_transition_lock_serializes_readers_and_writers(delivery_case):
    case = delivery_case
    first, _ = succeed(case)
    blocked, release, second_started = threading.Event(), threading.Event(), threading.Event()

    def block_write(key, value):
        if key.endswith(".observation.json") and json.loads(value)["state"] == "ambiguous":
            blocked.set()
            assert release.wait(5)
    case.storage.after_put = block_write

    def second():
        second_started.set()
        try:
            publish(case, first)
        except optimizer.PromptOptimizationError as exc:
            assert exc.code == "optimization_observation_unconfirmed"

    with ThreadPoolExecutor(max_workers=2) as pool:
        writer = pool.submit(publish, case, first)
        assert blocked.wait(5)
        events = list(case.storage.events)
        reader = pool.submit(second)
        assert second_started.wait(5)
        try:
            with pytest.raises(TimeoutError):
                reader.result(timeout=0.1)
            assert case.storage.events == events  # not even checkpoint reads may bypass the row lock
        finally:
            release.set()
        writer.result(timeout=5)
        reader.result(timeout=5)
    assert len(case.langfuse.sent) == 1
    assert checkpoint(case, first)["state"] == "confirmed"


def test_historical_succeeded_without_checkpoint_is_unresolved_without_root(delivery_case):
    case = delivery_case
    first = reserve(case)
    payload = optimizer._model_call_bytes(optimizer.ModelCall(request={}, raw_response={}, validated_result={}))
    path = f"{optimizer.CHECKPOINT_PREFIX}/{case.run.id}/calls/{first.call_key}/{first.fence}.json"
    case.storage.put_stream(path, BytesIO(payload), len(payload))

    async def finish():
        async with case.sessions() as db:
            await optimizer.complete_persisted_call(db, run_id=case.run.id, call_key=first.call_key,
                fence=first.fence, result_artifact_ref=path, input_tokens=1, output_tokens=1,
                actual_cost=None, now=datetime.now(UTC))
            await db.commit()
    asyncio.run(finish())
    case.ledger.contract = None
    with pytest.raises(optimizer.PromptOptimizationError, match="historical_observation_unresolved"):
        publish(case, first)
    assert not case.langfuse.sent and not case.langfuse.prompt_reads


@pytest.mark.parametrize("field", ["id", "traceId", "projectId", "type", "name", "promptName", "promptVersion", "input", "output", "metadata", "providedModelName", "modelParameters", "endTime"])
def test_confirmation_requires_exact_retained_generation(delivery_case, field):
    case = delivery_case
    first, _ = succeed(case)

    def mutate(row):
        row[field] = None if field == "endTime" else 99 if field == "promptVersion" else {"tampered": True} if field in {"metadata", "modelParameters"} else '"different"'
    case.langfuse.mutate_row = mutate
    with pytest.raises(optimizer.PromptOptimizationError, match="observation_(mismatch|unresolved)"):
        publish(case, first)
    assert checkpoint(case, first)["state"] == "ambiguous"
    assert len(case.langfuse.sent) == 1


@pytest.mark.parametrize("invalid", [None, "sequence", "quote", "uuid"])
def test_real_pinned_extractor_compiler_executor_and_durable_replay(delivery_case, monkeypatch, invalid):
    case = delivery_case
    extraction = extraction_result(_synthetic_segments())
    if invalid == "sequence":
        extraction["facts"][0]["source_refs"][0]["sequence"] = 999
    elif invalid == "quote":
        extraction["facts"][0]["source_refs"][0]["quote"] = "not in source"
    elif invalid == "uuid":
        extraction["facts"][0]["source_refs"][0]["transcript_segment_id"] = str(uuid4())
    outputs = [extraction, protocol_result(_synthetic_segments()), *[
        {"score": 1.0, "verdict": "pass", "feedback": "synthetic supported"} for _ in range(3)
    ]]
    requests = []

    def respond(request):
        requests.append(json.loads(request.content))
        output = outputs[len(requests) - 1]
        return httpx.Response(200, json={"model": "actual/synthetic", "choices": [{
            "finish_reason": "stop", "message": {"content": output if isinstance(output, str) else canonical_json(output)},
        }], "usage": {"prompt_tokens": 10, "completion_tokens": 20}})
    http_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: http_client(
        **kwargs, transport=httpx.MockTransport(respond)))

    def adapter():
        return optimizer.PromptOptimizationAdapter(
            run_id=case.run.id, contract=case.contract, ledger=case.ledger,
            executor=optimizer._ProductionModelExecutor(settings=case.settings),
            observer=lambda **value: case.ledger.publish_observation(
                case.langfuse, call_key=value["call_key"], fence=value["fence"]),
            budget=optimizer.OptimizationBudget(max_calls=100, max_tokens=100000,
                max_cost=Decimal("100"), deadline_at=case.run.deadline_at),
            calibrations={name: optimizer.calibrate_judge(prompt_name=name,
                expected=["pass", "fail"], actual=["pass", "fail"], threshold=1, operator_approved=True)
                for name in optimizer.JUDGE_NAMES},
        )
    candidate = {"outcome_prompt": canonical_json(case.contract.source.prompt)}
    example = _example("durable")
    if invalid:
        for _ in range(2):
            with pytest.raises(ValueError):
                adapter().evaluate([example], candidate)
        assert len(requests) == len(case.langfuse.sent) == 1
        return
    evaluating_adapter = adapter()
    result = evaluating_adapter.evaluate([example], candidate)
    assert result.outputs == [outputs[1]] and result.scores == [1.0]
    assert adapter().evaluate([example], candidate).outputs == result.outputs
    assert len(requests) == len(case.langfuse.sent) == 5
    assert requests[0]["model"] == case.contract.extractor.model
    assert requests[1]["model"] == case.contract.source.model
    assert canonical_json(extraction) in "\n".join(item["content"] for item in requests[1]["messages"])
    for request in requests[:2]:
        text = "\n".join(item["content"] for item in request["messages"])
        assert str(_synthetic_segments()[0].segment_id) in text
        assert _synthetic_segments()[0].text in text
    # A resumed GEPA checkpoint need not repeat earlier evaluations. Its new
    # adapter has no in-memory call counter; reflection identity must still match.
    outputs.extend([f"```\n{candidate['outcome_prompt']}\n```"] * 2)
    reflective = {"outcome_prompt": []}
    case.langfuse.visible = False
    with pytest.raises(optimizer.OptimizationObservationPending):
        evaluating_adapter.propose_new_texts(candidate, reflective, ["outcome_prompt"])
    case.langfuse.visible = True
    proposal = adapter().propose_new_texts(candidate, reflective, ["outcome_prompt"])
    assert proposal == candidate
    assert len(requests) == len(case.langfuse.sent) == 6


@pytest.mark.parametrize("tampered", [False, True])
def test_history_cannot_export_unconfirmed_or_tampered_receipts(delivery_case, tampered):
    case = delivery_case
    first, _ = succeed(case)
    if tampered:
        publish(case, first)
        row = row_state(case, first)
        receipt = json.loads(case.storage.get_bytes(row.result_artifact_ref))
        receipt["raw_response"] = {"tampered": True}
        case.storage.replace(row.result_artifact_ref, canonical_json(receipt).encode())
    with pytest.raises(optimizer.PromptOptimizationError, match="receipt_hash_mismatch|observation_unconfirmed"):
        asyncio.run(case.ledger.history_observations())


@pytest.mark.parametrize("mutation", ["missing_null", "bool_instead_of_int"])
def test_confirmation_metadata_is_exact_including_null_and_types(delivery_case, mutation):
    case = delivery_case
    first, _ = succeed(case)

    def mutate(row):
        if mutation == "missing_null":
            del row["metadata"]["actual_provider"]
        else:
            row["metadata"]["prompt_version"] = True
    case.langfuse.mutate_row = mutate
    with pytest.raises(optimizer.PromptOptimizationError, match="observation_mismatch"):
        publish(case, first)
    assert checkpoint(case, first)["state"] == "ambiguous"


@pytest.mark.parametrize("failure", [404, 503])
def test_confirmation_read_error_never_resends(delivery_case, failure):
    case = delivery_case
    first, _ = succeed(case)
    case.langfuse.read_status = failure
    for _ in range(2):
        with pytest.raises(optimizer.PromptOptimizationError, match="observation_unresolved"):
            publish(case, first)
    assert checkpoint(case, first)["state"] == "ambiguous"
    assert len(case.langfuse.sent) == 1


def test_delivery_cancelled_after_emission_is_observation_only_on_restart(delivery_case):
    case = delivery_case
    first, _ = succeed(case)
    case.langfuse.send_error = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        publish(case, first)
    assert checkpoint(case, first)["state"] == "ambiguous"
    case.ledger = optimizer._PersistentLedgerBridge(settings=case.settings, run_id=case.run.id,
                                                    storage=case.storage, contract=None)
    case.langfuse.send_error = None
    publish(case, first)
    assert checkpoint(case, first)["state"] == "confirmed" and len(case.langfuse.sent) == 1


def test_start_and_resolve_pin_exact_extractor_and_separate_controls(delivery_case, monkeypatch):
    from unittest.mock import AsyncMock

    from tests.fixtures.meeting_protocol import protocol_bundle
    from twobrain_rec_server import config
    from twobrain_rec_server.cli import prompt_optimization as cli
    from twobrain_rec_server.observability import langfuse

    case = delivery_case
    bundle = protocol_bundle()
    monkeypatch.setattr(cli, "fetch_root_bundle_by_label", lambda _: bundle)
    monkeypatch.setattr(cli, "create_langfuse_client", lambda _: case.langfuse)
    monkeypatch.setattr(cli, "shutdown_langfuse", lambda _: None)
    monkeypatch.setattr(cli, "connect_temporal_client", AsyncMock())
    monkeypatch.setattr(cli, "start_prompt_optimization_workflow", AsyncMock(return_value=SimpleNamespace(run_id="synthetic")))
    monkeypatch.setattr(config, "get_settings", lambda: case.settings)
    monkeypatch.setattr(langfuse, "create_langfuse_client", lambda _: case.langfuse)
    monkeypatch.setattr(langfuse, "shutdown_langfuse", lambda _: None)
    args = cli.build_parser().parse_args([
        "start", "--actor-id", "synthetic", "--prompt-name", case.contract.source.name,
        "--max-calls", "100", "--max-tokens", "100000", "--max-cost", "100",
        *[value for split in ("train", "development", "heldout") for value in (
            f"--{split}-ref", f"synthetic://{split}", f"--{split}-hash", "a" * 64, f"--{split}-count", "1")],
    ])

    async def run():
        engine, sessions = case.factory(case.settings)
        try:
            started = await cli._start(args, settings=case.settings, sessionmaker=sessions)
        finally:
            await engine.dispose()
        resolved = await optimizer.resolve_prompt_optimization_contract_activity({"run_id": started["run_id"]})
        pinned = optimizer._contract_from_resolved(resolved)
        assert pinned.extractor.canonical_hash == bundle.child(pinned.extractor.name).canonical_hash
        assert pinned.extractor.root_bundle_hash == pinned.source.root_bundle_hash
        assert pinned.reflection.root_bundle_hash is None
        assert all(snapshot.root_bundle_hash is None for snapshot in pinned.judges.values())
        assert len(optimizer._calibrations_from_resolved(resolved, pinned)) == 3
    asyncio.run(run())


def test_actual_temporal_retry_only_confirms_retained_observation(delivery_case):
    from temporalio import activity
    from temporalio.testing import WorkflowEnvironment
    from temporalio.worker import Worker

    from tests.integration.test_prompt_optimization_replay import RetainedObservationRetryWorkflow

    case = delivery_case
    first, _ = succeed(case)
    attempts = []

    @activity.defn(name="optimizer_retained_observation_activity")
    async def deliver() -> str:
        attempts.append(activity.info().attempt)
        case.langfuse.visible = len(attempts) > 1
        await asyncio.to_thread(publish, case, first)
        return "confirmed"

    async def run():
        async with await WorkflowEnvironment.start_local() as env:
            queue = f"synthetic-delivery-{uuid4()}"
            async with Worker(env.client, task_queue=queue, workflows=[RetainedObservationRetryWorkflow], activities=[deliver]):
                result = await env.client.execute_workflow(RetainedObservationRetryWorkflow.run,
                    id=str(uuid4()), task_queue=queue, execution_timeout=timedelta(seconds=40))
                assert result == "confirmed"
    asyncio.run(run())
    assert attempts == [1, 2]
    assert len(case.langfuse.sent) == 1
    assert checkpoint(case, first)["state"] == "confirmed"
