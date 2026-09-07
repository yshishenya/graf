from __future__ import annotations

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import delete, select

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import PromptOptimizationCallLedger, PromptOptimizationRun
from twobrain_rec_server.db.session import (
    create_prompt_optimization_database,
    verify_prompt_optimization_database_identity,
)
from twobrain_rec_server.observability.langfuse import create_langfuse_client, shutdown_langfuse
from twobrain_rec_server.outcomes.prompt_bundle import (
    bind_snapshot_from_metadata,
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
    prompt_config_hash,
    required_control_prompt_gate,
    required_judge_calibration,
    validate_history_materialization_certificate,
)
from twobrain_rec_server.outcomes.prompts import validate_prompt_snapshot
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.prompt_optimization_workflow import PromptOptimizationWorkflow
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    prompt_optimization_workflow_id,
    prompt_rollback_workflow_id,
    start_prompt_optimization_workflow,
    start_prompt_rollback_workflow,
)

TERMINAL_RUN_STATUSES = {"rejected", "expired", "failed", "cancelled", "rolled_back"}


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
    start.add_argument("--protected-label-capability-verified", action="store_true")

    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("run_id", type=UUID)
    for command in ("approve", "reject"):
        decision = subparsers.add_parser(command)
        decision.add_argument("run_id", type=UUID)
        decision.add_argument("--actor-id", required=True)
    expire = subparsers.add_parser("expire")
    expire.add_argument("run_id", type=UUID)
    rollback = subparsers.add_parser("rollback")
    rollback.add_argument("run_id", type=UUID)
    rollback.add_argument("--actor-id", required=True)
    purge = subparsers.add_parser("purge")
    purge.add_argument("run_id", type=UUID)
    purge.add_argument("--confirm", action="store_true")
    return parser


async def run_command(
    args: argparse.Namespace, *, settings: Settings | None = None
) -> dict[str, object]:
    settings = settings or get_settings()
    if not settings.prompt_optimization_enabled:
        raise RuntimeError("prompt optimization is disabled")
    actor_id = str(getattr(args, "actor_id", None) or "graf-prompt-optimization-cli")[:120]
    engine, sessionmaker = create_prompt_optimization_database(
        settings,
        actor_id=actor_id,
        reason_category="operator_cli",
    )
    try:
        await verify_prompt_optimization_database_identity(sessionmaker)
        if args.command == "start":
            return await _start(args, settings=settings, sessionmaker=sessionmaker)
        if args.command == "inspect":
            async with sessionmaker() as db:
                run = await db.get(PromptOptimizationRun, args.run_id)
                if run is None:
                    raise RuntimeError("optimization run not found")
                return _run_metadata(run)
        if args.command in {"approve", "reject"}:
            return await _decide(
                args,
                settings=settings,
                sessionmaker=sessionmaker,
                decision="approved" if args.command == "approve" else "rejected",
            )
        if args.command == "expire":
            async with sessionmaker() as db:
                run = await db.scalar(
                    select(PromptOptimizationRun)
                    .where(PromptOptimizationRun.id == args.run_id)
                    .with_for_update()
                )
                if run is None or run.approval_expires_at is None:
                    raise RuntimeError("optimization run is not awaiting approval")
                if datetime.now(UTC) < run.approval_expires_at:
                    raise RuntimeError("optimization approval has not expired")
                run.approval_state = "expired"
                run.status = "expired"
                await db.commit()
                return _run_metadata(run)
        if args.command == "rollback":
            return await _rollback(args, settings=settings, sessionmaker=sessionmaker)
        if args.command == "purge":
            return await _purge(args, settings=settings, sessionmaker=sessionmaker)
        raise RuntimeError("unsupported optimizer command")
    finally:
        await engine.dispose()


async def _start(
    args: argparse.Namespace, *, settings: Settings, sessionmaker
) -> dict[str, object]:
    if not args.protected_label_capability_verified:
        raise RuntimeError("protected production-label capability is required")
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
            raise RuntimeError("production root bundle has no route binding")
        reflection = bind_snapshot_from_metadata(
            _fetch_snapshot(client, "graf/prompt-optimization/reflection", "text"),
            bundle_metadata,
        )
        judges = [
            bind_snapshot_from_metadata(_fetch_snapshot(client, name, "chat"), bundle_metadata)
            for name in JUDGE_NAMES
        ]
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
        "protected_label_capability_verified": True,
        "reflection_control_gate": reflection_gate,
        "root_bundle_binding": bundle_metadata,
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


async def _decide(
    args: argparse.Namespace,
    *,
    settings: Settings,
    sessionmaker,
    decision: str,
) -> dict[str, object]:
    action_id = uuid4()
    async with sessionmaker() as db:
        run = await db.scalar(
            select(PromptOptimizationRun)
            .where(PromptOptimizationRun.id == args.run_id)
            .with_for_update()
        )
        if run is None or run.status != "candidate" or run.approval_state != "awaiting_human":
            raise RuntimeError("optimization run is not awaiting approval")
        if run.approval_expires_at is None or datetime.now(UTC) >= run.approval_expires_at:
            raise RuntimeError("optimization approval expired")
        run.approval_action_id = action_id
        run.approved_by_actor_id = args.actor_id
        await db.commit()
        workflow_id = run.workflow_id
    temporal = await connect_temporal_client(settings, outcome_tracing=True)
    handle = temporal.get_workflow_handle(workflow_id)
    result = await handle.execute_update(
        PromptOptimizationWorkflow.decide,
        {"action_id": str(action_id), "decision": decision},
    )
    return {"run_id": str(args.run_id), "action_id": str(action_id), "decision": result}


async def _rollback(
    args: argparse.Namespace, *, settings: Settings, sessionmaker
) -> dict[str, object]:
    action_id = uuid4()
    async with sessionmaker() as db:
        run = await db.get(PromptOptimizationRun, args.run_id, with_for_update=True)
        if run is None or run.status != "promoted" or run.candidate_prompt_version is None:
            raise RuntimeError("optimization run is not rollbackable")
        budget = dict(run.budget)
        budget["rollback_action"] = {
            "action_id": str(action_id),
            "actor_id": args.actor_id,
            "consumed": False,
        }
        run.budget = budget
        await db.commit()
        payload = {
            "run_id": str(run.id),
            "action_id": str(action_id),
            "prompt_name": run.prompt_name,
            "expected_current_version": run.candidate_prompt_version,
            "rollback_prompt_version": run.rollback_prompt_version,
        }
        workflow_id = prompt_rollback_workflow_id(str(run.id), run.rollback_prompt_version)
    temporal = await connect_temporal_client(settings, outcome_tracing=True)
    started = await start_prompt_rollback_workflow(
        temporal_client=temporal,
        settings=settings,
        workflow_id=workflow_id,
        payload=payload,
    )
    return {
        "run_id": str(args.run_id),
        "workflow_id": workflow_id,
        "run_id_temporal": started.run_id,
    }


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
    result = asyncio.run(run_command(build_parser().parse_args()))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
