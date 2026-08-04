#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import text

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    apply_tenant_context,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClient, MediaScribeClientError
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.submit import (
    poll_and_import_mediascribe_result,
    submit_to_mediascribe,
)
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.temporal_client import processing_workflow_id


@dataclass(frozen=True, slots=True)
class Candidate:
    meeting_id: UUID
    media_revision_id: UUID
    workspace_id: UUID
    organization_id: UUID
    user_id: UUID
    device_id: UUID
    workflow_status: str | None
    reason_code: str | None
    mediascribe_status: str | None
    has_external_job: bool
    request_mode: str | None


async def _find_candidates(engine, *, reason_code: str, meeting_id: UUID | None, limit: int) -> list[Candidate]:
    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="operator_diagnostics",
                actor_id="reprocess_manual_media_uploads.py",
                reason_category="manual_media_reprocess",
                feature_area="processing",
            ),
        )
        rows = (
            await conn.execute(
                text(
                    """
                    select
                        m.id as meeting_id,
                        mr.id as media_revision_id,
                        m.workspace_id,
                        w.organization_id,
                        m.created_by_user_id as user_id,
                        m.device_id,
                        pw.status as workflow_status,
                        coalesce(pw.last_reason_code, mj.last_error_code) as reason_code,
                        mj.status as mediascribe_status,
                        mj.external_job_id is not null as has_external_job,
                        mj.request_mode
                    from media_revisions mr
                    join meetings m on m.id = mr.meeting_id
                    join workspaces w on w.id = m.workspace_id
                    left join processing_workflows pw on pw.media_revision_id = mr.id
                    left join mediascribe_jobs mj on mj.processing_workflow_id = pw.id
                    where mr.source_kind = 'manual_upload'
                      and mr.status = 'accepted'
                      and m.status = 'ingested_pending_processing'
                      and (cast(:meeting_id as uuid) is null or m.id = cast(:meeting_id as uuid))
                      and coalesce(pw.last_reason_code, mj.last_error_code) = :reason_code
                      and coalesce(mj.external_job_id, '') = ''
                    order by coalesce(pw.updated_at, mr.updated_at) asc
                    limit :limit
                    """
                ),
                {
                    "meeting_id": str(meeting_id) if meeting_id is not None else None,
                    "reason_code": reason_code,
                    "limit": limit,
                },
            )
        ).mappings()
        return [
            Candidate(
                meeting_id=UUID(str(row["meeting_id"])),
                media_revision_id=UUID(str(row["media_revision_id"])),
                workspace_id=UUID(str(row["workspace_id"])),
                organization_id=UUID(str(row["organization_id"])),
                user_id=UUID(str(row["user_id"])),
                device_id=UUID(str(row["device_id"])),
                workflow_status=row["workflow_status"],
                reason_code=row["reason_code"],
                mediascribe_status=row["mediascribe_status"],
                has_external_job=bool(row["has_external_job"]),
                request_mode=row["request_mode"],
            )
            for row in rows
        ]


async def _run_candidate(sessionmaker, settings: Settings, storage: object, mediascribe_client: MediaScribeClient, candidate: Candidate, *, poll_attempts: int, poll_interval_seconds: int) -> dict[str, object]:
    tenant_scope = TenantScope(
        organization_id=candidate.organization_id,
        workspace_id=candidate.workspace_id,
        user_id=candidate.user_id,
        device_id=candidate.device_id,
    )
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            TenantDatabaseContext(
                organization_id=tenant_scope.organization_id,
                workspace_id=tenant_scope.workspace_id,
                user_id=tenant_scope.user_id,
                device_id=tenant_scope.device_id,
                context_kind="worker",
            ),
        )
        workflow = await store.upsert_processing_workflow(
            db,
            workspace_id=candidate.workspace_id,
            meeting_id=candidate.meeting_id,
            media_revision_id=candidate.media_revision_id,
            workflow_id=processing_workflow_id(candidate.media_revision_id),
            workflow_run_id=f"operator-reprocess-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}",
            status=ProcessingStatus.WORKFLOW_STARTED,
        )
        await store.record_processing_audit_event(
            db,
            workspace_id=candidate.workspace_id,
            meeting_id=candidate.meeting_id,
            processing_workflow_id=workflow.id,
            event_type="operator_reprocess_started",
            metadata={"reason_code": candidate.reason_code, "request_mode": candidate.request_mode},
        )
        try:
            submit_result = await submit_to_mediascribe(
                db=db,
                settings=settings,
                storage=storage,
                mediascribe_client=mediascribe_client,
                workflow=workflow,
            )
        except MediaScribeClientError as exc:
            return {
                "meeting_id": str(candidate.meeting_id),
                "media_revision_id": str(candidate.media_revision_id),
                "status": "submit_failed",
                "reason_code": exc.reason_code,
                "retryable": exc.retryable,
            }

        for poll_attempt in range(1, poll_attempts + 1):
            result = await poll_and_import_mediascribe_result(
                db=db,
                workflow=workflow,
                job=submit_result.job,
                mediascribe_client=mediascribe_client,
                outcome_generation_enabled=settings.outcome_generation_enabled,
            )
            if result.status in {
                ProcessingStatus.PROCESSED,
                ProcessingStatus.FAILED_TERMINAL,
                ProcessingStatus.FAILED_RETRYABLE,
                ProcessingStatus.BLOCKED,
            }:
                await store.record_processing_audit_event(
                    db,
                    workspace_id=candidate.workspace_id,
                    meeting_id=candidate.meeting_id,
                    processing_workflow_id=workflow.id,
                    mediascribe_job_id=submit_result.job.id,
                    event_type="operator_reprocess_finished",
                    metadata={"status": result.status.value, "poll_attempt": poll_attempt},
                )
                return {
                    "meeting_id": str(candidate.meeting_id),
                    "media_revision_id": str(candidate.media_revision_id),
                    "status": result.status.value,
                    "poll_attempt": poll_attempt,
                }
            await asyncio.sleep(poll_interval_seconds)

        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code="mediascribe_result_not_ready",
        )
        return {
            "meeting_id": str(candidate.meeting_id),
            "media_revision_id": str(candidate.media_revision_id),
            "status": "poll_limit_reached",
        }


async def run(args: argparse.Namespace) -> int:
    settings = Settings()
    engine = create_engine(settings)
    try:
        candidates = await _find_candidates(
            engine,
            reason_code=args.reason_code,
            meeting_id=UUID(args.meeting_id) if args.meeting_id else None,
            limit=args.limit,
        )
        if not args.execute:
            print(
                json.dumps(
                    {
                        "mode": "dry_run",
                        "candidate_count": len(candidates),
                        "candidates": [
                            {
                                "meeting_id": str(candidate.meeting_id),
                                "media_revision_id": str(candidate.media_revision_id),
                                "workflow_status": candidate.workflow_status,
                                "reason_code": candidate.reason_code,
                                "mediascribe_status": candidate.mediascribe_status,
                                "has_external_job": candidate.has_external_job,
                                "request_mode": candidate.request_mode,
                            }
                            for candidate in candidates
                        ],
                    },
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        storage = get_storage(settings)
        mediascribe_client = MediaScribeClient.from_settings(settings)
        sessionmaker = create_sessionmaker(engine)
        results = []
        for candidate in candidates:
            results.append(
                await _run_candidate(
                    sessionmaker,
                    settings,
                    storage,
                    mediascribe_client,
                    candidate,
                    poll_attempts=args.poll_attempts,
                    poll_interval_seconds=args.poll_interval_seconds,
                )
            )
        print(json.dumps({"mode": "execute", "candidate_count": len(candidates), "results": results}, ensure_ascii=False, indent=2))
        return 0
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reprocess accepted manual media uploads that failed before MediaScribe job creation.")
    parser.add_argument("--execute", action="store_true", help="Actually re-submit matching uploads to MediaScribe.")
    parser.add_argument("--meeting-id", help="Limit to one meeting id.")
    parser.add_argument("--reason-code", default="mediascribe_validation_failed")
    parser.add_argument("--limit", type=int, default=25)
    parser.add_argument("--poll-attempts", type=int, default=120)
    parser.add_argument("--poll-interval-seconds", type=int, default=5)
    return parser.parse_args()


def main() -> None:
    raise SystemExit(asyncio.run(run(parse_args())))


if __name__ == "__main__":
    main()
