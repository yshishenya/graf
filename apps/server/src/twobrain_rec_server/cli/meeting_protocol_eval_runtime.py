"""Run the existing meeting workflow on an isolated evaluation database/queue."""

from __future__ import annotations

import argparse
import asyncio
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import select, text
from temporalio import activity
from temporalio.client import WorkflowFailureError
from temporalio.common import WorkflowIDReusePolicy
from temporalio.exceptions import WorkflowAlreadyStartedError
from temporalio.worker import Worker

from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import (
    GenerationCall,
    MeetingOutcomeGenerationAttempt,
    MeetingOutcomeSet,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.observability.langfuse import create_langfuse_client, shutdown_langfuse
from twobrain_rec_server.outcomes import ai_service
from twobrain_rec_server.outcomes.prompt_bundle import (
    PromptBundleError,
    build_evaluation_snapshot,
    fetch_root_bundle_by_label,
    fetch_root_bundle_by_version,
    load_execution_authority,
    validate_evaluation_snapshot,
)
from twobrain_rec_server.workflows.outcome_generation_workflow import (
    OutcomeGenerationWorkflow,
    OutcomeObservabilityReconcilerWorkflow,
)
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
    outcome_generation_task_queue,
)

GENERATION_WAIT_SECONDS = 30 * 60
OBSERVER_WAIT_SECONDS = 60


def _require_evaluation_root(attempt, settings: Settings) -> None:
    # Only a fresh active candidate may resolve its root for the first time.
    if (
        attempt.prompt_version is None
        and (attempt.metadata_json or {}).get("prompt_bundle") is None
        and attempt.status in ai_service.ACTIVE_CANDIDATE_STATUSES
    ):
        return
    try:
        snapshot = ai_service._stored_prompt_snapshot(attempt)
        if (
            snapshot is None
            or type(snapshot.root_prompt_version) is not int
            or snapshot.root_prompt_version != settings.outcome_root_prompt_version
        ):
            raise ValueError
    except (ValueError, ai_service.OutcomeGenerationTerminalError):
        raise ai_service.OutcomeGenerationTerminalError("evaluation_root_mismatch") from None


async def verify_isolated_runtime(settings: Settings, sessionmaker, run_id: UUID, *, unresolved=False) -> None:
    """Require an exact per-run database and queue, not just a nonproduction flag."""
    if (
        settings.env != "protocol-evaluation"
        or settings.langfuse_environment != "protocol-evaluation"
        or (settings.outcome_root_prompt_version is None and not unresolved)
        or settings.temporal_task_queue != f"graf-protocol-eval-{run_id.hex}"
        or settings.prompt_optimization_enabled
    ):
        raise ai_service.OutcomeGenerationTerminalError("evaluation_isolation_required")
    async with sessionmaker() as db:
        name = await db.scalar(text("select current_database()"))
        if name != f"graf_protocol_eval_{run_id.hex}":
            raise ai_service.OutcomeGenerationTerminalError("evaluation_database_mismatch")


async def pin_evaluation_run(settings, sessionmaker, workdir, run_id):
    """Resolve dev once, then use the exclusive run-owned export even across restarts."""
    await verify_isolated_runtime(settings, sessionmaker, run_id, unresolved=True)
    if not settings.langfuse_project_id:
        raise ai_service.OutcomeGenerationTerminalError("evaluation_project_required")
    name = "root-authority.json"
    try:
        if (workdir.path / name).exists():
            saved = workdir.read_json(name)
        else:
            if settings.outcome_root_prompt_version is None and settings.outcome_prompt_label != "dev":
                raise ai_service.OutcomeGenerationTerminalError("evaluation_selector_required")
            client = create_langfuse_client(settings)
            try:
                def resolve():
                    projects = client.api.projects.get(request_options={"timeout_in_seconds": 30, "max_retries": 0})
                    if {project.id for project in projects.data} != {settings.langfuse_project_id}:
                        raise PromptBundleError("evaluation_project_mismatch")
                    if settings.outcome_root_prompt_version is not None:
                        return fetch_root_bundle_by_version(client, version=settings.outcome_root_prompt_version)
                    return fetch_root_bundle_by_label(client, label="dev")

                bundle = await asyncio.to_thread(resolve)
            finally:
                shutdown_langfuse(client)
            sample = workdir.read_json("sample-manifest.json") if (workdir.path / "sample-manifest.json").exists() else None
            if sample is not None:
                async with sessionmaker() as db:
                    if await db.scalar(select(GenerationCall.id).limit(1)) is not None:
                        raise ai_service.OutcomeGenerationTerminalError("evaluation_sample_late")
            saved = build_evaluation_snapshot(bundle, project_id=settings.langfuse_project_id, run_id=run_id,
                                              sample_manifest=sample)
            workdir.write_json(name, saved)
        _, authority = validate_evaluation_snapshot(saved)
        from twobrain_rec_server.cli.meeting_protocol_eval import evaluation_sample
        evaluation_sample(workdir, run_id)
        if (authority["run_id"] != str(run_id) or authority["project_id"] != settings.langfuse_project_id
                or settings.outcome_root_prompt_version not in {None, authority["root_version"]}):
            raise PromptBundleError("evaluation_root_mismatch")
        pinned = settings.model_copy(update={
            "outcome_root_prompt_version": authority["root_version"],
            "outcome_evaluation_workdir": workdir.path,
        })
        async with sessionmaker() as db:
            await load_execution_authority(db, pinned, pinned=authority)
        return pinned
    except ai_service.OutcomeGenerationTerminalError:
        raise
    except Exception:
        raise ai_service.OutcomeGenerationTerminalError("evaluation_authority_invalid") from None


class EvaluationActivities:
    """Only the source guard differs; inference, ledger and verification are shared."""

    def __init__(self, settings: Settings, sessionmaker, source_reader):
        self.settings = settings
        self.sessionmaker = sessionmaker
        self.source_reader = source_reader

    async def guard(self, payload: dict[str, Any]) -> None:
        async with self.sessionmaker() as db:
            await ai_service._apply_worker_workspace(db, UUID(payload["workspace_id"]))
            attempt = await ai_service._candidate_attempt(
                db,
                UUID(payload["workspace_id"]),
                UUID(payload["candidate_id"]),
            )
            metadata = attempt.metadata_json or {}
            source = metadata.get("evaluation_source")
            if metadata.get("evaluation_only") is not True or not isinstance(source, dict):
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_binding_missing")
            _require_evaluation_root(attempt, self.settings)
        await self.source_reader.check(source["meeting_id"], source["snapshot_hash"])
        from twobrain_rec_server.cli.meeting_protocol_eval import (
            PrivateWorkdir,
            evaluation_sample,
            validate_sample_source,
        )
        workdir = PrivateWorkdir(self.settings.outcome_evaluation_workdir)
        sample = evaluation_sample(workdir, metadata["evaluation_run_id"])
        if sample is not None:
            snapshot = workdir.read_json(f"source-{source['meeting_id']}.json")
            if snapshot["source_hash"] != source["snapshot_hash"]:
                raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")
            validate_sample_source(sample, snapshot)

    @activity.defn(name="resolve_outcome_prompt_config_activity")
    async def resolve(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self.guard(payload)
        return await ai_service.resolve_candidate_prompt(
            self.sessionmaker,
            settings=self.settings,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
        )

    @activity.defn(name="snapshot_outcome_transcript_metadata_activity")
    async def metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self.guard(payload)
        metadata, _ = await ai_service.snapshot_candidate_transcript(
            self.sessionmaker,
            settings=self.settings,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
        )
        return metadata

    @activity.defn(name="snapshot_outcome_transcript_chunk_activity")
    async def chunk(self, payload: dict[str, Any]) -> dict[str, Any]:
        await self.guard(payload)
        _, chunks = await ai_service.snapshot_candidate_transcript(
            self.sessionmaker,
            settings=self.settings,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
        )
        index = payload["chunk_index"]
        if type(index) is not int or not 0 <= index < len(chunks):
            raise ai_service.OutcomeGenerationTerminalError("evaluation_chunk_invalid")
        return chunks[index]

    @activity.defn(name="execute_outcome_generation_activity")
    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        async def source_guard():
            await self.guard(payload)

        return await ai_service.execute_candidate_generation(
            self.sessionmaker,
            settings=self.settings,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
            expected_snapshot_hash=payload["snapshot_hash"],
            evaluation_source_guard=source_guard,
        )

    @activity.defn(name="finalize_outcome_generation_failure_activity")
    async def finalize(self, payload: dict[str, Any]) -> dict[str, Any]:
        await ai_service.finalize_candidate_generation_failure(
            self.sessionmaker,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
            failure_code=payload["failure_code"],
        )
        return {"candidate_id": payload["candidate_id"], "status": "failed"}

    @activity.defn(name="publish_outcome_observability_activity")
    async def publish(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Retained completed calls remain deliverable after deletion/revocation.
        info = activity.info()
        result = await ai_service.publish_candidate_generation_calls(
            self.sessionmaker,
            settings=self.settings,
            workspace_id=UUID(payload["workspace_id"]),
            candidate_id=UUID(payload["candidate_id"]),
            activity_attempt=info.attempt,
            temporal_workflow_id=payload.get("generation_workflow_id") or info.workflow_id,
            temporal_run_id=payload.get("generation_workflow_run_id") or info.workflow_run_id,
            temporal_activity_id=info.activity_id,
        )
        return {"candidate_id": payload["candidate_id"], **result}

    def worker(self, temporal_client) -> Worker:
        return Worker(
            temporal_client,
            task_queue=outcome_generation_task_queue(self.settings),
            workflows=[OutcomeGenerationWorkflow, OutcomeObservabilityReconcilerWorkflow],
            activities=[
                self.resolve,
                self.metadata,
                self.chunk,
                self.generate,
                self.finalize,
                self.publish,
            ],
            max_concurrent_activities=1,
        )


def save_once(workdir, name, document):
    target = workdir.path / name
    if target.exists():
        if workdir.read_json(name) != document:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_working_copy_conflict")
    else:
        workdir.write_json(name, document)


async def generate_one(*, settings, sessionmaker, source_reader, workdir, run_id, meeting_id):
    from twobrain_rec_server.cli.meeting_protocol_eval import purge_shadow_source

    settings = await pin_evaluation_run(settings, sessionmaker, workdir, run_id)
    try:
        return await _generate_one(
            settings=settings,
            sessionmaker=sessionmaker,
            source_reader=source_reader,
            workdir=workdir,
            run_id=run_id,
            meeting_id=meeting_id,
        )
    except ai_service.OutcomeGenerationTerminalError as exc:
        if str(exc) in {"evaluation_source_changed", "evaluation_source_unavailable"}:
            cleanup_failed = False
            for prefix in ("source", "output", "review", "inventory-notes", "exclusion"):
                try:
                    workdir.discard(f"{prefix}-{meeting_id}.json")
                except ai_service.OutcomeGenerationTerminalError:
                    cleanup_failed = True
            try:
                async with sessionmaker() as db:
                    await purge_shadow_source(db, meeting_id)
                    await db.commit()
            except Exception:
                cleanup_failed = True
            if cleanup_failed:
                raise ai_service.OutcomeGenerationTerminalError(
                    "evaluation_private_cleanup_failed"
                ) from None
        raise


async def _generate_one(*, settings, sessionmaker, source_reader, workdir, run_id, meeting_id):
    from twobrain_rec_server.cli.meeting_protocol_eval import (
        evaluation_sample,
        mirror_source,
        validate_sample_source,
    )

    snapshot = await source_reader.read(meeting_id)
    validate_sample_source(evaluation_sample(workdir, run_id), snapshot)
    await source_reader.check(meeting_id, snapshot["source_hash"])
    if (workdir.path / "inventory.json").exists():
        inventory = workdir.read_json("inventory.json")
        expected = next(
            (row for row in inventory["meetings"] if row["meeting_id"] == str(meeting_id)), None
        )
        if expected is None or expected["source_hash"] != snapshot["source_hash"]:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")
    if (workdir.path / f"source-{meeting_id}.json").exists() and workdir.read_json(
        f"source-{meeting_id}.json"
    )["source_hash"] != snapshot["source_hash"]:
        raise ai_service.OutcomeGenerationTerminalError("evaluation_source_changed")
    save_once(workdir, f"source-{meeting_id}.json", snapshot)
    async with sessionmaker() as db:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )
        )
        if attempt is None:
            attempt = await mirror_source(db, snapshot, run_id)
            await db.commit()
        if (
            (attempt.metadata_json or {}).get("evaluation_only") is not True
            or (attempt.metadata_json or {}).get("evaluation_run_id") != str(run_id)
            or (attempt.metadata_json or {}).get("evaluation_source")
            != {
                "meeting_id": str(meeting_id),
                "snapshot_hash": snapshot["source_hash"],
            }
        ):
            raise ai_service.OutcomeGenerationTerminalError("evaluation_source_binding_missing")
        _require_evaluation_root(attempt, settings)
        candidate_id, workspace_id = attempt.candidate_id, attempt.workspace_id
        payload = {
            **ai_service.summary_workflow_payload(attempt),
            "meeting_id": str(meeting_id),
            "workspace_id": str(workspace_id),
        }
    temporal = await connect_temporal_client(
        settings, identity=f"graf-protocol-eval:{run_id.hex}", outcome_tracing=True
    )
    activities = EvaluationActivities(settings, sessionmaker, source_reader)
    workflow_id = f"outcome-generation/{candidate_id}"
    async with activities.worker(temporal):
        try:
            handle = await temporal.start_workflow(
                OutcomeGenerationWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=outcome_generation_task_queue(settings),
                id_reuse_policy=WorkflowIDReusePolicy.REJECT_DUPLICATE,
            )
        except WorkflowAlreadyStartedError:
            handle = temporal.get_workflow_handle(workflow_id)
        # The durable attempt/call below contains the bounded failure code.
        try:
            async with asyncio.timeout(GENERATION_WAIT_SECONDS):
                with suppress(WorkflowFailureError):
                    await handle.result()
        except TimeoutError:
            raise ai_service.OutcomeGenerationTerminalError(
                "evaluation_generation_pending"
            ) from None
        # Delivery cannot postpone revocation cleanup. Retained calls are independently
        # recoverable even when this worker exits before Langfuse confirms delivery.
        try:
            async with asyncio.timeout(OBSERVER_WAIT_SECONDS):
                while True:
                    await source_reader.check(meeting_id, snapshot["source_hash"])
                    async with sessionmaker() as db:
                        calls = (
                            await db.scalars(
                                select(GenerationCall).where(
                                    GenerationCall.candidate_id == candidate_id
                                )
                            )
                        ).all()
                        pending = any(
                            ai_service._generation_call_is_publishable(call)
                            and call.export_status != "confirmed"
                            for call in calls
                        )
                    if not pending:
                        break
                    await asyncio.sleep(2)
        except TimeoutError:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_observer_pending") from None
    await source_reader.check(meeting_id, snapshot["source_hash"])
    async with sessionmaker() as db:
        attempt = await db.get(MeetingOutcomeGenerationAttempt, attempt.id)
        _require_evaluation_root(attempt, settings)
        outcome = (
            await db.get(MeetingOutcomeSet, attempt.outcome_set_id)
            if attempt.outcome_set_id
            else None
        )
        root = (attempt.metadata_json or {}).get("prompt_bundle", {})
        calls = (
            await db.scalars(
                select(GenerationCall)
                .where(
                    GenerationCall.candidate_id == candidate_id,
                )
                .order_by(GenerationCall.call_sequence, GenerationCall.provider_attempt)
            )
        ).all()
        result = {
            "run_id": str(run_id),
            "meeting_id": str(meeting_id),
            "candidate_id": str(candidate_id),
            "source_hash": snapshot["source_hash"],
            "root_hash": root.get("root_bundle_hash"),
            "output_hash": outcome.content_hash if outcome else None,
            "state": attempt.status,
            "failure_code": attempt.failure_code,
            "protocol": outcome.protocol_json if outcome else None,
            "calls": [
                {
                    "sequence": call.call_sequence,
                    "state": call.call_state,
                    "export_status": call.export_status,
                    "raw_response": call.raw_response_json,
                    "validated_result": call.validated_result_json,
                }
                for call in calls
            ],
        }
    save_once(workdir, f"output-{meeting_id}.json", result)
    return {key: value for key, value in result.items() if key not in {"protocol", "calls"}}


async def recover_observer(*, settings, sessionmaker, run_id, meeting_id):
    """Deliver retained calls after purge; never read source or register inference.

    Use a separate per-run queue so recovery cannot pick up abandoned generation
    tasks. The existing publisher replays the original root, even an older one.
    """
    await verify_isolated_runtime(settings, sessionmaker, run_id)
    async with sessionmaker() as db:
        attempt = await db.scalar(
            select(MeetingOutcomeGenerationAttempt).where(
                MeetingOutcomeGenerationAttempt.meeting_id == meeting_id,
            )
        )
        metadata = (attempt.metadata_json or {}) if attempt is not None else {}
        source = metadata.get("evaluation_source")
        if (
            metadata.get("evaluation_only") is not True
            or metadata.get("evaluation_run_id") != str(run_id)
            or not isinstance(source, dict)
            or source.get("meeting_id") != str(meeting_id)
        ):
            raise ai_service.OutcomeGenerationTerminalError("evaluation_source_binding_missing")
        if attempt.status in ai_service.ACTIVE_CANDIDATE_STATUSES:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_observer_candidate_active")
        candidate_id = attempt.candidate_id
        payload = {
            "candidate_id": str(candidate_id),
            "workspace_id": str(attempt.workspace_id),
            "generation_workflow_id": attempt.workflow_id,
            "generation_workflow_run_id": attempt.workflow_run_id,
        }
    temporal = await connect_temporal_client(
        settings, identity=f"graf-protocol-eval-observer:{run_id.hex}", outcome_tracing=True
    )
    activities = EvaluationActivities(settings, sessionmaker, None)
    queue = f"{outcome_generation_task_queue(settings)}-observer-recovery"
    async with Worker(
        temporal,
        task_queue=queue,
        workflows=[OutcomeObservabilityReconcilerWorkflow],
        activities=[activities.publish],
        max_concurrent_activities=1,
    ):
        workflow_id = f"outcome-observability-recovery/{candidate_id}"
        try:
            handle = await temporal.start_workflow(
                OutcomeObservabilityReconcilerWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=queue,
                id_reuse_policy=WorkflowIDReusePolicy.ALLOW_DUPLICATE,
            )
        except WorkflowAlreadyStartedError:
            handle = temporal.get_workflow_handle(workflow_id)
        try:
            async with asyncio.timeout(OBSERVER_WAIT_SECONDS):
                result = await handle.result()
        except (TimeoutError, WorkflowFailureError):
            raise ai_service.OutcomeGenerationTerminalError("evaluation_observer_pending") from None
    if result.get("candidate_terminal") is not True or result.get("pending_count") != 0:
        raise ai_service.OutcomeGenerationTerminalError("evaluation_observer_pending")
    return {"state": "observations_confirmed", "published_count": result["published_count"]}


def main():
    import json

    from twobrain_rec_server.cli.meeting_protocol_eval import (
        PrivateWorkdir,
        SourceReader,
        finalize_run,
    )

    parser = argparse.ArgumentParser(
        description="Private full-corpus protocol evaluation; never publishes outcomes"
    )
    parser.add_argument("command", choices=("inventory", "generate", "recover-observer", "report"))
    parser.add_argument("--source-host")
    parser.add_argument("--source-container")
    parser.add_argument("--workdir", type=Path)
    parser.add_argument("--run-id", required=True, type=UUID)
    parser.add_argument("--meeting-id", type=UUID)
    args = parser.parse_args()
    # SDK/SQL failures can include model content or bound parameters. Only explicit
    # bounded results below go to stdout; full call evidence remains in the ledger.
    logging.disable(logging.CRITICAL)

    async def run():
        if args.command != "recover-observer":
            if not args.workdir or not args.source_host or not args.source_container:
                raise ai_service.OutcomeGenerationTerminalError(
                    "evaluation_source_arguments_required"
                )
            workdir = PrivateWorkdir(args.workdir)
            reader = SourceReader(args.source_host, args.source_container)
        if args.command == "inventory":
            from collections import Counter

            inventory = await reader.inventory()
            save_once(
                workdir, "inventory.json", {"run_id": str(args.run_id), "meetings": inventory}
            )
            return {
                "total": len(inventory),
                "selection_status": dict(Counter(row["selection_status"] for row in inventory)),
            }
        if args.command != "report" and args.meeting_id is None:
            raise ai_service.OutcomeGenerationTerminalError("evaluation_meeting_id_required")
        settings = get_settings()
        engine = create_engine(settings)
        try:
            if args.command == "report":
                settings = await pin_evaluation_run(settings, create_sessionmaker(engine), workdir, args.run_id)
                result = await finalize_run(
                    settings, create_sessionmaker(engine), reader, workdir, args.run_id,
                )
                # Full identities belong to the private report/operator journal only.
                return {key: value for key, value in result.items() if key != "qualification_report"}
            if args.command == "recover-observer":
                return await recover_observer(
                    settings=settings,
                    sessionmaker=create_sessionmaker(engine),
                    run_id=args.run_id,
                    meeting_id=args.meeting_id,
                )
            return await generate_one(
                settings=settings,
                sessionmaker=create_sessionmaker(engine),
                source_reader=reader,
                workdir=workdir,
                run_id=args.run_id,
                meeting_id=args.meeting_id,
            )
        finally:
            await engine.dispose()

    try:
        result = asyncio.run(run())
        print(json.dumps(result, ensure_ascii=False))
        if args.command == "report" and result.get("complete") is not True:
            raise SystemExit(1)
    except Exception:
        # Never include exception repr: Pydantic, SQL and provider failures may carry content.
        print(json.dumps({"state": "failed", "failure_code": "evaluation_command_failed"}))
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()
