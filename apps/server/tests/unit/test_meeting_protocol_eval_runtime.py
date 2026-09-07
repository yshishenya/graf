import asyncio
import json
import shutil
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, call
from uuid import uuid4

import pytest
from temporalio.client import WorkflowFailureError
from temporalio.exceptions import ApplicationError, WorkflowAlreadyStartedError
from temporalio.testing import WorkflowEnvironment
from temporalio.worker import Worker as TemporalWorker

from tests.fixtures.meeting_protocol import pin_protocol_prompts
from twobrain_rec_server.cli import meeting_protocol_eval as evaluator
from twobrain_rec_server.cli import meeting_protocol_eval_runtime as runtime
from twobrain_rec_server.cli.meeting_protocol_eval_runtime import (
    EvaluationActivities,
    verify_isolated_runtime,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.outcomes import ai_service


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", [None, "database", "queue", "environment", "root"])
async def test_eval_runtime_requires_exact_isolation(mutation):
    run_id = uuid4()
    settings = Settings(
        env="protocol-evaluation",
        langfuse_environment="protocol-evaluation",
        outcome_root_prompt_version=1,
        temporal_task_queue=f"graf-protocol-eval-{run_id.hex}",
    )
    if mutation == "queue":
        settings.temporal_task_queue = "twobrain-rec-processing"
    elif mutation == "environment":
        settings.env = "production"
    elif mutation == "root":
        settings.outcome_root_prompt_version = None

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_):
            pass

        async def scalar(self, _query):
            return "twobrain_rec" if mutation == "database" else f"graf_protocol_eval_{run_id.hex}"

    if mutation:
        with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="evaluation_"):
            await verify_isolated_runtime(settings, Session, run_id)
    else:
        await verify_isolated_runtime(settings, Session, run_id)


@pytest.mark.anyio
@pytest.mark.parametrize("revoked", [False, True])
async def test_eval_activity_uses_shared_generator_and_live_guard(monkeypatch, revoked):
    invoked = []
    instance = EvaluationActivities(Settings(), object(), object())
    payload = {
        "workspace_id": str(uuid4()),
        "candidate_id": str(uuid4()),
        "snapshot_hash": "source-hash",
    }

    async def guard(current):
        assert current == payload
        if revoked:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")
        invoked.append("guard")

    async def execute(sessionmaker, **kwargs):
        assert sessionmaker is instance.sessionmaker
        assert kwargs["expected_snapshot_hash"] == payload["snapshot_hash"]
        await kwargs["evaluation_source_guard"]()
        invoked.append("generate")
        return {"state": "candidate"}

    monkeypatch.setattr(instance, "guard", guard)
    monkeypatch.setattr(ai_service, "execute_candidate_generation", execute)
    if revoked:
        with pytest.raises(
            ai_service.OutcomeGenerationTerminalError, match="evaluation_source_changed"
        ):
            await instance.generate(payload)
        assert invoked == []
    else:
        assert await instance.generate(payload) == {"state": "candidate"}
        assert invoked == ["guard", "generate"]


@pytest.mark.anyio
async def test_eval_mode_cannot_be_used_in_ordinary_runtime():
    async def forbidden_guard():
        raise AssertionError("must refuse before reading the source")

    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="summary_evaluation_isolation_required"
    ):
        await ai_service.execute_candidate_generation(
            None,
            settings=Settings(),
            workspace_id=uuid4(),
            candidate_id=uuid4(),
            expected_snapshot_hash="source",
            evaluation_source_guard=forbidden_guard,
        )


@pytest.fixture
def generate_one_case(tmp_path, monkeypatch):
    meeting_id, run_id, other_meeting_id = uuid4(), uuid4(), uuid4()
    workdir = evaluator.PrivateWorkdir.create(tmp_path, tmp_path / "checkout")
    prefixes = ("source", "output", "review", "inventory-notes", "exclusion")
    own_names = [f"{prefix}-{meeting_id}.json" for prefix in prefixes]
    other_names = [f"{prefix}-{other_meeting_id}.json" for prefix in prefixes]
    for name in [*own_names, *other_names, "inventory.json"]:
        workdir.write_json(name, {"synthetic": name})
    original = {path.name: path.read_bytes() for path in workdir.path.iterdir()}
    events = []

    class Session:
        async def __aenter__(self):
            events.append("session")
            return self

        async def __aexit__(self, *_):
            events.append("exit")

        async def commit(self):
            events.append("commit")

    session = Session()

    async def verify(settings, sessionmaker, current_run_id):
        assert settings is arguments["settings"]
        assert sessionmaker is arguments["sessionmaker"]
        assert current_run_id == run_id
        events.append("verify")

    async def purge(db, current_meeting_id):
        assert db is session and current_meeting_id == meeting_id
        events.append("purge")

    arguments = {
        "settings": object(),
        "sessionmaker": lambda: session,
        # A bare object deliberately cannot read any source or contact production.
        "source_reader": object(),
        "workdir": workdir,
        "run_id": run_id,
        "meeting_id": meeting_id,
    }
    purge_mock = AsyncMock(side_effect=purge)
    monkeypatch.setattr(runtime, "verify_isolated_runtime", verify)
    async def pin(settings, sessionmaker, current_workdir, current_run_id):
        assert current_workdir is workdir
        await runtime.verify_isolated_runtime(settings, sessionmaker, current_run_id)
        return settings

    monkeypatch.setattr(runtime, "pin_evaluation_run", pin)
    # This in-memory flow fixture stubs pinning and exercises full-corpus mode;
    # signed representative selection is covered by its dedicated contract tests.
    monkeypatch.setattr(evaluator, "evaluation_sample", lambda _workdir, _run_id: None)
    monkeypatch.setattr(evaluator, "purge_shadow_source", purge_mock)
    return SimpleNamespace(
        arguments=arguments,
        workdir=workdir,
        events=events,
        own_names=own_names,
        other_names=other_names,
        original=original,
        purge=purge_mock,
        session=session,
    )


@pytest.mark.anyio
@pytest.mark.parametrize("code", ["evaluation_source_unavailable", "evaluation_source_changed"])
async def test_generate_one_purges_old_copies_on_early_source_invalidation(
    monkeypatch, generate_one_case, code
):
    case = generate_one_case
    failure = ai_service.OutcomeGenerationTerminalError(code)

    async def generate(**kwargs):
        assert kwargs == case.arguments
        assert case.events == ["verify"]
        case.events.append("generate")
        # Fail before a fresh snapshot or Temporal session has been created.
        raise failure

    monkeypatch.setattr(runtime, "_generate_one", generate)
    with pytest.raises(ai_service.OutcomeGenerationTerminalError) as caught:
        await runtime.generate_one(**case.arguments)
    assert caught.value is failure
    assert case.events == ["verify", "generate", "session", "purge", "commit", "exit"]
    case.purge.assert_awaited_once()
    assert all(not (case.workdir.path / name).exists() for name in case.own_names)
    for name in [*case.other_names, "inventory.json"]:
        assert (case.workdir.path / name).read_bytes() == case.original[name]


@pytest.mark.anyio
@pytest.mark.parametrize("baseline", ["inventory", "saved_source"])
async def test_generate_one_detects_changed_source_before_save_and_purges(
    monkeypatch, generate_one_case, baseline
):
    case = generate_one_case
    meeting_id = case.arguments["meeting_id"]
    snapshot = {
        "meeting_id": str(meeting_id),
        "selection_status": "available",
        "source_hash": "b" * 64,
    }
    case.workdir.discard("inventory.json")
    case.workdir.discard(case.own_names[0])
    if baseline == "inventory":
        # No saved source: the run inventory must independently invalidate this read.
        case.workdir.write_json(
            "inventory.json",
            {
                "run_id": str(case.arguments["run_id"]),
                "meetings": [{**snapshot, "source_hash": "a" * 64}],
            },
        )
    else:
        # Helper callers without an inventory still compare the previous source.
        case.workdir.write_json(case.own_names[0], {**snapshot, "source_hash": "a" * 64})
    preserved = {
        path.name: path.read_bytes()
        for path in case.workdir.path.iterdir()
        if path.name not in case.own_names
    }
    reader = SimpleNamespace(
        read=AsyncMock(return_value=snapshot), check=AsyncMock(return_value=None)
    )
    case.arguments["source_reader"] = reader
    save = Mock(wraps=runtime.save_once)
    monkeypatch.setattr(runtime, "save_once", save)

    # Exercise the real early _generate_one path, with no source or Temporal calls.
    with pytest.raises(ai_service.OutcomeGenerationTerminalError) as caught:
        await runtime.generate_one(**case.arguments)
    assert str(caught.value) == "evaluation_source_changed"
    reader.read.assert_awaited_once_with(meeting_id)
    reader.check.assert_awaited_once_with(meeting_id, snapshot["source_hash"])
    save.assert_not_called()
    case.purge.assert_awaited_once()
    assert case.events == ["verify", "session", "purge", "commit", "exit"]
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == preserved


@pytest.mark.anyio
@pytest.mark.parametrize("code", ["evaluation_source_unavailable", "evaluation_source_changed"])
async def test_generate_one_attempts_every_discard_and_purge_after_cleanup_error(
    monkeypatch, generate_one_case, code
):
    case = generate_one_case
    generate = AsyncMock(side_effect=ai_service.OutcomeGenerationTerminalError(code))
    monkeypatch.setattr(runtime, "_generate_one", generate)
    original_discard = case.workdir.discard

    def discard(name):
        case.events.append(f"discard:{name}")
        if name == case.own_names[0]:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_private_cleanup_failed")
        original_discard(name)

    discard_mock = Mock(side_effect=discard)
    monkeypatch.setattr(case.workdir, "discard", discard_mock)
    with pytest.raises(ai_service.OutcomeGenerationTerminalError) as caught:
        await runtime.generate_one(**case.arguments)
    assert str(caught.value) == "evaluation_private_cleanup_failed"
    assert caught.value.__suppress_context__
    generate.assert_awaited_once_with(**case.arguments)
    assert discard_mock.call_args_list == [call(name) for name in case.own_names]
    case.purge.assert_awaited_once()
    assert case.events == [
        "verify",
        *(f"discard:{name}" for name in case.own_names),
        "session",
        "purge",
        "commit",
        "exit",
    ]
    assert all(not (case.workdir.path / name).exists() for name in case.own_names[1:])
    for name in [case.own_names[0], *case.other_names, "inventory.json"]:
        assert (case.workdir.path / name).read_bytes() == case.original[name]


@pytest.mark.anyio
async def test_generate_one_preserves_all_copies_on_transient_source_read_error(
    monkeypatch, generate_one_case
):
    case = generate_one_case
    failure = ai_service.OutcomeGenerationTerminalError("evaluation_source_read_failed")
    generate = AsyncMock(side_effect=failure)
    monkeypatch.setattr(runtime, "_generate_one", generate)

    with pytest.raises(ai_service.OutcomeGenerationTerminalError) as caught:
        await runtime.generate_one(**case.arguments)
    assert caught.value is failure
    generate.assert_awaited_once_with(**case.arguments)
    case.purge.assert_not_awaited()
    assert case.events == ["verify"]
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.anyio
async def test_generate_one_refuses_before_generation_or_cleanup_when_isolation_fails(
    monkeypatch, generate_one_case
):
    case = generate_one_case
    failure = ai_service.OutcomeGenerationTerminalError("evaluation_database_mismatch")
    verify = AsyncMock(side_effect=failure)
    generate = AsyncMock()
    monkeypatch.setattr(runtime, "verify_isolated_runtime", verify)
    monkeypatch.setattr(runtime, "_generate_one", generate)

    with pytest.raises(ai_service.OutcomeGenerationTerminalError) as caught:
        await runtime.generate_one(**case.arguments)
    assert caught.value is failure
    verify.assert_awaited_once_with(
        case.arguments["settings"], case.arguments["sessionmaker"], case.arguments["run_id"]
    )
    generate.assert_not_awaited()
    case.purge.assert_not_awaited()
    assert case.events == []
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.anyio
async def test_generate_one_returns_result_without_cleanup(monkeypatch, generate_one_case):
    case = generate_one_case
    result = {"state": "candidate", "candidate_id": str(uuid4())}
    generate = AsyncMock(return_value=result)
    monkeypatch.setattr(runtime, "_generate_one", generate)

    assert await runtime.generate_one(**case.arguments) is result
    generate.assert_awaited_once_with(**case.arguments)
    case.purge.assert_not_awaited()
    assert case.events == ["verify"]
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.fixture
def runtime_flow_case(generate_one_case, monkeypatch):
    case = generate_one_case
    meeting_id, run_id = case.arguments["meeting_id"], case.arguments["run_id"]
    case.arguments["settings"] = Settings(
        env="protocol-evaluation",
        langfuse_environment="protocol-evaluation",
        outcome_root_prompt_version=6,
        temporal_task_queue=f"graf-protocol-eval-{run_id.hex}",
    )
    snapshot = {"meeting_id": str(meeting_id), "source_hash": "a" * 64}
    for name in ("inventory.json", case.own_names[0], case.own_names[1]):
        case.workdir.discard(name)
    case.workdir.write_json("inventory.json", {"run_id": str(run_id), "meetings": [snapshot]})
    case.workdir.write_json(case.own_names[0], snapshot)
    case.reader = SimpleNamespace(read=AsyncMock(return_value=snapshot), check=AsyncMock())
    case.arguments["source_reader"] = case.reader
    case.attempt = SimpleNamespace(
        id=uuid4(),
        candidate_id=uuid4(),
        workspace_id=uuid4(),
        meeting_id=meeting_id,
        source_result_id=uuid4(),
        template_key="graf-auto-v1",
        template_version=2,
        prompt_version=1,
        status="candidate",
        outcome_set_id=uuid4(),
        failure_code=None,
        workflow_run_id="synthetic-generation-run",
        metadata_json={
            "evaluation_only": True,
            "evaluation_run_id": str(run_id),
            "evaluation_source": {"meeting_id": str(meeting_id), "snapshot_hash": "a" * 64},
            "prompt_bundle": {"root_prompt_version": 6, "root_bundle_hash": "b" * 64},
        },
    )
    case.attempt.workflow_id = f"outcome-generation/{case.attempt.candidate_id}"
    case.outcome = SimpleNamespace(content_hash="c" * 64, protocol_json={"synthetic": True})
    case.calls = [
        SimpleNamespace(
            call_state="completed",
            completed_at=True,
            raw_response_json={"synthetic": "retained"},
            validated_result_json={"synthetic": "validated"},
            export_status="pending",
        )
    ]
    case.session.scalar = AsyncMock(return_value=case.attempt)
    case.session.scalars = AsyncMock(return_value=SimpleNamespace(all=lambda: case.calls))
    case.session.get = AsyncMock(
        side_effect=lambda model, _id: (
            case.attempt if model is runtime.MeetingOutcomeGenerationAttempt else case.outcome
        )
    )
    case.handle = SimpleNamespace(
        result=AsyncMock(
            return_value={
                "candidate_terminal": True,
                "pending_count": 0,
                "published_count": 1,
            }
        )
    )
    case.temporal = SimpleNamespace(start_workflow=AsyncMock(return_value=case.handle))
    case.connect = AsyncMock(return_value=case.temporal)
    monkeypatch.setattr(runtime, "connect_temporal_client", case.connect)

    class Worker:
        async def __aenter__(self):
            case.events.append("worker_enter")
            return self

        async def __aexit__(self, *_):
            case.events.append("worker_exit")

    case.worker = Mock(return_value=Worker())
    monkeypatch.setattr(runtime, "Worker", case.worker)
    monkeypatch.setattr(
        ai_service,
        "_stored_prompt_snapshot",
        lambda attempt: (
            SimpleNamespace(
                root_prompt_version=attempt.metadata_json["prompt_bundle"]["root_prompt_version"]
            )
            if attempt.metadata_json.get("prompt_bundle")
            else None
        ),
    )
    case.original = {path.name: path.read_bytes() for path in case.workdir.path.iterdir()}
    return case


@pytest.mark.anyio
@pytest.mark.parametrize("during_delivery", [False, True])
async def test_revoke_purges_without_waiting_for_observer(
    monkeypatch, runtime_flow_case, during_delivery
):
    case = runtime_flow_case
    failure = ai_service.OutcomeGenerationTerminalError("evaluation_source_unavailable")
    if during_delivery:
        # Access was still valid at workflow completion, then revoked during delivery.
        case.reader.check.side_effect = [None, None, failure]
        sleep = AsyncMock(side_effect=[None, AssertionError("must recheck during delivery")])
    else:
        case.handle.result.side_effect = WorkflowFailureError(cause=ApplicationError(str(failure)))
        case.reader.check.side_effect = [None, failure]
        sleep = AsyncMock(side_effect=AssertionError("must purge before waiting for delivery"))
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    retained = deepcopy(vars(case.calls[0]))
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_source_unavailable$"
    ):
        await asyncio.wait_for(runtime.generate_one(**case.arguments), timeout=0.1)
    case.purge.assert_awaited_once()
    assert all(not (case.workdir.path / name).exists() for name in case.own_names)
    assert vars(case.calls[0]) == retained
    if during_delivery:
        sleep.assert_awaited_once()
    else:
        sleep.assert_not_awaited()


@pytest.mark.anyio
async def test_observer_wait_is_bounded_and_preserves_retry_copies(monkeypatch, runtime_flow_case):
    case = runtime_flow_case
    monkeypatch.setattr(runtime, "OBSERVER_WAIT_SECONDS", 0.01, raising=False)
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_observer_pending$"
    ):
        await asyncio.wait_for(runtime.generate_one(**case.arguments), timeout=0.1)
    case.purge.assert_not_awaited()
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.anyio
async def test_transient_source_error_during_observer_wait_preserves_retry_copies(
    runtime_flow_case,
):
    case = runtime_flow_case
    case.reader.check.side_effect = [
        None,
        ai_service.OutcomeGenerationTerminalError("evaluation_source_read_failed"),
    ]
    retained = deepcopy(vars(case.calls[0]))
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_source_read_failed$"
    ):
        await runtime.generate_one(**case.arguments)
    case.purge.assert_not_awaited()
    assert vars(case.calls[0]) == retained
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.anyio
async def test_generation_wait_is_bounded_and_preserves_retry_copies(
    monkeypatch, runtime_flow_case
):
    case = runtime_flow_case
    case.handle.result.side_effect = asyncio.Event().wait
    monkeypatch.setattr(runtime, "GENERATION_WAIT_SECONDS", 0.01)
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_generation_pending$"
    ):
        await asyncio.wait_for(runtime.generate_one(**case.arguments), timeout=0.1)
    case.purge.assert_not_awaited()
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.parametrize("mutation", [None, "root", "corrupt", "missing"])
def test_root_resume_validates_real_stored_snapshot(mutation):
    attempt = SimpleNamespace(
        prompt_name="graf/meeting-outcome/auto", metadata_json={"template_sections": ["summary"]}, template_id=None,
        template_key="graf-auto-v1", template_version=2, output_language="ru",
        detail_level="detailed",
    )
    pin_protocol_prompts(attempt)
    settings = Settings(outcome_root_prompt_version=1)
    if mutation == "root":
        settings.outcome_root_prompt_version = 6
    elif mutation == "corrupt":
        attempt.prompt_hash = "0" * 64
    elif mutation == "missing":
        attempt.metadata_json.pop("prompt_bundle")
    if mutation is None:
        runtime._require_evaluation_root(attempt, settings)
    else:
        with pytest.raises(
            ai_service.OutcomeGenerationTerminalError, match="^evaluation_root_mismatch$"
        ) as caught:
            runtime._require_evaluation_root(attempt, settings)
        assert caught.value.__suppress_context__


@pytest.mark.parametrize("status", ["queued", "generating", "candidate"])
def test_only_active_unpinned_candidate_may_resolve_first_root(status):
    attempt = SimpleNamespace(
        status=status,
        prompt_name="graf/meeting-outcome/auto",
        prompt_version=None,
        metadata_json={},
    )
    if status == "candidate":
        with pytest.raises(
            ai_service.OutcomeGenerationTerminalError, match="^evaluation_root_mismatch$"
        ):
            runtime._require_evaluation_root(attempt, Settings(outcome_root_prompt_version=6))
    else:
        runtime._require_evaluation_root(attempt, Settings(outcome_root_prompt_version=6))


@pytest.mark.anyio
async def test_resume_accepts_same_root_and_saves_output(runtime_flow_case):
    case = runtime_flow_case
    case.calls.clear()
    result = await runtime.generate_one(**case.arguments)
    assert result["state"] == "candidate"
    assert result["root_hash"] == case.attempt.metadata_json["prompt_bundle"]["root_bundle_hash"]
    assert case.workdir.read_json(case.own_names[1])["protocol"] == case.outcome.protocol_json
    case.connect.assert_awaited_once()
    case.purge.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("response_received", [False, True])
async def test_observer_drain_follows_shared_retry_export_requirements(
    monkeypatch, runtime_flow_case, response_received,
):
    case = runtime_flow_case
    prior = SimpleNamespace(
        call_sequence=1, provider_attempt=1, call_state="failed", completed_at=True,
        export_status="pending" if response_received else "not_required",
        raw_response_json={"error": "synthetic"} if response_received else None,
        validated_result_json={"generation_error": {
            "code": "litellm_transport_error", "retryable_classification": True,
            "egress_state": "response_received" if response_received else "not_sent",
            "response_received": response_received,
        }},
    )
    completed = case.calls[0]
    completed.export_status = "confirmed"
    completed.call_sequence, completed.provider_attempt = 1, 2
    verifier = deepcopy(completed)
    verifier.call_sequence, verifier.provider_attempt = 2, 1
    case.calls[:] = [prior, completed, verifier]
    retained = deepcopy([vars(call) for call in case.calls])
    async def delivered(_delay):
        assert response_received and prior.export_status == "pending"
        prior.export_status = "confirmed"

    sleep = AsyncMock(side_effect=delivered)
    monkeypatch.setattr(runtime.asyncio, "sleep", sleep)
    result = await runtime.generate_one(**case.arguments)
    assert result["state"] == "candidate"
    assert sleep.await_count == int(response_received)
    if response_received:
        retained[0]["export_status"] = "confirmed"
    assert [vars(call) for call in case.calls] == retained
    assert len(case.workdir.read_json(case.own_names[1])["calls"]) == 3


@pytest.mark.anyio
@pytest.mark.parametrize("stored_version", [5, None, "6"])
async def test_resume_rejects_wrong_or_missing_root_before_temporal(
    runtime_flow_case, stored_version
):
    case = runtime_flow_case
    case.attempt.metadata_json["prompt_bundle"]["root_prompt_version"] = stored_version
    case.calls.clear()
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_root_mismatch$"
    ):
        await runtime.generate_one(**case.arguments)
    case.connect.assert_not_awaited()
    case.purge.assert_not_awaited()
    assert {path.name: path.read_bytes() for path in case.workdir.path.iterdir()} == case.original


@pytest.mark.anyio
async def test_activity_guard_rejects_old_root_before_source_read(monkeypatch, runtime_flow_case):
    case = runtime_flow_case
    case.attempt.metadata_json["prompt_bundle"]["root_prompt_version"] = 5
    monkeypatch.setattr(ai_service, "_apply_worker_workspace", AsyncMock())
    monkeypatch.setattr(ai_service, "_candidate_attempt", AsyncMock(return_value=case.attempt))
    activities = EvaluationActivities(
        case.arguments["settings"], case.arguments["sessionmaker"], case.reader
    )
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_root_mismatch$"
    ):
        await activities.guard(
            {
                "workspace_id": str(case.attempt.workspace_id),
                "candidate_id": str(case.attempt.candidate_id),
            }
        )
    case.reader.check.assert_not_awaited()


@pytest.mark.anyio
async def test_recover_observer_after_purge_uses_only_retained_publisher(runtime_flow_case):
    case = runtime_flow_case
    case.attempt.status = "cancelled"
    case.attempt.metadata_json["purged_for_deletion"] = True
    case.attempt.metadata_json["prompt_bundle"]["root_prompt_version"] = 5
    for name in case.own_names:
        case.workdir.discard(name)
    retained = deepcopy(vars(case.calls[0]))
    result = await runtime.recover_observer(
        settings=case.arguments["settings"],
        sessionmaker=case.arguments["sessionmaker"],
        run_id=case.arguments["run_id"],
        meeting_id=case.arguments["meeting_id"],
    )
    assert result == {"state": "observations_confirmed", "published_count": 1}
    case.reader.read.assert_not_awaited()
    case.reader.check.assert_not_awaited()
    case.purge.assert_not_awaited()
    assert vars(case.calls[0]) == retained
    worker = case.worker.call_args.kwargs
    assert worker["workflows"] == [runtime.OutcomeObservabilityReconcilerWorkflow]
    assert [fn.__name__ for fn in worker["activities"]] == ["publish"]
    assert (
        worker["task_queue"]
        == runtime.outcome_generation_task_queue(case.arguments["settings"]) + "-observer-recovery"
    )
    started = case.temporal.start_workflow.call_args
    assert started.args[0] == runtime.OutcomeObservabilityReconcilerWorkflow.run
    assert started.kwargs["task_queue"] == worker["task_queue"]
    assert started.args[1]["candidate_id"] == str(case.attempt.candidate_id)
    assert all(not (case.workdir.path / name).exists() for name in case.own_names)


@pytest.mark.anyio
@pytest.mark.parametrize("mutation", ["run", "marker", "meeting", "active"])
async def test_recover_observer_rejects_unbound_or_active_candidates(runtime_flow_case, mutation):
    case = runtime_flow_case
    if mutation == "run":
        case.attempt.metadata_json["evaluation_run_id"] = str(uuid4())
    elif mutation == "marker":
        case.attempt.metadata_json["evaluation_only"] = False
    elif mutation == "meeting":
        case.attempt.metadata_json["evaluation_source"]["meeting_id"] = str(uuid4())
    else:
        case.attempt.status = "generating"
    with pytest.raises(ai_service.OutcomeGenerationTerminalError, match="^evaluation_"):
        await runtime.recover_observer(
            settings=case.arguments["settings"],
            sessionmaker=case.arguments["sessionmaker"],
            run_id=case.arguments["run_id"],
            meeting_id=case.arguments["meeting_id"],
        )
    case.connect.assert_not_awaited()


@pytest.mark.anyio
async def test_recover_observer_timeout_leaves_ledger_retryable(monkeypatch, runtime_flow_case):
    case = runtime_flow_case
    case.handle.result.side_effect = asyncio.Event().wait
    monkeypatch.setattr(runtime, "OBSERVER_WAIT_SECONDS", 0.01, raising=False)
    retained = deepcopy(vars(case.calls[0]))
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_observer_pending$"
    ):
        await runtime.recover_observer(
            settings=case.arguments["settings"],
            sessionmaker=case.arguments["sessionmaker"],
            run_id=case.arguments["run_id"],
            meeting_id=case.arguments["meeting_id"],
        )
    assert vars(case.calls[0]) == retained
    case.purge.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.parametrize("terminal,pending", [(False, 0), (True, 1)])
async def test_recover_observer_never_confirms_incomplete_delivery(
    runtime_flow_case, terminal, pending
):
    case = runtime_flow_case
    case.handle.result.return_value = {
        "candidate_terminal": terminal,
        "pending_count": pending,
        "published_count": 0,
    }
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_observer_pending$"
    ):
        await runtime.recover_observer(
            settings=case.arguments["settings"],
            sessionmaker=case.arguments["sessionmaker"],
            run_id=case.arguments["run_id"],
            meeting_id=case.arguments["meeting_id"],
        )


@pytest.mark.anyio
async def test_recover_observer_reattaches_to_existing_recovery(runtime_flow_case):
    case = runtime_flow_case
    workflow_id = f"outcome-observability-recovery/{case.attempt.candidate_id}"
    case.temporal.start_workflow.side_effect = WorkflowAlreadyStartedError(workflow_id, "synthetic")
    case.temporal.get_workflow_handle = Mock(return_value=case.handle)
    result = await runtime.recover_observer(
        settings=case.arguments["settings"],
        sessionmaker=case.arguments["sessionmaker"],
        run_id=case.arguments["run_id"],
        meeting_id=case.arguments["meeting_id"],
    )
    case.temporal.get_workflow_handle.assert_called_once_with(workflow_id)
    assert result["state"] == "observations_confirmed"


@pytest.mark.anyio
async def test_recover_observer_refuses_invalid_isolation(monkeypatch, runtime_flow_case):
    case = runtime_flow_case
    monkeypatch.setattr(
        runtime,
        "verify_isolated_runtime",
        AsyncMock(
            side_effect=ai_service.OutcomeGenerationTerminalError("evaluation_database_mismatch"),
        ),
    )
    with pytest.raises(
        ai_service.OutcomeGenerationTerminalError, match="^evaluation_database_mismatch$"
    ):
        await runtime.recover_observer(
            settings=case.arguments["settings"],
            sessionmaker=case.arguments["sessionmaker"],
            run_id=case.arguments["run_id"],
            meeting_id=case.arguments["meeting_id"],
        )
    case.session.scalar.assert_not_awaited()
    case.connect.assert_not_awaited()


@pytest.mark.anyio
@pytest.mark.skipif(shutil.which("temporal") is None, reason="Requires existing local Temporal CLI")
async def test_recover_observer_real_temporal_after_purge(monkeypatch, runtime_flow_case):
    case = runtime_flow_case
    case.attempt.status = "cancelled"
    case.attempt.metadata_json["purged_for_deletion"] = True
    for name in case.own_names:
        case.workdir.discard(name)
    retained = deepcopy(vars(case.calls[0]))
    publish = AsyncMock(
        return_value={
            "candidate_terminal": True,
            "pending_count": 0,
            "published_count": 1,
        }
    )
    monkeypatch.setattr(ai_service, "publish_candidate_generation_calls", publish)
    monkeypatch.setattr(runtime, "Worker", TemporalWorker)
    async with await WorkflowEnvironment.start_local(
        dev_server_existing_path=shutil.which("temporal"),
    ) as temporal:
        case.connect.return_value = temporal.client
        result = await asyncio.wait_for(
            runtime.recover_observer(
                settings=case.arguments["settings"],
                sessionmaker=case.arguments["sessionmaker"],
                run_id=case.arguments["run_id"],
                meeting_id=case.arguments["meeting_id"],
            ),
            timeout=45,
        )
    assert result == {"state": "observations_confirmed", "published_count": 1}
    publish.assert_awaited_once()
    delivered = publish.call_args.kwargs
    assert delivered["candidate_id"] == case.attempt.candidate_id
    assert delivered["temporal_workflow_id"] == case.attempt.workflow_id
    assert delivered["temporal_run_id"] == case.attempt.workflow_run_id
    assert vars(case.calls[0]) == retained
    case.reader.read.assert_not_awaited()
    case.reader.check.assert_not_awaited()
    assert all(not (case.workdir.path / name).exists() for name in case.own_names)


def test_recover_observer_cli_needs_no_private_workdir_or_source(monkeypatch, capsys):
    run_id, meeting_id = uuid4(), uuid4()
    monkeypatch.setattr(
        "sys.argv",
        ["eval", "recover-observer", "--run-id", str(run_id), "--meeting-id", str(meeting_id)],
    )
    forbidden = Mock(side_effect=AssertionError("recovery cannot access private/source files"))
    monkeypatch.setattr(evaluator, "PrivateWorkdir", forbidden)
    monkeypatch.setattr(evaluator, "SourceReader", forbidden)
    settings, sessions = object(), object()
    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(runtime, "get_settings", lambda: settings)
    monkeypatch.setattr(runtime, "create_engine", lambda _: engine)
    monkeypatch.setattr(runtime, "create_sessionmaker", lambda _: sessions)
    recover = AsyncMock(return_value={"state": "observations_confirmed", "published_count": 2})
    monkeypatch.setattr(runtime, "recover_observer", recover, raising=False)
    # Avoid changing global test logging while exercising the CLI wrapper.
    monkeypatch.setattr(runtime.logging, "disable", Mock())
    runtime.main()
    recover.assert_awaited_once_with(
        settings=settings, sessionmaker=sessions, run_id=run_id, meeting_id=meeting_id
    )
    forbidden.assert_not_called()
    engine.dispose.assert_awaited_once()
    assert json.loads(capsys.readouterr().out) == {
        "state": "observations_confirmed",
        "published_count": 2,
    }


@pytest.mark.parametrize("outcome", ["complete", "pending", "failed", "exception"])
def test_report_cli_uses_final_source_cutoff_without_generation(monkeypatch, capsys, outcome):
    run_id = uuid4()
    monkeypatch.setattr("sys.argv", [
        "eval", "report", "--run-id", str(run_id), "--workdir", "/synthetic-unused",
        "--source-host", "synthetic-host", "--source-container", "synthetic-container",
    ])
    workdir, reader, settings, sessions = object(), object(), object(), object()
    private_dir = Mock(return_value=workdir)
    source_reader = Mock(return_value=reader)
    monkeypatch.setattr(evaluator, "PrivateWorkdir", private_dir)
    monkeypatch.setattr(evaluator, "SourceReader", source_reader)
    engine = SimpleNamespace(dispose=AsyncMock())
    monkeypatch.setattr(runtime, "get_settings", lambda: settings)
    monkeypatch.setattr(runtime, "create_engine", lambda _: engine)
    monkeypatch.setattr(runtime, "create_sessionmaker", lambda _: sessions)
    report = {
        "complete": outcome == "complete", "found": 1,
        "passed": int(outcome == "complete"), "pending": int(outcome == "pending"),
        "failed": int(outcome == "failed"), "errors": {}, "cutoff_at": "synthetic-cutoff",
    }
    if outcome == "complete":
        report["qualification_report"] = {"private_marker": "synthetic private report identities"}
    finalize = AsyncMock(return_value=report)
    if outcome == "exception":
        finalize.side_effect = RuntimeError("synthetic private exception content")
    monkeypatch.setattr(evaluator, "finalize_run", finalize)
    monkeypatch.setattr(runtime, "pin_evaluation_run", AsyncMock(return_value=settings))
    forbidden = AsyncMock(side_effect=AssertionError("report cannot generate or start Temporal"))
    monkeypatch.setattr(runtime, "generate_one", forbidden)
    monkeypatch.setattr(runtime, "connect_temporal_client", forbidden)
    monkeypatch.setattr(runtime.logging, "disable", Mock())
    if outcome == "complete":
        runtime.main()
    else:
        with pytest.raises(SystemExit) as caught:
            runtime.main()
        assert caught.value.code == 1
    finalize.assert_awaited_once_with(settings, sessions, reader, workdir, run_id)
    engine.dispose.assert_awaited_once()
    forbidden.assert_not_awaited()
    source_reader.assert_called_once_with("synthetic-host", "synthetic-container")
    output = capsys.readouterr()
    assert "synthetic private" not in output.out + output.err
    assert json.loads(output.out) == (
        {"state": "failed", "failure_code": "evaluation_command_failed"}
        if outcome == "exception" else {key: value for key, value in report.items() if key != "qualification_report"}
    )
