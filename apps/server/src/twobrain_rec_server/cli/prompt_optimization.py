from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

from sqlalchemy import delete

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import PromptOptimizationCallLedger, PromptOptimizationRun
from twobrain_rec_server.db.session import (
    create_prompt_optimization_database,
    verify_prompt_optimization_database_identity,
)
from twobrain_rec_server.observability.langfuse import create_langfuse_client, shutdown_langfuse
from twobrain_rec_server.outcomes.prompt_bundle import (
    fetch_root_bundle_by_label,
    snapshot_bundle_metadata,
)
from twobrain_rec_server.outcomes.prompt_optimization import (
    ADAPTER_VERSION,
    JUDGE_NAMES,
    OPTIMIZATION_HISTORY_MATERIALIZATION_KEY,
    OPTIMIZATION_HISTORY_STAGING_KEY,
    OPTIMIZER_VERSION,
    PromptOptimizationError,
    _snapshot_payload,
    prompt_config_hash,
    required_control_prompt_gate,
    required_judge_calibration,
    validate_history_materialization_certificate,
)
from twobrain_rec_server.outcomes.prompts import EXTRACTOR_PROMPT_NAME, validate_prompt_snapshot
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    prompt_optimization_workflow_id,
    start_prompt_optimization_workflow,
)

TERMINAL_RUN_STATUSES = {"rejected", "expired", "failed", "cancelled", "rolled_back", "completed"}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="GRAF deployment-global prompt optimization")
    subparsers = parser.add_subparsers(dest="command", required=True)
    start = subparsers.add_parser("start")
    start.add_argument("--actor-id", required=True)
    start.add_argument("--prompt-name", required=True)
    for split in ("train", "development", "heldout"):
        start.add_argument(f"--{split}-ref", required=True)
        start.add_argument(f"--{split}-hash", required=True)
        start.add_argument(f"--{split}-count", required=True, type=int)
    start.add_argument("--max-calls", required=True, type=int)
    start.add_argument("--max-tokens", required=True, type=int)
    start.add_argument("--max-cost", required=True, type=Decimal)
    start.add_argument("--deadline-hours", type=int, default=24)

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("run_id", type=UUID)
    purge = subparsers.add_parser("purge")
    purge.add_argument("run_id", type=UUID)
    purge.add_argument("--confirm", action="store_true")
    promote = subparsers.add_parser("promote-root", help="Admit one fully evaluated root; never a child prompt")
    promote.add_argument("--actor-id", required=True)
    promote.add_argument("--operation-id", required=True, type=UUID)
    promote.add_argument("--run-id", required=True, type=UUID)
    promote.add_argument("--expected-source-version", required=True, type=int)
    promote.add_argument("--workdir", type=Path, help="Required for a new operation, not a completed replay")
    promote.add_argument("--source-host")
    promote.add_argument("--source-container")
    promote.add_argument("--confirm", action="store_true")
    return parser


async def run_command(
    args: argparse.Namespace, *, settings: Settings | None = None
) -> dict[str, object]:
    settings = settings or get_settings()
    if args.command == "promote-root" and not args.confirm:
        raise RuntimeError("root_promotion_confirmation_required")
    if args.command != "promote-root" and not settings.prompt_optimization_enabled:
        raise RuntimeError("prompt optimization is disabled")
    actor_id = str(getattr(args, "actor_id", None) or "graf-prompt-optimization-cli")[:120]
    engine, sessionmaker = create_prompt_optimization_database(
        settings,
        actor_id=actor_id,
        reason_category="operator_cli",
    )
    try:
        await verify_prompt_optimization_database_identity(sessionmaker)
        if args.command == "promote-root":
            return await _promote_root(args, settings=settings, sessionmaker=sessionmaker)
        if args.command == "start":
            return await _start(args, settings=settings, sessionmaker=sessionmaker)
        if args.command == "inspect":
            async with sessionmaker() as db:
                run = await db.get(PromptOptimizationRun, args.run_id)
                if run is None:
                    raise RuntimeError("optimization run not found")
                return _run_metadata(run)
        if args.command == "purge":
            return await _purge(args, settings=settings, sessionmaker=sessionmaker)
        raise RuntimeError("unsupported optimizer command")
    finally:
        await engine.dispose()


async def _promote_root(args, *, settings, sessionmaker):
    from twobrain_rec_server.cli.meeting_protocol_eval import PrivateWorkdir, SourceReader
    from twobrain_rec_server.db.models import PromptRootPromotion
    from twobrain_rec_server.db.session import create_engine, create_sessionmaker
    from twobrain_rec_server.outcomes.prompt_bundle import promote_root_bundle

    # The writer still verifies the complete historical receipt under its lock.
    # This read only avoids requiring cleaned-up private inputs for a completed replay.
    async with sessionmaker() as db:
        previous = await db.get(PromptRootPromotion, args.operation_id)
        completed = previous is not None and previous.state == "succeeded"
    workdir = evaluation_settings = evaluation_sessions = reader = engine = client = None
    checks = {"approved_at": "", "protected_label": {}, "sole_mutation_credential": {}}
    try:
        if not completed:
            if not args.workdir or not args.source_host or not args.source_container:
                raise RuntimeError("root_operator_arguments_invalid")
            workdir = PrivateWorkdir(args.workdir)
            evaluation_settings = Settings(**workdir.read_json("evaluation-settings.json"))
            checks = workdir.read_json("operator-checks.json")
            if set(checks) != {"approved_at", "protected_label", "sole_mutation_credential"}:
                raise RuntimeError("root_operator_evidence_invalid")
            engine = create_engine(evaluation_settings)
            evaluation_sessions = create_sessionmaker(engine)
            reader = SourceReader(args.source_host, args.source_container)
            client = create_langfuse_client(settings)
        event = await promote_root_bundle(
            sessionmaker, settings=settings, client=client, operation_id=args.operation_id,
            expected_source_version=args.expected_source_version, operator_actor=args.actor_id,
            approved_at=checks["approved_at"], protected_label=checks["protected_label"],
            sole_mutation_credential=checks["sole_mutation_credential"],
            evaluation_settings=evaluation_settings, evaluation_sessionmaker=evaluation_sessions,
            source_reader=reader,
            workdir=workdir, run_id=args.run_id,
        )
        return {"state": "succeeded", "operation_id": event.operation_id,
                "root_version": event.target.root_version, "root_export_hash": event.target.root_export.hash}
    finally:
        try:
            if client is not None:
                shutdown_langfuse(client)
        finally:
            if engine is not None:
                await engine.dispose()


async def _start(
    args: argparse.Namespace, *, settings: Settings, sessionmaker
) -> dict[str, object]:
    refs = {split: getattr(args, f"{split}_ref") for split in ("train", "development", "heldout")}
    if any(not value.startswith("synthetic://") for value in refs.values()):
        raise RuntimeError("only synthetic dataset references are accepted")
    if (
        args.max_calls < 1
        or args.max_tokens < 1
        or args.max_cost < 0
        or not 1 <= args.deadline_hours <= 24
    ):
        raise RuntimeError("optimization budget is invalid")
    client = create_langfuse_client(settings)
    try:
        root_bundle = fetch_root_bundle_by_label(client)
        source = root_bundle.child(args.prompt_name)
        bundle_metadata = snapshot_bundle_metadata(source)
        if bundle_metadata is None:
            raise RuntimeError("production root bundle metadata is missing")
        extractor = root_bundle.child(EXTRACTOR_PROMPT_NAME)
        reflection = _fetch_snapshot(client, "graf/prompt-optimization/reflection", "text")
        judges = [_fetch_snapshot(client, name, "chat") for name in JUDGE_NAMES]
    finally:
        shutdown_langfuse(client)
    judge_gates = {
        item.name: required_judge_calibration(item)[1]
        for item in judges
    }
    reflection_gate = required_control_prompt_gate(
        reflection,
        expected_gate="reflection",
    )
    run_id = uuid4()
    workflow_id = prompt_optimization_workflow_id(str(run_id))
    deadline = datetime.now(UTC) + timedelta(hours=args.deadline_hours)
    manifest_hashes = {
        split: {"sha256": getattr(args, f"{split}_hash"), "count": getattr(args, f"{split}_count")}
        for split in ("train", "development", "heldout")
    }
    budget = {
        "max_calls": args.max_calls,
        "max_tokens": args.max_tokens,
        "max_cost": str(args.max_cost),
        "reflection_control_gate": reflection_gate,
        "root_bundle_binding": bundle_metadata,
        "extractor_prompt": _snapshot_payload(extractor),
    }
    async with sessionmaker() as db:
        run = PromptOptimizationRun(
            id=run_id,
            deployment_scope="global",
            initiated_by_actor_id=args.actor_id,
            prompt_name=source.name,
            source_prompt_version=source.version,
            source_config_hash=prompt_config_hash(source.config),
            train_dataset_ref=refs["train"],
            development_dataset_ref=refs["development"],
            heldout_dataset_ref=refs["heldout"],
            dataset_manifest_hashes=manifest_hashes,
            optimizer_version=OPTIMIZER_VERSION,
            adapter_version=ADAPTER_VERSION,
            metric_versions={
                name: str(judge_gates[name]["evaluator_version"])
                for name in JUDGE_NAMES
            },
            reflection_prompt_name=reflection.name,
            reflection_prompt_version=reflection.version,
            reflection_config_hash=prompt_config_hash(reflection.config),
            judge_prompt_refs=[
                {
                    "prompt_name": item.name,
                    "prompt_version": item.version,
                    "config_hash": prompt_config_hash(item.config),
                    "calibration_gate": judge_gates[item.name],
                }
                for item in judges
            ],
            budget=budget,
            deadline_at=deadline,
            workflow_id=workflow_id,
            rollback_prompt_version=source.version,
            status="queued",
        )
        db.add(run)
        await db.commit()
    temporal = await connect_temporal_client(
        settings,
        identity=f"graf-prompt-operator:{args.actor_id[:120]}",
        outcome_tracing=True,
    )
    payload = {
        "run_id": str(run_id),
        "workflow_id": workflow_id,
        "prompt_name": source.name,
        "dataset_manifest_hashes": manifest_hashes,
        "deadline_at": deadline.isoformat(),
        "budget": budget,
    }
    try:
        started = await start_prompt_optimization_workflow(
            temporal_client=temporal,
            settings=settings,
            workflow_id=workflow_id,
            payload=payload,
        )
    except Exception:
        async with sessionmaker() as db:
            run = await db.get(PromptOptimizationRun, run_id)
            if run is not None:
                run.status = "failed"
                run.failure_code = "temporal_start_failed"
                await db.commit()
        raise
    async with sessionmaker() as db:
        run = await db.get(PromptOptimizationRun, run_id)
        if run is not None:
            run.workflow_run_id = started.run_id
            await db.commit()
            return _run_metadata(run)
    raise RuntimeError("optimization run disappeared")


async def _purge(
    args: argparse.Namespace, *, settings: Settings, sessionmaker
) -> dict[str, object]:
    if not args.confirm:
        raise RuntimeError("purge requires --confirm")
    async with sessionmaker() as db:
        run = await db.get(PromptOptimizationRun, args.run_id)
        if run is None:
            return {"run_id": str(args.run_id), "status": "not_found"}
        if run.status not in TERMINAL_RUN_STATUSES:
            raise RuntimeError("only terminal synthetic runs can be purged")
        materialization = dict(
            (run.budget or {}).get(OPTIMIZATION_HISTORY_MATERIALIZATION_KEY, {})
        )
        staging = dict((run.budget or {}).get(OPTIMIZATION_HISTORY_STAGING_KEY, {}))
        incomplete_phases = []
        for phase in ("evolution", "heldout"):
            staging_certificate = staging.get(phase)
            materialization_certificate = materialization.get(phase)
            if staging_certificate is None and materialization_certificate is None:
                continue
            if staging_certificate != {"status": "started"}:
                incomplete_phases.append(phase)
                continue
            try:
                validate_history_materialization_certificate(
                    materialization_certificate,
                    phase=phase,
                )
            except PromptOptimizationError:
                incomplete_phases.append(phase)
        if incomplete_phases:
            return {
                "run_id": str(args.run_id),
                "status": "blocked_history_materialization",
                "incomplete_phases": incomplete_phases,
                "staging_plaintext_retained": True,
                "retained_observability": ["langfuse", "temporal_history"],
            }

    # Object storage is deleted first. If listing or any individual deletion
    # fails, the durable run row remains the cleanup authority for a safe retry.
    storage = get_storage(settings)
    prefix = f"_system/prompt-optimization/{args.run_id}/"
    deleted_object_count = 0
    for item in storage.client.list_objects(
        settings.minio_bucket,
        prefix=prefix,
        recursive=True,
    ):
        storage.delete_object(item.object_name)
        deleted_object_count += 1

    async with sessionmaker() as db:
        run = await db.get(PromptOptimizationRun, args.run_id, with_for_update=True)
        if run is None:
            return {
                "run_id": str(args.run_id),
                "status": "purged",
                "deleted_object_count": deleted_object_count,
                "retained_observability": ["langfuse", "temporal_history"],
            }
        if run.status not in TERMINAL_RUN_STATUSES:
            raise RuntimeError("only terminal synthetic runs can be purged")
        await db.execute(
            delete(PromptOptimizationCallLedger).where(
                PromptOptimizationCallLedger.run_id == args.run_id
            )
        )
        await db.delete(run)
        await db.commit()
    return {
        "run_id": str(args.run_id),
        "status": "purged",
        "deleted_object_count": deleted_object_count,
        "retained_observability": ["langfuse", "temporal_history"],
    }


def _fetch_snapshot(client, name: str, prompt_type: str):
    prompt = client.get_prompt(
        name,
        label="production",
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


def _run_metadata(run: PromptOptimizationRun) -> dict[str, object]:
    return {
        "run_id": str(run.id),
        "workflow_id": run.workflow_id,
        "prompt_name": run.prompt_name,
        "source_prompt_version": run.source_prompt_version,
        "candidate_prompt_version": run.candidate_prompt_version,
        "status": run.status,
        "approval_state": run.approval_state,
        "aggregate_scores": run.aggregate_scores,
        "failure_code": run.failure_code,
    }


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "promote-root":
        # Qualification reads private meetings. Do not expose SDK/SQL validation inputs.
        logging.disable(logging.CRITICAL)
        try:
            result = asyncio.run(run_command(args))
        except Exception as exc:
            from twobrain_rec_server.outcomes.prompt_bundle import PromptBundleError

            code = str(exc) if isinstance(exc, PromptBundleError) and str(exc) in {
                "root_promotion_reconciliation_required", "root_bundle_source_conflict",
                "root_operation_conflict", "root_qualification_incomplete", "root_operator_evidence_invalid",
            } else "root_promotion_command_failed"
            state = "reconciliation_required" if code == "root_promotion_reconciliation_required" else "failed"
            print(json.dumps({"state": state, "failure_code": code}))
            raise SystemExit(1) from None
    else:
        result = asyncio.run(run_command(args))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
