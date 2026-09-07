from __future__ import annotations

import asyncio
import threading
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID

import pytest

from tests.fixtures.outcome_prompts import desired_prompts
from twobrain_rec_server.cli.langfuse_prompts import (
    create_root_bundle_candidate,
    sync_prompts,
)
from twobrain_rec_server.outcomes.prompt_bundle import (
    snapshot_bundle_metadata,
)
from twobrain_rec_server.outcomes.prompt_optimization import (
    OUTCOME_EVAL_METRIC_THRESHOLDS,
    OptimizationCandidate,
    PromptOptimizationError,
    SyntheticExample,
    SyntheticManifest,
    _commit_database_until_quiescent,
    _publish_optimization_terminal_observation,
    _snapshot_from_payload,
    _snapshot_payload,
    load_persisted_candidate_result,
    optimization_terminal_observation_id,
    parse_reflection_proposal,
    prompt_config_hash,
    publish_or_recover_unlabelled_candidate,
    publish_prompt_candidate_activity,
    publish_unlabelled_candidate,
    validate_candidate_prompt,
    validate_heldout_candidate,
    validate_outcome_eval_receipt,
)
from twobrain_rec_server.outcomes.prompts import (
    CONTROL_GATE_CONFIG_KEY,
    canonical_json,
    validate_prompt_snapshot,
)

CONTROL_PROMPTS = {
    name: value for name, value in desired_prompts().items()
    if not name.startswith("graf/meeting-outcome/")
}


@pytest.mark.anyio
@pytest.mark.parametrize(
    ("operation", "expected_status"),
    [
        ("candidate", "cancelled"),
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
            state["database"] = "candidate"
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
    run_id = UUID("10000000-0000-0000-0000-000000000001")
    run = SimpleNamespace(
        id=run_id,
        status="candidate" if operation == "persisted_candidate" else "running",
        approval_state="not_requested",
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
        aggregate_scores={},
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
        return candidate

    monkeypatch.setattr(
        optimization_module,
        "_run_thread_until_quiescent",
        return_snapshot,
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
    }

    with pytest.raises(RuntimeError, match="database commit lost"):
        await publish_prompt_candidate_activity(payload)
    result = await publish_prompt_candidate_activity(payload)

    assert result["candidate_prompt_version"] == 2
    assert run.status == "candidate"
    assert run.approval_state == "not_requested"
    assert run.approval_expires_at is None
    assert result["approval_expires_at"] is None
    client.create_prompt.assert_called_once()
    assert client.create_prompt.call_args.kwargs["labels"] == []


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["completed", "promoted", "rolled_back", "failed", "cancelled"])
async def test_finished_run_callback_cannot_create_a_candidate(monkeypatch, status):
    source = _source()
    client = Mock()
    run = SimpleNamespace(
        status=status, source_prompt_version=source.version, candidate_prompt_version=None,
        candidate_prompt_hash=None, candidate_config_hash=None, approval_expires_at=None,
    )
    _install_prompt_transition_activity_fakes(
        monkeypatch, run=run, client=client, storage=SimpleNamespace(),
    )
    with pytest.raises(PromptOptimizationError, match="optimization_run_not_active"):
        await publish_prompt_candidate_activity({
            "run_id": "10000000-0000-0000-0000-000000000001",
            "resolved_contract": {"source_prompt": _snapshot_payload(source)},
            "optimization_result": {"prompt_text": canonical_json(source.prompt)},
            "heldout_result": {"hard_gates_passed": True},
        })
    assert client.mock_calls == []
    assert run.status == status


@pytest.mark.parametrize("bootstrap", [False, True])
def test_prompt_sync_creates_only_unlabelled_candidates(monkeypatch, bootstrap) -> None:
    import langfuse

    from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME

    class Client:
        def __init__(self) -> None:
            self.created = []

        def get_prompt(self, name, **kwargs):
            assert "label" not in kwargs
            assert kwargs["version"] == 7
            if bootstrap:
                assert name != EXTRACTOR_PROMPT_NAME  # The new child does not exist yet.
            return Mock(version=7, prompt="previous prompt", config={
                "config_contract_version": 3,
                "model": "gemini/gemini-3.8-flash",
                "top_p": 0.7, "max_tokens": 12000,
                CONTROL_GATE_CONFIG_KEY: {"old_evidence": "must-not-be-carried"},
            })

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
        source_versions={name: 7 for name in desired_prompts()},
        source_names={EXTRACTOR_PROMPT_NAME: "graf/meeting-outcome/auto"} if bootstrap else None,
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
    assert sum(value.startswith("created-outcome-candidate:") for value in outcomes) == 12
    assert all(row["config"]["model"] == "gemini/gemini-3.8-flash" for row in client.created)
    assert all(row["config"]["top_p"] == 0.7 for row in client.created)
    assert all(row["config"]["max_tokens"] == 12000 for row in client.created)
    assert all("temperature" not in row["config"] for row in client.created)
    assert all("reasoning_effort" not in row["config"] for row in client.created)
    assert all(CONTROL_GATE_CONFIG_KEY not in row["config"] for row in client.created)


@pytest.mark.parametrize("failure", ["missing-model", "wrong-version", "unknown-field"])
def test_prompt_sync_validates_all_exact_sources_before_any_write(monkeypatch, failure) -> None:
    import langfuse

    class Client:
        create_prompt = Mock()

        def get_prompt(self, name, **kwargs):
            assert "label" not in kwargs
            config = {"config_contract_version": 1, "model": "test-model"}
            version = kwargs["version"]
            if name == list(desired_prompts())[-1]:
                if failure == "missing-model":
                    del config["model"]
                elif failure == "wrong-version":
                    version += 1
                else:
                    config["base_url"] = "https://example.invalid"
            return Mock(version=version, prompt="previous prompt", config=config)

        def flush(self) -> None:
            pass

        def shutdown(self) -> None:
            pass

    client = Client()
    monkeypatch.setattr(langfuse, "Langfuse", lambda **_kwargs: client)
    with pytest.raises(ValueError):
        sync_prompts(
            base_url="https://langfuse.invalid", public_key="pk-test", secret_key="sk-test",
            apply=True, source_versions={name: 7 for name in desired_prompts()},
        )
    client.create_prompt.assert_not_called()


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
    result = create_root_bundle_candidate(
        base_url="https://langfuse.invalid",
        public_key="pk-test",
        secret_key="sk-test",
        child_versions=versions,
    )

    assert result["root_prompt_version"] == 31
    assert result["child_versions"] == dict(sorted(versions.items()))
    assert sorted(calls) == sorted(versions.items())


def test_optimizer_snapshot_and_candidate_retain_root_binding() -> None:
    from tests.fixtures.meeting_protocol import protocol_bundle

    bound = protocol_bundle().child("graf/meeting-outcome/auto")

    restored = _snapshot_from_payload(_snapshot_payload(bound))
    candidate = validate_candidate_prompt(bound, canonical_json(bound.prompt))

    assert snapshot_bundle_metadata(restored) == snapshot_bundle_metadata(bound)
    assert snapshot_bundle_metadata(candidate) == snapshot_bundle_metadata(bound)
    changed = [dict(message) for message in bound.prompt]
    changed[0]["content"] += " Additional synthetic emphasis."
    counterfactual = validate_candidate_prompt(bound, canonical_json(changed))
    assert snapshot_bundle_metadata(counterfactual) is None
    assert counterfactual.config == bound.config


def test_production_optimizer_uses_secret_file_and_standard_gateway(
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
