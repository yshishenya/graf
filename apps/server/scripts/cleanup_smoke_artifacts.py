#!/usr/bin/env python3
import argparse
import asyncio
import json
from typing import Any

from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    TenantDatabaseContext,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.deployment import SmokeCleanupRecord, build_smoke_identity_seed


async def _table_exists(conn, table_name: str) -> bool:
    result = await conn.execute(
        text("select to_regclass(:table_name) is not null"),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = await conn.execute(
        text(
            """
            select exists (
                select 1
                from information_schema.columns
                where table_schema = current_schema()
                  and table_name = :table_name
                  and column_name = :column_name
            )
            """
        ),
        {"table_name": table_name, "column_name": column_name},
    )
    return bool(result.scalar())


def _maintenance_context() -> MaintenanceTenantContext:
    return MaintenanceTenantContext(
        operation_name="production_smoke_cleanup",
        actor_id="cleanup_smoke_artifacts.py",
        reason_category="smoke_cleanup",
        feature_area="ingest",
    )


async def _discover_smoke_meetings(
    conn: Any,
    smoke_identity: dict[str, str],
) -> list[str]:
    rows = (
        await conn.execute(
            text(
                """
                select m.id as meeting_id
                from meetings m
                join workspaces w on w.id = m.workspace_id
                join organizations o on o.id = w.organization_id
                join registered_devices d on d.id = m.device_id
                where m.workspace_id=:workspace_id
                  and m.created_by_user_id=:user_id
                  and m.device_id=:device_id
                  and w.organization_id=:organization_id
                  and w.slug like 'internal-smoke-workspace-%'
                  and o.slug like 'internal-smoke-org-%'
                  and d.device_public_id like 'internal-smoke-%'
                """
            ),
            smoke_identity,
        )
    ).mappings()
    return sorted({str(row["meeting_id"]) for row in rows})


async def _discover_upload_sessions(conn: Any, meeting_ids: list[str]) -> dict[str, list[str]]:
    sessions: dict[str, list[str]] = {}
    for meeting_id in meeting_ids:
        rows = (
            await conn.execute(
                text("select id from upload_sessions where meeting_id=:meeting_id"),
                {"meeting_id": meeting_id},
            )
        ).fetchall()
        sessions[meeting_id] = [str(row[0]) for row in rows]
    return sessions


async def _available_tables(conn: Any, table_names: set[str]) -> set[str]:
    available: set[str] = set()
    for table_name in table_names:
        if await _table_exists(conn, table_name):
            available.add(table_name)
    return available


async def _delete_statement(
    conn: Any,
    available_tables: set[str],
    table_name: str,
    sql: str,
    params: dict[str, str],
) -> int:
    if table_name not in available_tables:
        return 0
    result = await conn.execute(text(sql), params)
    return result.rowcount or 0


async def _delete_smoke_meeting_rows(
    conn: Any,
    *,
    meeting_id: str,
    session_ids: list[str],
    available_tables: set[str],
    processing_dependency_has_revision: bool,
) -> int:
    removed_rows = 0
    meeting_params = {"meeting_id": meeting_id}
    processing_dependency_delete = (
        "delete from processing_dependency_states where meeting_id=:meeting_id"
    )
    if processing_dependency_has_revision:
        # Lock the parent rows before deleting children so a concurrent worker
        # cannot insert a new FK row between the dependency delete and the
        # media revision delete.
        await conn.execute(
            text(
                "select id from media_revisions "
                "where meeting_id=:meeting_id for update"
            ),
            meeting_params,
        )
        processing_dependency_delete = """
            delete from processing_dependency_states
            where meeting_id=:meeting_id
               or media_revision_id in (
                   select id from media_revisions where meeting_id=:meeting_id
               )
        """
    ordered_meeting_deletes = [
        (
            "calendar_audit_events",
            "delete from calendar_audit_events where meeting_id=:meeting_id",
        ),
        (
            "recording_calendar_context_links",
            "delete from recording_calendar_context_links where meeting_id=:meeting_id",
        ),
        (
            "recording_calendar_match_attempts",
            "delete from recording_calendar_match_attempts where consumed_by_meeting_id=:meeting_id",
        ),
        (
            "transcript_segments",
            """
            delete from transcript_segments where meeting_id=:meeting_id
               or processing_result_id in (
                   select id from processing_results where meeting_id=:meeting_id
               )
            """,
        ),
        (
            "diarization_segments",
            """
            delete from diarization_segments where meeting_id=:meeting_id
               or processing_result_id in (
                   select id from processing_results where meeting_id=:meeting_id
               )
            """,
        ),
        (
            "processing_audit_events",
            """
            delete from processing_audit_events
            where meeting_id=:meeting_id
               or mediascribe_job_id in (
                   select id from mediascribe_jobs where meeting_id=:meeting_id
               )
               or processing_workflow_id in (
                   select id from processing_workflows where meeting_id=:meeting_id
               )
            """,
        ),
        (
            "processing_dependency_states",
            processing_dependency_delete,
        ),
        (
            "dispatch_intents",
            "delete from dispatch_intents where meeting_id=:meeting_id",
        ),
        (
            "meetings",
            "update meetings set current_outcome_set_id=null where id=:meeting_id",
        ),
        (
            "meeting_summary_slots",
            """
            update meeting_summary_slots
               set current_outcome_set_id=null,
                   current_binding_class=null,
                   legacy_migration_proof_hash=null
             where meeting_id=:meeting_id
            """,
        ),
        (
            "meeting_outcome_generation_attempts",
            """
            delete from meeting_outcome_generation_attempts
            where meeting_id=:meeting_id
               or processing_result_id in (
                   select id from processing_results where meeting_id=:meeting_id
               )
               or source_result_id in (
                   select id from processing_results where meeting_id=:meeting_id
               )
               or outcome_set_id in (
                   select id from meeting_outcome_sets
                   where meeting_id=:meeting_id
                      or processing_result_id in (
                          select id from processing_results where meeting_id=:meeting_id
                      )
               )
            """,
        ),
        (
            "meeting_outcome_items",
            """
            delete from meeting_outcome_items
            where outcome_set_id in (
                select id from meeting_outcome_sets
                where meeting_id=:meeting_id
                   or processing_result_id in (
                       select id from processing_results where meeting_id=:meeting_id
                   )
            )
            """,
        ),
        (
            "meeting_outcome_sets",
            """
            delete from meeting_outcome_sets where meeting_id=:meeting_id
               or processing_result_id in (
                   select id from processing_results where meeting_id=:meeting_id
               )
            """,
        ),
        (
            "processing_results",
            "delete from processing_results where meeting_id=:meeting_id",
        ),
        (
            "mediascribe_jobs",
            "delete from mediascribe_jobs where meeting_id=:meeting_id",
        ),
        (
            "processing_workflows",
            "delete from processing_workflows where meeting_id=:meeting_id",
        ),
        (
            "playback_normalization_attempts",
            "delete from playback_normalization_attempts where meeting_id=:meeting_id",
        ),
        (
            "playback_normalization_jobs",
            "delete from playback_normalization_jobs where meeting_id=:meeting_id",
        ),
        (
            "meeting_deletion_artifact_states",
            "delete from meeting_deletion_artifact_states where meeting_id=:meeting_id",
        ),
        (
            "meeting_deletion_reports",
            "delete from meeting_deletion_reports where meeting_id=:meeting_id",
        ),
        (
            "local_purge_tasks",
            "delete from local_purge_tasks where meeting_id=:meeting_id",
        ),
        (
            "meeting_lifecycle_audit_events",
            "delete from meeting_lifecycle_audit_events where meeting_id=:meeting_id",
        ),
        (
            "meeting_deletion_requests",
            "delete from meeting_deletion_requests where meeting_id=:meeting_id",
        ),
        (
            "meeting_share_grants",
            "delete from meeting_share_grants where meeting_id=:meeting_id",
        ),
        (
            "meeting_artifact_policies",
            "delete from meeting_artifact_policies where meeting_id=:meeting_id",
        ),
        (
            "meeting_egress_audit_events",
            "delete from meeting_egress_audit_events where meeting_id=:meeting_id",
        ),
        (
            "export_packages",
            "delete from export_packages where meeting_id=:meeting_id",
        ),
        (
            "ingest_audit_events",
            "delete from ingest_audit_events where meeting_id=:meeting_id",
        ),
        (
            "manifest_snapshots",
            "delete from manifest_snapshots where meeting_id=:meeting_id",
        ),
        (
            "track_artifacts",
            "delete from track_artifacts where meeting_id=:meeting_id",
        ),
    ]
    for table_name, sql in ordered_meeting_deletes:
        removed_rows += await _delete_statement(
            conn,
            available_tables,
            table_name,
            sql,
            meeting_params,
        )

    for session_id in session_ids:
        session_params = {"session_id": session_id}
        for table_name, sql in (
            (
                "ingest_audit_events",
                "delete from ingest_audit_events where upload_session_id=:session_id",
            ),
            (
                "temporary_upload_objects",
                "delete from temporary_upload_objects where upload_session_id=:session_id",
            ),
            (
                "upload_parts",
                "delete from upload_parts where upload_session_id=:session_id",
            ),
            ("upload_sessions", "delete from upload_sessions where id=:session_id"),
        ):
            removed_rows += await _delete_statement(
                conn,
                available_tables,
                table_name,
                sql,
                session_params,
            )

    for table_name, sql in (
        (
            "processing_placeholders",
            "delete from processing_placeholders where meeting_id=:meeting_id",
        ),
        ("media_revisions", "delete from media_revisions where meeting_id=:meeting_id"),
        ("meetings", "delete from meetings where id=:meeting_id"),
    ):
        removed_rows += await _delete_statement(
            conn,
            available_tables,
            table_name,
            sql,
            meeting_params,
        )
    return removed_rows


def _smoke_storage_prefix(smoke_identity: dict[str, str]) -> str:
    return (
        f"organizations/{smoke_identity['organization_id']}/"
        f"workspaces/{smoke_identity['workspace_id']}/"
    )


def _remove_storage_prefix(settings: Settings, prefix: str) -> tuple[int, int]:
    storage = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    object_names = {
        item.object_name
        for item in storage.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
        if item.object_name
    }
    for object_name in sorted(object_names):
        storage.remove_object(settings.minio_bucket, object_name)
    residue = sum(
        1
        for _item in storage.list_objects(settings.minio_bucket, prefix=prefix, recursive=True)
    )
    return len(object_names), residue


async def _database_residue(conn: Any, smoke_identity: dict[str, str]) -> list[str]:
    checks = (
        ("organizations", "select count(*) from organizations where id=:organization_id"),
        ("workspaces", "select count(*) from workspaces where id=:workspace_id"),
        ("user_identities", "select count(*) from user_identities where id=:user_id"),
        ("registered_devices", "select count(*) from registered_devices where id=:device_id"),
        (
            "workspace_memberships",
            "select count(*) from workspace_memberships where workspace_id=:workspace_id and user_id=:user_id",
        ),
        (
            "auth_sessions",
            "select count(*) from auth_sessions where workspace_id=:workspace_id and user_id=:user_id",
        ),
        (
            "meetings",
            "select count(*) from meetings where workspace_id=:workspace_id and created_by_user_id=:user_id and device_id=:device_id",
        ),
        (
            "playback_normalization_jobs",
            "select count(*) from playback_normalization_jobs where workspace_id=:workspace_id",
        ),
        (
            "playback_normalization_attempts",
            "select count(*) from playback_normalization_attempts where workspace_id=:workspace_id",
        ),
        (
            "fair_use_reviews",
            "select count(*) from fair_use_reviews where workspace_id=:workspace_id",
        ),
        (
            "playback_backfill_runs",
            "select count(*) from playback_backfill_runs where workspace_id=:workspace_id",
        ),
    )
    residue: list[str] = []
    for table_name, sql in checks:
        if not await _table_exists(conn, table_name):
            continue
        count = int(await conn.scalar(text(sql), smoke_identity) or 0)
        if count:
            residue.append(f"{table_name}:{count}")
    return residue


async def cleanup_smoke_artifacts(
    run_id: str,
    meeting_id: str | None = None,
    session_id: str | None = None,
) -> tuple[int, int, list[str]]:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    removed_rows = 0
    seed = build_smoke_identity_seed(run_id)
    smoke_identity: dict[str, str] = {
        "workspace_id": str(seed.workspace_id),
        "user_id": str(seed.user_id),
        "device_id": str(seed.device_id),
        "organization_id": str(seed.organization_id),
    }

    meeting_ids: list[str] = []
    residue: list[str] = []
    try:
        async with engine.begin() as conn:
            await apply_tenant_context_to_connection(conn, _maintenance_context())
            # Lock the synthetic parent before discovery/deletion. PostgreSQL
            # FK inserts take a key-share lock on this row, so a concurrent
            # playback worker cannot create a new workspace child between the
            # ordered deletes and workspace removal.
            await conn.execute(
                text("select id from workspaces where id=:workspace_id for update"),
                {"workspace_id": smoke_identity["workspace_id"]},
            )
            meeting_ids = await _discover_smoke_meetings(conn, smoke_identity)
            sessions_by_meeting = await _discover_upload_sessions(conn, meeting_ids)
            if meeting_id in sessions_by_meeting and session_id:
                sessions_by_meeting[meeting_id] = sorted(
                    {*sessions_by_meeting[meeting_id], session_id}
                )
            table_names = {
                "auth_session_device_bindings",
                "auth_sessions",
                "calendar_audit_events",
                "recording_calendar_context_links",
                "recording_calendar_match_attempts",
                "transcript_segments",
                "diarization_segments",
                "processing_audit_events",
                "processing_dependency_states",
                "dispatch_intents",
                "meeting_summary_slots",
                "meeting_outcome_generation_attempts",
                "meeting_outcome_items",
                "meeting_outcome_sets",
                "processing_results",
                "generation_calls",
                "mediascribe_jobs",
                "processing_workflows",
                "playback_normalization_attempts",
                "playback_normalization_jobs",
                "playback_backfill_runs",
                "meeting_deletion_artifact_states",
                "meeting_deletion_reports",
                "local_purge_tasks",
                "meeting_lifecycle_audit_events",
                "meeting_deletion_requests",
                "meeting_share_grants",
                "meeting_artifact_policies",
                "meeting_egress_audit_events",
                "export_packages",
                "ingest_audit_events",
                "manifest_snapshots",
                "track_artifacts",
                "temporary_upload_objects",
                "upload_parts",
                "upload_sessions",
                "processing_placeholders",
                "media_revisions",
                "meetings",
            }
            available_tables = await _available_tables(conn, table_names)
            processing_dependency_has_revision = await _column_exists(
                conn, "processing_dependency_states", "media_revision_id"
            )
            await apply_tenant_context_to_connection(
                conn,
                TenantDatabaseContext(
                    organization_id=seed.organization_id,
                    workspace_id=seed.workspace_id,
                    user_id=seed.user_id,
                    device_id=seed.device_id,
                    context_kind="request",
                ),
            )
            for discovered_meeting_id in meeting_ids:
                removed_rows += await _delete_smoke_meeting_rows(
                    conn,
                    meeting_id=discovered_meeting_id,
                    session_ids=sessions_by_meeting[discovered_meeting_id],
                    available_tables=available_tables,
                    processing_dependency_has_revision=processing_dependency_has_revision,
                )
            # Playback normalization tables use a dedicated RLS policy that
            # permits tenant-scoped request/worker writes, not the generic
            # maintenance cleanup context. The meeting-scoped jobs are gone
            # above, so remove their workspace-scoped backfill parent here.
            removed_rows += await _delete_statement(
                conn,
                available_tables,
                "playback_backfill_runs",
                "delete from playback_backfill_runs where workspace_id=:workspace_id",
                {"workspace_id": smoke_identity["workspace_id"]},
            )

            await apply_tenant_context_to_connection(conn, _maintenance_context())
            identity_deletes = (
                # Billing rows are workspace-scoped and must be removed before
                # the synthetic workspace. Keep child rows ahead of their
                # invoice/usage parents so cleanup remains safe after a smoke
                # request exercises the billing path.
                (
                    "promotion_redemptions",
                    "delete from promotion_redemptions where workspace_id=:workspace_id",
                ),
                (
                    "observed_provider_refunds",
                    "delete from observed_provider_refunds where workspace_id=:workspace_id",
                ),
                (
                    "billing_entitlement_grants",
                    "delete from billing_entitlement_grants where workspace_id=:workspace_id",
                ),
                (
                    "usage_ledger_entries",
                    "delete from usage_ledger_entries where workspace_id=:workspace_id",
                ),
                (
                    "usage_reservations",
                    "delete from usage_reservations where workspace_id=:workspace_id",
                ),
                (
                    "free_usage_windows",
                    "delete from free_usage_windows where workspace_id=:workspace_id",
                ),
                (
                    "time_credit_ledger_reversals",
                    "delete from time_credit_ledger_entries where workspace_id=:workspace_id and reversal_of_id is not null",
                ),
                (
                    "time_credit_ledger_entries",
                    "delete from time_credit_ledger_entries where workspace_id=:workspace_id",
                ),
                (
                    "storage_reservations",
                    "delete from storage_reservations where workspace_id=:workspace_id",
                ),
                (
                    "billing_notification_deliveries",
                    "delete from billing_notification_deliveries where workspace_id=:workspace_id",
                ),
                (
                    "generation_calls",
                    "delete from generation_calls where workspace_id=:workspace_id",
                ),
                (
                    "fair_use_reviews",
                    "delete from fair_use_reviews where workspace_id=:workspace_id",
                ),
                (
                    "ingest_audit_events",
                    "delete from ingest_audit_events where workspace_id=:workspace_id",
                ),
                (
                    "billing_audit_events",
                    "delete from billing_audit_events where workspace_id=:workspace_id",
                ),
                (
                    "billing_webhook_events",
                    "delete from billing_webhook_events where workspace_id=:workspace_id",
                ),
                (
                    "referral_attributions",
                    "delete from referral_attributions where workspace_id=:workspace_id",
                ),
                (
                    "referral_links",
                    "delete from referral_links where workspace_id=:workspace_id",
                ),
                (
                    "billing_payment_methods",
                    "delete from billing_payment_methods where workspace_id=:workspace_id",
                ),
                (
                    "billing_invoices",
                    "delete from billing_invoices where workspace_id=:workspace_id",
                ),
                (
                    "billing_operations",
                    "delete from billing_operations where workspace_id=:workspace_id",
                ),
                (
                    "workspace_subscriptions",
                    "delete from workspace_subscriptions where workspace_id=:workspace_id",
                ),
                (
                    "trial_activations",
                    "delete from trial_activations where workspace_id=:workspace_id",
                ),
                (
                    "account_closure_requests",
                    "delete from account_closure_requests where workspace_id=:workspace_id",
                ),
                (
                    "auth_session_device_bindings",
                    "delete from auth_session_device_bindings where registered_device_id=:device_id",
                ),
                (
                    "auth_sessions",
                    "delete from auth_sessions where user_id=:user_id and workspace_id=:workspace_id",
                ),
                (
                    "workspace_memberships",
                    "delete from workspace_memberships where workspace_id=:workspace_id and user_id=:user_id",
                ),
                (
                    "registered_devices",
                    "delete from registered_devices where id=:device_id and device_public_id like 'internal-smoke-%'",
                ),
                (
                    "user_identities",
                    "delete from user_identities where id=:user_id and organization_id=:organization_id",
                ),
                (
                    "workspaces",
                    "delete from workspaces where id=:workspace_id and organization_id=:organization_id and slug like 'internal-smoke-workspace-%'",
                ),
                (
                    "organizations",
                    "delete from organizations where id=:organization_id and slug like 'internal-smoke-org-%'",
                ),
            )
            identity_tables = await _available_tables(
                conn,
                {table_name for table_name, _sql in identity_deletes},
            )
            for table_name, sql in identity_deletes:
                removed_rows += await _delete_statement(
                    conn,
                    identity_tables,
                    table_name,
                    sql,
                    smoke_identity,
                )

        removed_objects, storage_residue = _remove_storage_prefix(
            settings,
            _smoke_storage_prefix(smoke_identity),
        )
        if storage_residue:
            residue.append(f"storage_residue:{storage_residue}")

        async with engine.begin() as conn:
            await apply_tenant_context_to_connection(conn, _maintenance_context())
            residue.extend(await _database_residue(conn, smoke_identity))
    finally:
        await engine.dispose()
    return removed_rows, removed_objects, residue


def main() -> None:
    parser = argparse.ArgumentParser(description="Record or execute cleanup for internal smoke artifacts.")
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--meeting-id")
    parser.add_argument("--session-id")
    parser.add_argument("--residue-owner")
    parser.add_argument("--residue-follow-up-reason")
    args = parser.parse_args()

    database_records_removed = 0
    object_keys_removed = 0
    residue_records: list[str] = []
    if args.execute:
        database_records_removed, object_keys_removed, residue_records = asyncio.run(
            cleanup_smoke_artifacts(
                args.run_id,
                meeting_id=args.meeting_id,
                session_id=args.session_id,
            )
        )

    cleanup = SmokeCleanupRecord(
        run_id=args.run_id,
        cleanup_result=(
            "pass" if args.execute and not residue_records else
            "residue_recorded" if args.execute else
            "blocked"
        ),
        database_records_removed=database_records_removed,
        object_keys_removed=object_keys_removed,
        residue_records=residue_records,
        residue_owner=(
            args.residue_owner or "deployment-operator"
            if not args.execute or residue_records
            else None
        ),
        residue_follow_up_reason=(
            args.residue_follow_up_reason or "automatic-smoke-cleanup-incomplete"
            if not args.execute or residue_records
            else None
        ),
    )
    print(json.dumps(cleanup.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
