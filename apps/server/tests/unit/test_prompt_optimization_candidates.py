"""The optimizer can create candidates, never authorize production changes."""

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from twobrain_rec_server.cli import langfuse_prompts
from twobrain_rec_server.cli import prompt_optimization as cli
from twobrain_rec_server.outcomes import prompt_optimization as optimizer
from twobrain_rec_server.workflows import prompt_optimization_workflow as workflows


@pytest.mark.anyio
async def test_root_operator_cli_requires_confirmation_and_is_independent_of_optimizer(monkeypatch, tmp_path):
    from twobrain_rec_server.config import Settings

    args = cli.build_parser().parse_args([
        "promote-root", "--actor-id", "synthetic-operator", "--operation-id", str(uuid4()),
        "--run-id", str(uuid4()), "--expected-source-version", "1", "--workdir", str(tmp_path),
        "--source-host", "example.invalid", "--source-container", "synthetic",
    ])
    create_db = Mock(return_value=(SimpleNamespace(dispose=AsyncMock()), Mock()))
    monkeypatch.setattr(cli, "create_prompt_optimization_database", create_db)
    monkeypatch.setattr(cli, "verify_prompt_optimization_database_identity", AsyncMock())
    promote = AsyncMock(return_value={"state": "succeeded"})
    monkeypatch.setattr(cli, "_promote_root", promote, raising=False)
    with pytest.raises(RuntimeError, match="confirmation_required"):
        await cli.run_command(args, settings=Settings(prompt_optimization_enabled=False))
    create_db.assert_not_called()
    args.confirm = True
    assert await cli.run_command(args, settings=Settings(prompt_optimization_enabled=False)) == {"state": "succeeded"}
    promote.assert_awaited_once()


@pytest.mark.anyio
@pytest.mark.parametrize("failure,completed", [(False, False), (True, False), (False, True)])
async def test_root_cli_calls_single_writer_and_closes_resources(monkeypatch, tmp_path, failure, completed):
    from pathlib import Path

    from twobrain_rec_server.cli.meeting_protocol_eval import PrivateWorkdir
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db import session
    from twobrain_rec_server.outcomes import prompt_bundle

    workdir = PrivateWorkdir.create(tmp_path, Path.cwd())
    workdir.write_json("evaluation-settings.json", {"env": "protocol-evaluation"})
    checks = {"approved_at": datetime.now(UTC).isoformat(), "protected_label": {}, "sole_mutation_credential": {}}
    workdir.write_json("operator-checks.json", checks)
    args = SimpleNamespace(workdir=workdir.path, source_host="example.invalid", source_container="synthetic",
                           operation_id=uuid4(), run_id=uuid4(), actor_id="operator", expected_source_version=1)
    engine = SimpleNamespace(dispose=AsyncMock())
    sessions = Mock()
    monkeypatch.setattr(session, "create_engine", lambda _: engine)
    monkeypatch.setattr(session, "create_sessionmaker", lambda _: sessions)
    client = Mock()
    monkeypatch.setattr(cli, "create_langfuse_client", lambda _: client)
    close = Mock()
    monkeypatch.setattr(cli, "shutdown_langfuse", close)
    event = SimpleNamespace(operation_id=str(args.operation_id), target=SimpleNamespace(
        root_version=4, root_export=SimpleNamespace(hash="a" * 64)))
    writer = AsyncMock(return_value=event, side_effect=RuntimeError("private evidence") if failure else None)
    monkeypatch.setattr(prompt_bundle, "promote_root_bundle", writer)
    db = SimpleNamespace(get=AsyncMock(return_value=SimpleNamespace(state="succeeded") if completed else None))
    context = AsyncMock()
    context.__aenter__.return_value = db
    operator_sessions = Mock(return_value=context)
    if completed:
        args.workdir = tmp_path / "already-cleaned"
        monkeypatch.setattr(cli, "create_langfuse_client", Mock(side_effect=AssertionError("unexpected live client")))
    if failure:
        with pytest.raises(RuntimeError):
            await cli._promote_root(args, settings=Settings(), sessionmaker=operator_sessions)
    else:
        assert await cli._promote_root(args, settings=Settings(), sessionmaker=operator_sessions) == {
            "state": "succeeded", "operation_id": str(args.operation_id), "root_version": 4,
            "root_export_hash": "a" * 64,
        }
    writer.assert_awaited_once()
    assert writer.await_args.args == (operator_sessions,)
    assert writer.await_args.kwargs["evaluation_sessionmaker"] is (None if completed else sessions)
    assert writer.await_args.kwargs["approved_at"] == ("" if completed else checks["approved_at"])
    assert "qualification" not in writer.await_args.kwargs
    if completed:
        engine.dispose.assert_not_awaited()
        close.assert_not_called()
    else:
        engine.dispose.assert_awaited_once()
        close.assert_called_once_with(client)


@pytest.mark.parametrize("reconciliation", [False, True])
def test_root_cli_never_prints_private_exception(monkeypatch, capsys, reconciliation):
    from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

    args = SimpleNamespace(command="promote-root")
    monkeypatch.setattr(cli, "build_parser", lambda: SimpleNamespace(parse_args=lambda: args))
    error = PromptBundleError("root_promotion_reconciliation_required") if reconciliation else RuntimeError("private evidence")
    monkeypatch.setattr(cli, "run_command", AsyncMock(side_effect=error))
    monkeypatch.setattr(cli.logging, "disable", Mock())
    with pytest.raises(SystemExit) as caught:
        cli.main()
    assert caught.value.code == 1
    expected = ('{"state": "reconciliation_required", "failure_code": "root_promotion_reconciliation_required"}'
                if reconciliation else '{"state": "failed", "failure_code": "root_promotion_command_failed"}')
    assert capsys.readouterr().out.strip() == expected


def test_root_replay_parser_does_not_require_cleaned_up_evaluation_inputs():
    args = cli.build_parser().parse_args([
        "promote-root", "--actor-id", "operator", "--operation-id", str(uuid4()),
        "--run-id", str(uuid4()), "--expected-source-version", "1", "--confirm",
    ])
    assert args.workdir is args.source_host is args.source_container is None


@pytest.mark.parametrize("command", ["approve", "reject", "expire", "rollback"])
def test_optimizer_cli_has_no_child_decision_commands(command):
    with pytest.raises(SystemExit) as caught:
        cli.build_parser().parse_args([command, "10000000-0000-0000-0000-000000000001"])
    assert caught.value.code == 2
    assert command not in cli.build_parser().format_help()


@pytest.mark.parametrize("option", ["--promote-control", "--promote-root-bundle-version"])
def test_langfuse_cli_rejects_old_promotion_before_reading_credentials(monkeypatch, option):
    monkeypatch.setattr("sys.argv", [
        "langfuse-prompts", "--public-key-file", "/synthetic/missing-public",
        "--secret-key-file", "/synthetic/missing-secret", option,
        "graf/prompt-optimization/reflection" if option == "--promote-control" else "2",
    ])
    with pytest.raises(SystemExit) as caught:
        langfuse_prompts.main()
    assert caught.value.code == 2


def test_obsolete_production_writers_and_child_lkg_are_removed():
    for name in (
        "move_production_label", "promote_control_prompt", "control_gate_evidence_hash",
        "validate_control_prompt_gate", "persist_verified_promoted_snapshot",
        "load_verified_promoted_snapshot", "build_verified_promoted_snapshot",
        "promoted_snapshot_object_key", "_publish_label_transition",
    ):
        assert not hasattr(optimizer, name), name
    assert not hasattr(langfuse_prompts, "promote_control_prompt_version")
    assert not hasattr(langfuse_prompts, "promote_root_bundle_candidate")
    assert not hasattr(langfuse_prompts, "promote_root_bundle_label")


def test_root_cli_single_version_includes_extraction_and_verification(monkeypatch, capsys):
    from pathlib import Path

    from twobrain_rec_server.outcomes.prompt_bundle import OUTCOME_PROMPT_NAMES

    monkeypatch.setattr("sys.argv", [
        "langfuse-prompts", "--public-key-file", "/synthetic/public",
        "--secret-key-file", "/synthetic/secret", "--create-root-bundle",
        "--root-child-version", "7",
    ])
    monkeypatch.setattr(Path, "read_text", lambda *_args, **_kwargs: "synthetic-credential")
    create = Mock(return_value={"root_prompt_version": 8})
    monkeypatch.setattr(langfuse_prompts, "create_root_bundle_candidate", create)
    langfuse_prompts.main()
    assert create.call_args.kwargs["child_versions"] == {name: 7 for name in OUTCOME_PROMPT_NAMES}
    assert "synthetic-credential" not in capsys.readouterr().out


@pytest.mark.anyio
@pytest.mark.parametrize("name", [
    "authorize_prompt_optimization_action_activity", "authorize_prompt_rollback_action_activity",
    "promote_prompt_candidate_activity", "rollback_prompt_production_label_activity",
])
async def test_retired_activity_cannot_read_or_mutate_external_state(monkeypatch, name):
    settings = Mock(side_effect=AssertionError("retired activity accessed runtime"))
    monkeypatch.setattr("twobrain_rec_server.config.get_settings", settings)
    function = getattr(optimizer, name)
    if name.startswith("authorize_"):
        assert await function({}) == {"status": "denied"}
    else:
        with pytest.raises(optimizer.PromptOptimizationError, match="root_promotion_required"):
            await function({})
    settings.assert_not_called()


@pytest.mark.anyio
@pytest.mark.parametrize("status", ["candidate", "completed", "promoted", "rolled_back",
                                   "rejected", "expired", "failed", "cancelled"])
async def test_finished_run_cannot_reserve_new_inference(status):
    run = SimpleNamespace(deployment_scope="global", status=status)
    db = SimpleNamespace(scalar=AsyncMock(return_value=run),
                         scalars=AsyncMock(return_value=SimpleNamespace(all=lambda: [])), flush=AsyncMock())
    with pytest.raises(optimizer.PromptOptimizationError, match="optimization_run_not_active"):
        await optimizer.reserve_persisted_call(
            db, run_id=uuid4(), call_key="synthetic", phase="task", prompt_version=1,
            config_hash="a" * 64, model_route="synthetic", token_ceiling=1,
            cost_ceiling=Decimal(0), activity_attempt=1, now=datetime.now(UTC),
        )
    # Reading retained calls remains allowed; only a new reservation is forbidden.
    db.scalars.assert_awaited_once()
    db.flush.assert_not_called()


@pytest.mark.anyio
async def test_new_workflow_finishes_with_candidate_without_approval_or_label_mutation(monkeypatch):
    calls = []

    async def execute(name, payload, **_options):
        calls.append(name)
        if name == "resolve_prompt_optimization_contract_activity":
            return {"source_prompt_version": 1, "rollback_prompt_version": 1}
        if name in {"run_gepa_prompt_optimization_activity", "validate_heldout_prompt_candidate_activity"}:
            return {"hard_gates_passed": True, "temporal_history": {
                "phase": "evolution" if name.startswith("run_gepa") else "heldout", "chunk_count": 1,
            }}
        if name in {"snapshot_prompt_optimization_history_chunk_activity",
                    "finalize_prompt_optimization_history_materialization_activity"}:
            return {}
        if name == "publish_prompt_candidate_activity":
            assert "approval_expires_at" not in payload
            return {"candidate_prompt_version": 2}
        if name == "finalize_prompt_optimization_activity":
            assert payload["status"] == "completed"
            return {"status": "completed"}
        raise AssertionError(name)

    monkeypatch.setattr(workflows, "workflow", SimpleNamespace(
        execute_activity=execute, patched=lambda _id: True,
        now=lambda: datetime.now(UTC), unsafe=SimpleNamespace(is_replaying=lambda: False),
    ))
    instance = workflows.PromptOptimizationWorkflow()
    assert await instance.run({"run_id": "synthetic"}) == {"status": "completed"}
    before = list(calls)
    assert await instance.decide({"action_id": "synthetic", "decision": "approved"}) == "denied"
    assert calls == before
    assert instance.status()["approval_state"] == "not_requested"
