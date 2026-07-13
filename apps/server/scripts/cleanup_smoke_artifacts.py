#!/usr/bin/env python3
import argparse
import asyncio
import json

from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.deployment import SmokeCleanupRecord, build_smoke_identity_seed


async def _table_exists(conn, table_name: str) -> bool:
    result = await conn.execute(
        text("select to_regclass(:table_name) is not null"),
        {"table_name": table_name},
    )
    return bool(result.scalar())


async def cleanup_smoke_artifacts(
    run_id: str,
    meeting_id: str | None = None,
    session_id: str | None = None,
) -> tuple[int, int]:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    object_keys: list[str] = []
    removed_rows = 0
    seed = build_smoke_identity_seed(run_id)
    smoke_identity: dict[str, str] = {
        "workspace_id": str(seed.workspace_id),
        "user_id": str(seed.user_id),
        "device_id": str(seed.device_id),
        "organization_id": str(seed.organization_id),
    }

    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="production_smoke_cleanup",
                actor_id="cleanup_smoke_artifacts.py",
                reason_category="smoke_cleanup",
                feature_area="ingest",
            ),
        )
        if meeting_id:
            row = (
                await conn.execute(
                    text(
                        """
                        select
                            m.workspace_id,
                            m.created_by_user_id,
                            m.device_id,
                            w.organization_id,
                            w.slug as workspace_slug,
                            o.slug as organization_slug,
                            d.device_public_id
                        from meetings m
                        join workspaces w on w.id = m.workspace_id
                        join organizations o on o.id = w.organization_id
                        join registered_devices d on d.id = m.device_id
                        where m.id=:meeting_id
                        """
                    ),
                    {"meeting_id": meeting_id},
                )
            ).mappings().first()
            if row and (
                str(row["workspace_slug"]).startswith("internal-smoke-workspace-")
                and str(row["organization_slug"]).startswith("internal-smoke-org-")
                and str(row["device_public_id"]).startswith("internal-smoke-")
            ):
                smoke_identity = {
                    "workspace_id": str(row["workspace_id"]),
                    "user_id": str(row["created_by_user_id"]),
                    "device_id": str(row["device_id"]),
                    "organization_id": str(row["organization_id"]),
                }

        if session_id:
            for table, column in (("upload_parts", "upload_session_id"), ("temporary_upload_objects", "upload_session_id")):
                rows = (
                    await conn.execute(
                        text(f"select storage_object_key from {table} where {column}=:session_id"),
                        {"session_id": session_id},
                    )
                ).fetchall()
                object_keys.extend(row[0] for row in rows)
        if meeting_id:
            rows = (
                await conn.execute(
                    text("select storage_object_key from track_artifacts where meeting_id=:meeting_id"),
                    {"meeting_id": meeting_id},
                )
            ).fetchall()
            object_keys.extend(row[0] for row in rows)

        has_auth_bindings = await _table_exists(conn, "auth_session_device_bindings")
        has_auth_sessions = await _table_exists(conn, "auth_sessions")

    storage = Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=settings.minio_secure,
    )
    removed_objects = 0
    for object_key in sorted(set(object_keys)):
        storage.remove_object(settings.minio_bucket, object_key)
        removed_objects += 1

    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="production_smoke_cleanup",
                actor_id="cleanup_smoke_artifacts.py",
                reason_category="smoke_cleanup",
                feature_area="ingest",
            ),
        )
        statements = []
        if meeting_id and session_id:
            processing_tables = {
                table_name: await _table_exists(conn, table_name)
                for table_name in (
                    "calendar_audit_events",
                    "recording_calendar_context_links",
                    "recording_calendar_match_attempts",
                    "transcript_segments",
                    "diarization_segments",
                    "processing_audit_events",
                    "processing_dependency_states",
                    "meeting_outcome_generation_attempts",
                    "meeting_outcome_items",
                    "meeting_outcome_sets",
                    "processing_results",
                    "mediascribe_jobs",
                    "processing_workflows",
                )
            }
            processing_statements = [
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
                ("transcript_segments", "delete from transcript_segments where meeting_id=:meeting_id"),
                ("diarization_segments", "delete from diarization_segments where meeting_id=:meeting_id"),
                ("processing_audit_events", "delete from processing_audit_events where meeting_id=:meeting_id"),
                ("processing_dependency_states", "delete from processing_dependency_states where meeting_id=:meeting_id"),
                (
                    "meeting_outcome_generation_attempts",
                    """
                    delete from meeting_outcome_generation_attempts
                    where meeting_id=:meeting_id
                       or outcome_set_id in (
                           select id from meeting_outcome_sets where meeting_id=:meeting_id
                       )
                    """,
                ),
                (
                    "meeting_outcome_items",
                    """
                    delete from meeting_outcome_items
                    where outcome_set_id in (
                        select id from meeting_outcome_sets where meeting_id=:meeting_id
                    )
                    """,
                ),
                ("meeting_outcome_sets", "delete from meeting_outcome_sets where meeting_id=:meeting_id"),
                ("processing_results", "delete from processing_results where meeting_id=:meeting_id"),
                ("mediascribe_jobs", "delete from mediascribe_jobs where meeting_id=:meeting_id"),
                ("processing_workflows", "delete from processing_workflows where meeting_id=:meeting_id"),
            ]
            statements.extend(
                (sql, {"meeting_id": meeting_id})
                for table_name, sql in processing_statements
                if processing_tables[table_name]
            )
            statements.extend(
                [
                    ("delete from ingest_audit_events where upload_session_id=:session_id or meeting_id=:meeting_id", {"session_id": session_id, "meeting_id": meeting_id}),
                    ("delete from manifest_snapshots where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
                    ("delete from track_artifacts where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
                    ("delete from temporary_upload_objects where upload_session_id=:session_id", {"session_id": session_id}),
                    ("delete from upload_parts where upload_session_id=:session_id", {"session_id": session_id}),
                    ("delete from upload_sessions where id=:session_id", {"session_id": session_id}),
                    ("delete from processing_placeholders where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
                    ("delete from media_revisions where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
                    ("delete from meetings where id=:meeting_id", {"meeting_id": meeting_id}),
                ]
            )
        if smoke_identity:
            if has_auth_bindings:
                statements.append(
                    (
                        "delete from auth_session_device_bindings where registered_device_id=:device_id",
                        smoke_identity,
                    )
                )
            if has_auth_sessions:
                statements.append(
                    (
                        "delete from auth_sessions where user_id=:user_id and workspace_id=:workspace_id",
                        smoke_identity,
                    )
                )
            statements.extend(
                [
                    (
                        "delete from workspace_memberships where workspace_id=:workspace_id and user_id=:user_id",
                        smoke_identity,
                    ),
                    (
                        "delete from registered_devices where id=:device_id and device_public_id like 'internal-smoke-%'",
                        smoke_identity,
                    ),
                    (
                        "delete from user_identities where id=:user_id and organization_id=:organization_id",
                        smoke_identity,
                    ),
                    (
                        "delete from workspaces where id=:workspace_id and organization_id=:organization_id and slug like 'internal-smoke-workspace-%'",
                        smoke_identity,
                    ),
                    (
                        "delete from organizations where id=:organization_id and slug like 'internal-smoke-org-%'",
                        smoke_identity,
                    ),
                ]
            )
        for sql, params in statements:
            result = await conn.execute(text(sql), params)
            removed_rows += result.rowcount or 0
    await engine.dispose()
    return removed_rows, removed_objects


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
    if args.execute:
        database_records_removed, object_keys_removed = asyncio.run(
            cleanup_smoke_artifacts(
                args.run_id,
                meeting_id=args.meeting_id,
                session_id=args.session_id,
            )
        )

    cleanup = SmokeCleanupRecord(
        run_id=args.run_id,
        cleanup_result="pass" if args.execute else "blocked",
        database_records_removed=database_records_removed,
        object_keys_removed=object_keys_removed,
        residue_owner=args.residue_owner if not args.execute else None,
        residue_follow_up_reason=args.residue_follow_up_reason if not args.execute else None,
    )
    print(json.dumps(cleanup.model_dump(mode="json"), sort_keys=True))


if __name__ == "__main__":
    main()
