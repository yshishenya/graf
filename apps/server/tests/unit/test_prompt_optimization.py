from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from twobrain_rec_server.cli.langfuse_prompts import (
    CONTROL_PROMPTS,
    create_root_bundle_candidate,
    desired_prompts,
    promote_control_prompt_version,
    sync_prompts,
)
from twobrain_rec_server.outcomes.prompt_bundle import (
    bind_snapshot_from_metadata,
    snapshot_bundle_metadata,
)
from twobrain_rec_server.outcomes.prompt_optimization import (
    OUTCOME_EVAL_METRIC_THRESHOLDS,
    OptimizationCandidate,
    PromptOptimizationError,
    PromptOptimizationReconciliationError,
    SyntheticExample,
    SyntheticManifest,
    _commit_database_until_quiescent,
    _publish_optimization_terminal_observation,
    _run_thread_until_quiescent,
    _snapshot_from_payload,
    _snapshot_payload,
    authorize_prompt_rollback_action_activity,
    control_gate_evidence_hash,
    load_persisted_candidate_result,
    load_verified_promoted_snapshot,
    move_production_label,
    optimization_terminal_observation_id,
    parse_reflection_proposal,
    persist_verified_promoted_snapshot,
    promote_control_prompt,
    promote_prompt_candidate_activity,
    prompt_config_hash,
    publish_or_recover_unlabelled_candidate,
    publish_prompt_candidate_activity,
    publish_unlabelled_candidate,
    required_judge_calibration,
    rollback_prompt_production_label_activity,
    validate_candidate_prompt,
    validate_control_prompt_gate,
    validate_heldout_candidate,
    validate_outcome_eval_receipt,
)
from twobrain_rec_server.outcomes.prompts import (
    CONTROL_GATE_CONFIG_KEY,
    canonical_json,
    validate_prompt_snapshot,
)


@pytest.mark.anyio
async def test_cancel_during_label_move_commits_promoted_state_and_keeps_rollback_authority() -> (
    None
):
    started = threading.Event()
    release = threading.Event()
    state: dict[str, object] = {
        "database_status": "candidate",
        "production_version": 7,
        "rollback_prompt_version": 7,
    }

    def blocked_label_move() -> int:
        started.set()
        assert release.wait(timeout=2)
        state["production_version"] = 9
        return 9

    async def promotion_commit_boundary() -> dict[str, object]:
        version = await _run_thread_until_quiescent(
            blocked_label_move,
            on_cancel=lambda: None,
            complete_after_cancel=True,
        )
        state["database_status"] = "promoted"
        return {"status": "promoted", "production_prompt_version": version}

    task = asyncio.create_task(promotion_commit_boundary())
    assert await asyncio.to_thread(started.wait, 1)
    task.cancel()
    await asyncio.sleep(0)

    assert not task.done()
    assert state == {
        "database_status": "candidate",
        "production_version": 7,
        "rollback_prompt_version": 7,
    }

    release.set()
    assert await asyncio.wait_for(task, timeout=1) == {
        "status": "promoted",
        "production_prompt_version": 9,
    }
    assert state == {
        "database_status": "promoted",
        "production_version": 9,
        "rollback_prompt_version": 7,
    }


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "expected_status"),
    [
        ("candidate", "cancelled"),
        ("promotion", "promoted"),
        ("rollback", "rolled_back"),
    ],
)
async def test_cancel_during_db_commit_finishes_boundary_without_split_brain(
    operation,
    expected_status,
) -> None:
    commit_started = asyncio.Event()
    release_commit = asyncio.Event()
    cancellation_observed = threading.Event()
    state = {"external": operation, "database": "before", "commit_finished": False}

    class Database:
        async def commit(self) -> None:
            commit_started.set()
            await release_commit.wait()
            state["database"] = {
                "candidate": "candidate",
                "promotion": "promoted",
                "rollback": "rolled_back",
            }[operation]
            state["commit_finished"] = True

    async def activity_and_workflow_boundary() -> str:
        try:
            await _commit_database_until_quiescent(
                Database(),
                cancellation_observed=(cancellation_observed if operation == "candidate" else None),
                complete_after_cancel=True,
            )
            if operation == "candidate" and cancellation_observed.is_set():
                raise asyncio.CancelledError
            return str(state["database"])
        except asyncio.CancelledError:
            assert state["commit_finished"] is True
            state["database"] = "cancelled"
            return "cancelled"

    task = asyncio.create_task(activity_and_workflow_boundary())
    await commit_started.wait()
    task.cancel()
    await asyncio.sleep(0)

    assert not task.done()
    assert state == {
        "external": operation,
        "database": "before",
        "commit_finished": False,
    }

    release_commit.set()
    assert await task == expected_status
    assert state["database"] == expected_status
    assert state["commit_finished"] is True


def _source():
    prompt_type, prompt, config = desired_prompts()["graf/meeting-outcome/auto"]
    return validate_prompt_snapshot(
        name="graf/meeting-outcome/auto",
        version=1,
        prompt_type=prompt_type,
        prompt=prompt,
        config=config,
    )


def test_reflection_accepts_a_whitespace_padded_complete_chat_prompt() -> None:
    source = _source()
    proposal = parse_reflection_proposal(f"```\n{canonical_json(source.prompt)}\n```")

    assert validate_candidate_prompt(source, proposal).canonical_hash == source.canonical_hash
    with pytest.raises(PromptOptimizationError, match="candidate_"):
        validate_candidate_prompt(source, parse_reflection_proposal("```\nmessage only\n```"))


def test_candidate_publication_has_no_manual_label_and_never_auto_promotes() -> None:
    source = _source()
    created = Mock(version=2)
    fetched = Mock(version=2, prompt=source.prompt, config=source.config, labels=["latest"])
    client = Mock()
    client.create_prompt.return_value = created
    client.get_prompt.return_value = fetched
    result = publish_unlabelled_candidate(client, source=source, candidate_prompt=source.prompt)
    assert result.version == 2
    assert client.create_prompt.call_args.kwargs["labels"] == []
    client.update_prompt.assert_not_called()


def test_candidate_completion_loss_reuses_persisted_version_without_create() -> None:
    source = _source()
    candidate = Mock(
        version=2,
        prompt=source.prompt,
        config=source.config,
        labels=["latest"],
    )
    client = Mock()
    client.get_prompt.return_value = candidate

    restored = load_persisted_candidate_result(
        client,
        source=source,
        candidate_prompt=source.prompt,
        candidate_version=2,
        candidate_hash=validate_prompt_snapshot(
            name=source.name,
            version=2,
            prompt_type=source.prompt_type,
            prompt=source.prompt,
            config=source.config,
        ).canonical_hash,
        candidate_config_hash=prompt_config_hash(source.config),
    )

    assert restored.version == 2
    client.create_prompt.assert_not_called()


def test_candidate_external_create_is_recovered_after_database_commit_failure() -> None:
    source = _source()
    remote = Mock(
        version=2,
        prompt=source.prompt,
        config=source.config,
        labels=["latest"],
    )
    client = Mock()
    client.api.prompts.list.side_effect = [
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[SimpleNamespace(name=source.name, versions=[2])]),
    ]
    client.create_prompt.return_value = Mock(version=2)
    client.get_prompt.return_value = remote
    tag = "graf-optimization-run-10000000-0000-0000-0000-000000000001"

    first = publish_or_recover_unlabelled_candidate(
        client,
        source=source,
        candidate_prompt=source.prompt,
        idempotency_tag=tag,
    )
    # The first DB commit is lost. The retry discovers the uniquely tagged
    # Langfuse version and must not create a duplicate.
    second = publish_or_recover_unlabelled_candidate(
        client,
        source=source,
        candidate_prompt=source.prompt,
        idempotency_tag=tag,
    )

    assert first.version == second.version == 2
    client.create_prompt.assert_called_once()
    assert client.create_prompt.call_args.kwargs["labels"] == []
    assert tag in client.create_prompt.call_args.kwargs["tags"]


def test_production_move_is_protected_conflict_checked_and_postverified() -> None:
    source = _source()
    current = Mock(version=1, prompt=source.prompt, config=source.config)
    target = Mock(version=2, prompt=source.prompt, config=source.config)
    client = Mock()
    client.get_prompt.side_effect = [current, target, target]
    result = move_production_label(
        client,
        prompt_name=source.name,
        prompt_type="chat",
        expected_source_version=1,
        target_version=2,
        protected_label_capability_verified=True,
    )
    assert result.version == 2
    client.update_prompt.assert_called_once_with(
        name=source.name,
        version=2,
        new_labels=["production"],
    )
    client.clear_prompt_cache.assert_called_once_with()
    with pytest.raises(PromptOptimizationError, match="protected_label_capability_unavailable"):
        move_production_label(
            client,
            prompt_name=source.name,
            prompt_type="chat",
            expected_source_version=1,
            target_version=2,
            protected_label_capability_verified=False,
        )


def test_production_move_is_idempotent_after_label_mutation_crash() -> None:
    source = _source()
    target = Mock(version=2, prompt=source.prompt, config=source.config)
    client = Mock()
    client.get_prompt.side_effect = [target, target, target]

    result = move_production_label(
        client,
        prompt_name=source.name,
        prompt_type="chat",
        expected_source_version=1,
        target_version=2,
        protected_label_capability_verified=True,
    )

    assert result.version == 2
    client.update_prompt.assert_not_called()
    client.clear_prompt_cache.assert_called_once_with()


def test_production_move_retries_snapshot_export_after_label_already_moved() -> None:
    source = _source()
    target = Mock(version=2, prompt=source.prompt, config=source.config)
    client = Mock()
    client.get_prompt.side_effect = [source, target, target, target, target, target]

    class Storage:
        def __init__(self) -> None:
            self.objects: dict[str, bytes] = {}
            self.fail_once = True

        def put_stream(self, key, stream, _length):
            if self.fail_once:
                self.fail_once = False
                raise RuntimeError("snapshot export unavailable")
            self.objects[key] = stream.read()

        def get_bytes(self, key):
            return self.objects[key]

    storage = Storage()
    with pytest.raises(
        PromptOptimizationReconciliationError,
        match="production_label_reconciliation_required",
    ):
        move_production_label(
            client,
            prompt_name=source.name,
            prompt_type="chat",
            expected_source_version=1,
            target_version=2,
            protected_label_capability_verified=True,
            snapshot_storage=storage,
        )

    restored = move_production_label(
        client,
        prompt_name=source.name,
        prompt_type="chat",
        expected_source_version=1,
        target_version=2,
        protected_label_capability_verified=True,
        snapshot_storage=storage,
    )

    assert restored.version == 2
    client.update_prompt.assert_called_once()


def _install_prompt_transition_activity_fakes(
    monkeypatch,
    *,
    run,
    client,
    storage,
    commit_hook=None,
    session_exit_hook=None,
    engine_dispose_hook=None,
) -> dict[str, bool]:
    from twobrain_rec_server import config as config_module
    from twobrain_rec_server.db import session as session_module
    from twobrain_rec_server.observability import langfuse as langfuse_module
    from twobrain_rec_server.storage import minio_client as storage_module

    boundary_state = {"session_closed": False, "engine_disposed": False}

    class Engine:
        async def dispose(self):
            if engine_dispose_hook is not None:
                await engine_dispose_hook()
            boundary_state["engine_disposed"] = True
            return None

    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            if session_exit_hook is not None:
                await session_exit_hook()
            boundary_state["session_closed"] = True
            return None

        async def execute(self, _statement, *_args, **_kwargs):
            return None

        async def scalar(self, _statement):
            return run

        async def get(self, *_args, **_kwargs):
            return run

        async def commit(self):
            if commit_hook is not None:
                commit_hook(run)
            return None

    monkeypatch.setattr(config_module, "get_settings", lambda: SimpleNamespace())
    monkeypatch.setattr(
        session_module,
        "create_prompt_optimization_database",
        lambda _settings: (Engine(), lambda: Session()),
    )
    monkeypatch.setattr(langfuse_module, "create_langfuse_client", lambda _settings: client)
    monkeypatch.setattr(langfuse_module, "shutdown_langfuse", lambda _client: None)
    monkeypatch.setattr(storage_module, "get_storage", lambda _settings: storage)
    return boundary_state


@pytest.mark.anyio
@pytest.mark.parametrize("blocked_phase", ["session_exit", "engine_dispose"])
@pytest.mark.parametrize(
    ("operation", "expected_status"),
    [
        ("candidate", "cancelled"),
        ("persisted_candidate", "cancelled"),
        ("promotion", "promoted"),
        ("rollback", "rolled_back"),
    ],
)
async def test_cancel_during_session_exit_or_engine_dispose_keeps_activity_coherent(
    monkeypatch,
    blocked_phase,
    operation,
    expected_status,
) -> None:
    from twobrain_rec_server.outcomes import prompt_optimization as optimization_module

    boundary_started = asyncio.Event()
    release_boundary = asyncio.Event()

    async def block_boundary(phase: str) -> None:
        if blocked_phase == phase:
            boundary_started.set()
            await release_boundary.wait()

    source = _source()
    candidate = validate_prompt_snapshot(
        name=source.name,
        version=2,
        prompt_type=source.prompt_type,
        prompt=source.prompt,
        config=source.config,
    )
    action_id = UUID("30000000-0000-0000-0000-000000000003")
    run_id = UUID("10000000-0000-0000-0000-000000000001")
    run = SimpleNamespace(
        id=run_id,
        status=(
            "candidate"
            if operation in {"persisted_candidate", "promotion"}
            else "promoted"
            if operation == "rollback"
            else "running"
        ),
        approval_state="approved",
        approval_action_id=UUID("20000000-0000-0000-0000-000000000002"),
        approval_expires_at=(
            datetime.now(UTC) + timedelta(days=1) if operation == "persisted_candidate" else None
        ),
        prompt_name=source.name,
        source_prompt_version=source.version,
        candidate_prompt_version=(candidate.version if operation != "candidate" else None),
        candidate_prompt_hash=(candidate.canonical_hash if operation != "candidate" else None),
        candidate_config_hash=(
            prompt_config_hash(candidate.config) if operation != "candidate" else None
        ),
        rollback_prompt_version=source.version,
        aggregate_scores={},
        budget={
            "protected_label_capability_verified": True,
            "rollback_action": {
                "action_id": str(action_id),
                "actor_id": "operator",
                "consumed": True,
            },
        },
    )
    boundary_state = _install_prompt_transition_activity_fakes(
        monkeypatch,
        run=run,
        client=Mock(),
        storage=SimpleNamespace(),
        session_exit_hook=lambda: block_boundary("session_exit"),
        engine_dispose_hook=lambda: block_boundary("engine_dispose"),
    )

    async def return_snapshot(*_args, **_kwargs):
        return candidate if operation != "rollback" else source

    monkeypatch.setattr(
        optimization_module,
        "_run_thread_until_quiescent",
        return_snapshot,
    )
    monkeypatch.setattr(
        optimization_module,
        "_publish_label_transition",
        lambda *_args, **_kwargs: None,
    )
    expires_at = datetime.now(UTC) + timedelta(days=1)
    if operation in {"candidate", "persisted_candidate"}:
        activity = publish_prompt_candidate_activity(
            {
                "run_id": str(run_id),
                "resolved_contract": {"source_prompt": _snapshot_payload(source)},
                "optimization_result": {
                    "prompt_text": canonical_json(source.prompt),
                    "development_score": 1,
                },
                "heldout_result": {
                    "hard_gates_passed": True,
                    "heldout_scores": {},
                },
                "approval_expires_at": expires_at.isoformat(),
            }
        )
    elif operation == "promotion":
        activity = promote_prompt_candidate_activity(
            {
                "run_id": str(run_id),
                "prompt_name": source.name,
                "approval_action_id": str(run.approval_action_id),
            }
        )
    else:
        activity = rollback_prompt_production_label_activity(
            {
                "run_id": str(run_id),
                "prompt_name": source.name,
                "action_id": str(action_id),
            }
        )

    task = asyncio.create_task(activity)
    await boundary_started.wait()
    task.cancel()
    await asyncio.sleep(0)

    assert not task.done()
    release_boundary.set()
    if expected_status == "cancelled":
        with pytest.raises(asyncio.CancelledError):
            await task
    else:
        assert (await task)["status"] == expected_status
    assert boundary_state == {"session_closed": True, "engine_disposed": True}


@pytest.mark.anyio
async def test_candidate_activity_completion_loss_returns_persisted_result_without_duplicate(
    monkeypatch,
) -> None:
    source = _source()
    candidate = validate_prompt_snapshot(
        name=source.name,
        version=2,
        prompt_type=source.prompt_type,
        prompt=source.prompt,
        config=source.config,
    )
    remote = Mock(version=2, prompt=candidate.prompt, config=candidate.config, labels=[])
    client = Mock()
    client.get_prompt.return_value = remote
    expires_at = datetime.now(UTC) + timedelta(days=1)
    run = SimpleNamespace(
        status="candidate",
        source_prompt_version=source.version,
        candidate_prompt_version=candidate.version,
        candidate_prompt_hash=candidate.canonical_hash,
        candidate_config_hash=prompt_config_hash(candidate.config),
        approval_expires_at=expires_at,
    )
    _install_prompt_transition_activity_fakes(
        monkeypatch,
        run=run,
        client=client,
        storage=SimpleNamespace(),
    )

    result = await publish_prompt_candidate_activity(
        {
            "run_id": "10000000-0000-0000-0000-000000000001",
            "resolved_contract": {"source_prompt": _snapshot_payload(source)},
            "optimization_result": {
                "prompt_text": canonical_json(source.prompt),
                "development_score": 1,
            },
            "heldout_result": {"hard_gates_passed": True, "heldout_scores": {}},
            "approval_expires_at": expires_at.isoformat(),
        }
    )

    assert result["candidate_prompt_version"] == 2
    assert result["approval_expires_at"] == expires_at.isoformat()
    client.create_prompt.assert_not_called()


@pytest.mark.anyio
async def test_candidate_activity_recovers_external_create_after_db_commit_failure(
    monkeypatch,
) -> None:
    source = _source()
    candidate = Mock(version=2, prompt=source.prompt, config=source.config, labels=[])
    client = Mock()
    client.api.prompts.list.side_effect = [
        SimpleNamespace(data=[]),
        SimpleNamespace(data=[SimpleNamespace(name=source.name, versions=[2])]),
    ]
    client.create_prompt.return_value = Mock(version=2)
    client.get_prompt.return_value = candidate
    expires_at = datetime.now(UTC) + timedelta(days=1)
    run = SimpleNamespace(
        status="running",
        source_prompt_version=source.version,
        candidate_prompt_version=None,
        candidate_prompt_hash=None,
        candidate_config_hash=None,
        approval_expires_at=None,
    )
    commits = [0]

    def fail_first_commit(current_run) -> None:
        commits[0] += 1
        if commits[0] == 1:
            current_run.status = "running"
            current_run.candidate_prompt_version = None
            current_run.candidate_prompt_hash = None
            current_run.candidate_config_hash = None
            current_run.approval_expires_at = None
            raise RuntimeError("database commit lost")

    _install_prompt_transition_activity_fakes(
        monkeypatch,
        run=run,
        client=client,
        storage=SimpleNamespace(),
        commit_hook=fail_first_commit,
    )
    payload = {
        "run_id": "10000000-0000-0000-0000-000000000001",
        "resolved_contract": {"source_prompt": _snapshot_payload(source)},
        "optimization_result": {
            "prompt_text": canonical_json(source.prompt),
            "development_score": 1,
        },
        "heldout_result": {"hard_gates_passed": True, "heldout_scores": {}},
        "approval_expires_at": expires_at.isoformat(),
    }

    with pytest.raises(RuntimeError, match="database commit lost"):
        await publish_prompt_candidate_activity(payload)
    result = await publish_prompt_candidate_activity(payload)

    assert result["candidate_prompt_version"] == 2
    assert run.status == "candidate"
    client.create_prompt.assert_called_once()
    assert client.create_prompt.call_args.kwargs["labels"] == []


@pytest.mark.anyio
async def test_promotion_completion_loss_returns_verified_durable_result(monkeypatch) -> None:
    source = _source()
    target = validate_prompt_snapshot(
        name=source.name,
        version=2,
        prompt_type=source.prompt_type,
        prompt=source.prompt,
        config=source.config,
    )
    remote = Mock(version=2, prompt=target.prompt, config=target.config)
    client = Mock()
    client.get_prompt.return_value = remote

    class Storage:
        objects: dict[str, bytes] = {}

        def put_stream(self, key, stream, _length):
            self.objects[key] = stream.read()

        def get_bytes(self, key):
            return self.objects[key]

    run = SimpleNamespace(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        status="promoted",
        approval_state="approved",
        approval_action_id=UUID("20000000-0000-0000-0000-000000000002"),
        prompt_name=source.name,
        source_prompt_version=1,
        candidate_prompt_version=2,
        candidate_prompt_hash=target.canonical_hash,
        budget={"protected_label_capability_verified": True},
    )
    _install_prompt_transition_activity_fakes(
        monkeypatch,
        run=run,
        client=client,
        storage=Storage(),
    )

    result = await promote_prompt_candidate_activity(
        {
            "run_id": str(run.id),
            "prompt_name": run.prompt_name,
            "approval_action_id": str(run.approval_action_id),
        }
    )

    assert result == {"status": "promoted", "production_prompt_version": 2}
    client.update_prompt.assert_not_called()


@pytest.mark.anyio
async def test_rollback_completion_loss_reuses_consumed_action_and_durable_result(
    monkeypatch,
) -> None:
    source = _source()
    remote = Mock(version=1, prompt=source.prompt, config=source.config)
    client = Mock()
    client.get_prompt.return_value = remote

    class Storage:
        objects: dict[str, bytes] = {}

        def put_stream(self, key, stream, _length):
            self.objects[key] = stream.read()

        def get_bytes(self, key):
            return self.objects[key]

    action_id = "30000000-0000-0000-0000-000000000003"
    run = SimpleNamespace(
        id=UUID("10000000-0000-0000-0000-000000000001"),
        status="rolled_back",
        prompt_name=source.name,
        source_prompt_version=1,
        candidate_prompt_version=2,
        rollback_prompt_version=1,
        budget={
            "protected_label_capability_verified": True,
            "rollback_action": {
                "action_id": action_id,
                "actor_id": "operator",
                "consumed": True,
            },
        },
    )
    _install_prompt_transition_activity_fakes(
        monkeypatch,
        run=run,
        client=client,
        storage=Storage(),
    )

    assert await authorize_prompt_rollback_action_activity(
        {"run_id": str(run.id), "action_id": action_id}
    ) == {"status": "authorized"}

    result = await rollback_prompt_production_label_activity(
        {
            "run_id": str(run.id),
            "prompt_name": run.prompt_name,
            "action_id": action_id,
        }
    )

    assert result["status"] == "rolled_back"
    assert result["production_prompt_version"] == 1
    client.update_prompt.assert_not_called()


def test_production_move_supports_gated_initial_control_promotion() -> None:
    from langfuse.api.commons.errors.not_found_error import NotFoundError

    source = _source()
    target = Mock(version=2, prompt=source.prompt, config=source.config)
    client = Mock()
    client.get_prompt.side_effect = [NotFoundError(body={}), target, target]

    result = move_production_label(
        client,
        prompt_name=source.name,
        prompt_type="chat",
        expected_source_version=None,
        target_version=2,
        protected_label_capability_verified=True,
    )

    assert result.version == 2
    client.update_prompt.assert_called_once_with(
        name=source.name,
        version=2,
        new_labels=["production"],
    )


def test_verified_promoted_snapshot_is_owner_controlled_fallback() -> None:
    source = _source()

    class Storage:
        objects = {}

        def put_stream(self, key, stream, length):
            value = stream.read()
            assert len(value) == length
            self.objects[key] = value

        def get_bytes(self, key):
            return self.objects[key]

    storage = Storage()
    key = persist_verified_promoted_snapshot(storage, source)
    restored = load_verified_promoted_snapshot(storage, prompt_name=source.name)
    assert key.startswith("_system/prompts/verified-production/")
    assert restored.source == "verified_promoted_snapshot"
    assert restored.canonical_hash == source.canonical_hash


def test_prompt_sync_creates_only_unlabelled_candidates(monkeypatch) -> None:
    import langfuse

    class Client:
        def __init__(self) -> None:
            self.created = []

        def get_prompt(self, *_args, **_kwargs):
            raise RuntimeError("not seeded")

        def create_prompt(self, **kwargs):
            self.created.append(kwargs)
            return Mock(version=len(self.created))

        def flush(self) -> None:
            pass

        def shutdown(self) -> None:
            pass

    client = Client()
    monkeypatch.setattr(langfuse, "Langfuse", lambda **_kwargs: client)

    outcomes = sync_prompts(
        base_url="https://langfuse.invalid",
        public_key="pk-test",
        secret_key="sk-test",
        apply=True,
    )

    control_creates = [row for row in client.created if row["name"] in CONTROL_PROMPTS]
    outcome_creates = [row for row in client.created if row["name"] not in CONTROL_PROMPTS]
    assert control_creates and all(row["labels"] == [] for row in control_creates)
    assert outcome_creates and all(row["labels"] == [] for row in outcome_creates)
    assert all(
        f"config-contract-v{row['config']['config_contract_version']}" in row["tags"]
        for row in client.created
    )
    assert sum(value.startswith("created-control-candidate:") for value in outcomes) == 4
    assert sum(value.startswith("created-outcome-candidate:") for value in outcomes) == 10


def test_prompt_sync_treats_an_older_production_contract_as_change_required(
    monkeypatch,
) -> None:
    import langfuse

    prompt_name = "graf/meeting-outcome/auto"
    prompt_type, prompt, _config = desired_prompts()[prompt_name]

    class Client:
        def get_prompt(self, name, **_kwargs):
            if name == prompt_name:
                return Mock(
                    version=3,
                    prompt=prompt,
                    config={"config_contract_version": 1},
                )
            raise RuntimeError("not seeded")

        def flush(self) -> None:
            pass

        def shutdown(self) -> None:
            pass

    monkeypatch.setattr(langfuse, "Langfuse", lambda **_kwargs: Client())

    outcomes = sync_prompts(
        base_url="https://langfuse.invalid",
        public_key="pk-test",
        secret_key="sk-test",
        apply=False,
    )

    assert f"change-required:{prompt_name}" in outcomes


def test_root_bundle_candidate_accepts_exact_version_per_prompt(monkeypatch) -> None:
    import langfuse

    prompt_definitions = desired_prompts()
    names = [name for name in prompt_definitions if name.startswith("graf/meeting-outcome/")]
    versions = {name: index + 1 for index, name in enumerate(names)}
    calls: list[tuple[str, int]] = []

    class Client:
        def get_prompt(self, name, **kwargs):
            calls.append((name, kwargs["version"]))
            prompt_type, prompt, config = prompt_definitions[name]
            assert prompt_type == "chat"
            return Mock(version=kwargs["version"], prompt=prompt, config=config)

        def create_prompt(self, **_kwargs):
            return Mock(version=31)

        def flush(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr(langfuse, "Langfuse", lambda **_kwargs: Client())
    descriptor = {
        "alias": "gpt-5.6-luna",
        "binding_version": "graf-litellm-route-v1",
        "allowed_provider_models": [{"provider": "openai", "model": "gpt-5.6-luna"}],
        "request_compiler_hash": "a" * 64,
        "request_compiler_version": "graf-chat-compiler-v1",
    }
    from twobrain_rec_server.outcomes.prompt_bundle import route_binding_hash

    route_binding = {**descriptor, "binding_hash": route_binding_hash(descriptor)}
    result = create_root_bundle_candidate(
        base_url="https://langfuse.invalid",
        public_key="pk-test",
        secret_key="sk-test",
        child_versions=versions,
        route_binding=route_binding,
    )

    assert result["root_prompt_version"] == 31
    assert result["child_versions"] == dict(sorted(versions.items()))
    assert sorted(calls) == sorted(versions.items())


def test_optimizer_snapshot_and_candidate_retain_route_binding() -> None:
    source = _source()
    descriptor = {
        "alias": "gpt-5.6-luna",
        "binding_version": "graf-litellm-route-v1",
        "allowed_provider_models": [{"provider": "openai", "model": "gpt-5.6-luna"}],
        "request_compiler_hash": "a" * 64,
        "request_compiler_version": "graf-chat-compiler-v1",
    }
    from twobrain_rec_server.outcomes.prompt_bundle import route_binding_hash

    binding = {**descriptor, "binding_hash": route_binding_hash(descriptor)}
    bound = bind_snapshot_from_metadata(
        source,
        {
            "root_bundle_hash": "b" * 64,
            "root_prompt_version": 3,
            "route_binding_hash": binding["binding_hash"],
            "route_binding": binding,
        },
    )

    restored = _snapshot_from_payload(_snapshot_payload(bound))
    candidate = validate_candidate_prompt(bound, canonical_json(bound.prompt))

    assert snapshot_bundle_metadata(restored) == snapshot_bundle_metadata(bound)
    assert snapshot_bundle_metadata(candidate) == snapshot_bundle_metadata(bound)


def test_production_optimizer_uses_secret_file_and_requires_route_binding(
    monkeypatch, tmp_path
) -> None:
    from twobrain_rec_server.outcomes import generator as generator_module
    from twobrain_rec_server.outcomes.prompt_optimization import _ProductionModelExecutor

    secret = tmp_path / "twobrain_litellm_api_key"
    secret.write_text("luna-key\n", encoding="utf-8")
    captured: dict[str, object] = {}

    class Gateway:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(generator_module, "LiteLLMGateway", Gateway)
    _ProductionModelExecutor(
        settings=SimpleNamespace(
            litellm_base_url="https://litellm.pro-4.ru",
            litellm_api_key_file=secret,
            litellm_request_timeout_seconds=120,
        )
    )

    assert captured == {
        "base_url": "https://litellm.pro-4.ru",
        "api_key": "luna-key",
        "timeout_seconds": 120,
        "require_route_binding": True,
    }


def test_heldout_gate_uses_worst_example_instead_of_mean() -> None:
    first = SyntheticExample(
        id="heldout-1",
        transcript_json='[{"id":"segment"}]',
        segment_ids=frozenset({"segment"}),
        required_categories=("summary",),
    )
    second = SyntheticExample(
        id="heldout-2",
        transcript_json='[{"id":"segment-2"}]',
        segment_ids=frozenset({"segment-2"}),
        required_categories=("summary",),
    )
    heldout = SyntheticManifest.create(
        ref="synthetic://heldout/v1",
        split="heldout",
        version="v1",
        examples=(first, second),
    )
    candidate = OptimizationCandidate(
        prompt_text="prompt",
        prompt_hash="a" * 64,
        source_config_hash="b" * 64,
        development_score=1,
    )
    adapter = Mock()
    adapter.evaluate.return_value = SimpleNamespace(
        scores=[1.0, 0.2],
        objective_scores=[
            {name: 1.0 for name in CONTROL_PROMPTS if name.startswith("graf/evaluation/")},
            {name: 0.2 for name in CONTROL_PROMPTS if name.startswith("graf/evaluation/")},
        ],
    )

    result = validate_heldout_candidate(
        adapter=adapter,
        candidate=candidate,
        heldout=heldout,
        minimum_metric_score=0.5,
    )

    assert result.hard_gates_passed is False
    assert result.heldout_scores == {
        "minimum_judge_score": 0.2,
        "mean_judge_score": 0.6,
        "minimum_faithfulness_score": 0.2,
        "minimum_action_items_score": 0.2,
        "minimum_completeness_score": 0.2,
    }


def test_outcome_eval_receipt_requires_separate_metrics_and_must_unit_coverage() -> None:
    counts = {
        "examples": 12,
        "source_ref_cases": 12,
        "action_gold": 6,
        "owner_gold": 3,
        "due_gold": 3,
        "unknown_cases": 4,
        "must_units": 18,
        "injection_cases": 2,
        "long_context_positions": 3,
        "critical_failures": 0,
    }
    metrics = {name: 1.0 for name in OUTCOME_EVAL_METRIC_THRESHOLDS}

    passed = validate_outcome_eval_receipt(
        metrics=metrics,
        counts=counts,
        long_context_coverage_gap=0.04,
    )
    failed = validate_outcome_eval_receipt(
        metrics={**metrics, "action_recall": 0.89},
        counts={**counts, "critical_failures": 1},
        long_context_coverage_gap=0.06,
    )

    assert passed["hard_gates_passed"] is True
    assert passed["failure_codes"] == []
    assert set(passed) == {
        "counts",
        "failure_codes",
        "hard_gates_passed",
        "long_context_coverage_gap",
        "metrics",
    }
    assert failed["hard_gates_passed"] is False
    assert failed["failure_codes"] == [
        "action_recall_below_threshold",
        "critical_failures_present",
        "long_context_coverage_gap_exceeded",
    ]


def test_adversarial_outcome_manifest_covers_action_and_unknown_restraint_cases() -> None:
    fixtures = (
        SyntheticExample(
            id="explicit-action-owner-relative-due",
            transcript_json=(
                '[{"id":"00000000-0000-0000-0000-000000000001","sequence":0,'
                '"speaker_label":"Анна","text":"Я отправлю план до пятницы"}]'
            ),
            segment_ids=frozenset({"00000000-0000-0000-0000-000000000001"}),
            required_categories=("action_items",),
        ),
        SyntheticExample(
            id="proposal-is-not-action",
            transcript_json=(
                '[{"id":"00000000-0000-0000-0000-000000000002","sequence":0,'
                '"speaker_label":"SPEAKER_00","text":"Можно было бы отправить план"}]'
            ),
            segment_ids=frozenset({"00000000-0000-0000-0000-000000000002"}),
            required_categories=("action_items",),
        ),
        SyntheticExample(
            id="cancelled-and-reassigned-action",
            transcript_json=(
                '[{"id":"00000000-0000-0000-0000-000000000003","sequence":0,'
                '"speaker_label":"Анна","text":"Я отправлю план"},'
                '{"id":"00000000-0000-0000-0000-000000000004","sequence":1,'
                '"speaker_label":"Борис","text":"Нет, план отправлю я; задача Анны отменена"}]'
            ),
            segment_ids=frozenset(
                {
                    "00000000-0000-0000-0000-000000000003",
                    "00000000-0000-0000-0000-000000000004",
                }
            ),
            required_categories=("action_items",),
        ),
        SyntheticExample(
            id="unknown-speaker-never-owner",
            transcript_json=(
                '[{"id":"00000000-0000-0000-0000-000000000005","sequence":0,'
                '"speaker_label":"UNKNOWN","text":"Я проверю доступы"}]'
            ),
            segment_ids=frozenset({"00000000-0000-0000-0000-000000000005"}),
            required_categories=("action_items",),
        ),
    )
    manifest = SyntheticManifest.create(
        ref="synthetic://meeting-outcome-value/adversarial/v1",
        split="heldout",
        version="v1",
        examples=fixtures,
    )

    assert [example.id for example in manifest.examples] == [
        "explicit-action-owner-relative-due",
        "proposal-is-not-action",
        "cancelled-and-reassigned-action",
        "unknown-speaker-never-owner",
    ]
    assert len(manifest.sha256) == 64


def test_synthetic_example_accepts_runtime_sized_long_context() -> None:
    example = SyntheticExample(
        id="long-context-middle",
        transcript_json="x" * 300_000,
        segment_ids=frozenset({"segment"}),
        required_categories=("summary",),
    )

    assert len(example.transcript_json) == 300_000


def test_control_prompt_gate_requires_real_reflection_and_judge_evidence() -> None:
    reflection_type, reflection_prompt, reflection_config = CONTROL_PROMPTS[
        "graf/prompt-optimization/reflection"
    ]
    reflection = validate_prompt_snapshot(
        name="graf/prompt-optimization/reflection",
        version=2,
        prompt_type=reflection_type,
        prompt=reflection_prompt,
        config=reflection_config,
    )
    reflection_evidence = {
        "evaluator_version": "reflection-v1",
        "operator_actor_id": "deploy-operator",
        "operator_approved": True,
        "native_parser_smoke_passed": True,
        "variable_preservation_passed": True,
        "anti_copy_regression_passed": True,
        "bounded_cost_smoke_passed": True,
    }
    assert validate_control_prompt_gate(
        candidate=reflection,
        evidence=reflection_evidence,
    )["passed"]
    with pytest.raises(PromptOptimizationError, match="operator_approval_required"):
        validate_control_prompt_gate(
            candidate=reflection,
            evidence={**reflection_evidence, "operator_approved": False},
        )

    judge_name = "graf/evaluation/meeting-outcome-faithfulness"
    judge_type, judge_prompt, judge_config = CONTROL_PROMPTS[judge_name]
    judge = validate_prompt_snapshot(
        name=judge_name,
        version=3,
        prompt_type=judge_type,
        prompt=judge_prompt,
        config=judge_config,
    )
    judge_evidence = {
        "evaluator_version": "judge-v1",
        "operator_actor_id": "deploy-operator",
        "operator_approved": True,
        "calibration_manifest_hash": "a" * 64,
        "expected_labels": ["pass", "fail"] * 5,
        "actual_labels": ["pass", "fail"] * 5,
        "agreement_threshold": 0.9,
        "invalid_output_count": 0,
        "bounded_cost_smoke_passed": True,
    }
    aggregate = validate_control_prompt_gate(candidate=judge, evidence=judge_evidence)
    assert aggregate["agreement"] == 1
    gated = validate_prompt_snapshot(
        name=judge_name,
        version=4,
        prompt_type=judge_type,
        prompt=judge_prompt,
        config={
            **judge_config,
            CONTROL_GATE_CONFIG_KEY: {
                **aggregate,
                "evidence_hash": "b" * 64,
                "gate_version": 1,
                "operator_approved": True,
            },
        },
    )
    calibration, gate = required_judge_calibration(gated)
    assert calibration.passed
    assert gate["evaluator_version"] == "judge-v1"
    with pytest.raises(PromptOptimizationError, match="judge_control_prompt_gate_failed"):
        validate_control_prompt_gate(
            candidate=judge,
            evidence={**judge_evidence, "actual_labels": ["fail", "pass"] * 5},
        )


def test_control_promotion_persists_gate_in_exact_langfuse_prompt_version() -> None:
    from langfuse.api.commons.errors.not_found_error import NotFoundError

    judge_name = "graf/evaluation/meeting-outcome-faithfulness"
    judge_type, judge_prompt, judge_config = CONTROL_PROMPTS[judge_name]

    class Client:
        def __init__(self) -> None:
            self.production = False
            self.gated = None

        def get_prompt(self, _name, **kwargs):
            if kwargs.get("version") == 2:
                return Mock(version=2, prompt=judge_prompt, config=judge_config)
            if kwargs.get("version") == 3 or (
                kwargs.get("label") == "production" and self.production
            ):
                return self.gated
            raise NotFoundError(body={})

        def create_prompt(self, **kwargs):
            self.gated = Mock(version=3, prompt=kwargs["prompt"], config=kwargs["config"])
            return self.gated

        def update_prompt(self, **_kwargs):
            self.production = True

        def clear_prompt_cache(self):
            pass

    evidence = {
        "evaluator_version": "judge-v9",
        "operator_actor_id": "deploy-operator",
        "operator_approved": True,
        "calibration_manifest_hash": "a" * 64,
        "expected_labels": ["pass", "fail"] * 5,
        "actual_labels": ["pass", "fail"] * 5,
        "agreement_threshold": 0.9,
        "invalid_output_count": 0,
        "bounded_cost_smoke_passed": True,
    }
    client = Client()

    promoted, aggregate = promote_control_prompt(
        client,
        prompt_name=judge_name,
        prompt_type=judge_type,
        candidate_version=2,
        expected_source_version=None,
        evidence=evidence,
        protected_label_capability_verified=True,
    )

    gate = promoted.config[CONTROL_GATE_CONFIG_KEY]
    assert promoted.version == 3
    assert aggregate["evaluator_version"] == "judge-v9"
    assert gate["evaluator_version"] == "judge-v9"
    assert gate["evidence_hash"] == control_gate_evidence_hash(evidence)


def test_control_promotion_returns_the_exact_embedded_evidence_hash(monkeypatch) -> None:
    from twobrain_rec_server.cli import langfuse_prompts as cli_module

    evidence = {
        "evaluator_version": "reflection-v1",
        "operator_actor_id": "deploy-operator",
        "operator_approved": True,
        "native_parser_smoke_passed": True,
        "variable_preservation_passed": True,
        "anti_copy_regression_passed": True,
        "bounded_cost_smoke_passed": True,
    }
    embedded_hash = control_gate_evidence_hash(evidence)

    class Observation:
        def end(self):
            pass

    class Client:
        def start_observation(self, **_kwargs):
            return Observation()

        def flush(self):
            pass

        def shutdown(self):
            pass

    monkeypatch.setattr("langfuse.Langfuse", lambda **_kwargs: Client())
    monkeypatch.setattr(
        cli_module,
        "promote_control_prompt",
        lambda *_args, **_kwargs: (
            Mock(
                version=9,
                config={CONTROL_GATE_CONFIG_KEY: {"evidence_hash": embedded_hash}},
            ),
            {"passed": True},
        ),
    )

    result = promote_control_prompt_version(
        base_url="https://langfuse.invalid",
        public_key="pk-test",
        secret_key="sk-test",
        prompt_name="graf/prompt-optimization/reflection",
        candidate_version=8,
        expected_source_version=7,
        evidence=evidence,
        protected_label_capability_verified=True,
    )

    assert result["evidence_hash"] == embedded_hash


def test_optimizer_terminal_observation_retries_with_one_deterministic_identity() -> None:
    run_id = UUID("10000000-0000-0000-0000-000000000001")

    class Observation:
        def end(self):
            pass

    class Client:
        def __init__(self) -> None:
            self.calls = []

        def start_observation(self, **kwargs):
            self.calls.append(kwargs)
            return Observation()

        def flush(self):
            pass

    client = Client()
    terminal = {
        "aggregate_scores": {"heldout": 0.2},
        "failure_code": None,
        "prompt_name": "graf/meeting-outcome/auto",
        "status": "cancelled",
    }

    _publish_optimization_terminal_observation(client, run_id=run_id, terminal=terminal)
    _publish_optimization_terminal_observation(client, run_id=run_id, terminal=terminal)

    assert len(optimization_terminal_observation_id(run_id)) == 16
    assert optimization_terminal_observation_id(run_id) == optimization_terminal_observation_id(
        run_id
    )
    assert [call["output"] for call in client.calls] == [terminal, terminal]
    assert all(call["metadata"]["terminal"] is True for call in client.calls)
