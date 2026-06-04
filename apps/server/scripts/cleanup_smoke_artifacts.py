#!/usr/bin/env python3
import argparse
import asyncio
import json

from minio import Minio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import Settings
from twobrain_rec_server.deployment import SmokeCleanupRecord


async def cleanup_smoke_artifacts(meeting_id: str, session_id: str) -> tuple[int, int]:
    settings = Settings()
    engine = create_async_engine(settings.database_url)
    object_keys: list[str] = []
    removed_rows = 0
    smoke_identity: dict[str, str] = {}

    async with engine.begin() as conn:
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

        for table, column in (("upload_parts", "upload_session_id"), ("temporary_upload_objects", "upload_session_id")):
            rows = (
                await conn.execute(
                    text(f"select storage_object_key from {table} where {column}=:session_id"),
                    {"session_id": session_id},
                )
            ).fetchall()
            object_keys.extend(row[0] for row in rows)
        rows = (
            await conn.execute(
                text("select storage_object_key from track_artifacts where meeting_id=:meeting_id"),
                {"meeting_id": meeting_id},
            )
        ).fetchall()
        object_keys.extend(row[0] for row in rows)

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
        statements = [
            ("delete from ingest_audit_events where upload_session_id=:session_id or meeting_id=:meeting_id", {"session_id": session_id, "meeting_id": meeting_id}),
            ("delete from manifest_snapshots where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
            ("delete from track_artifacts where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
            ("delete from temporary_upload_objects where upload_session_id=:session_id", {"session_id": session_id}),
            ("delete from upload_parts where upload_session_id=:session_id", {"session_id": session_id}),
            ("delete from upload_sessions where id=:session_id", {"session_id": session_id}),
            ("delete from processing_placeholders where meeting_id=:meeting_id", {"meeting_id": meeting_id}),
            ("delete from meetings where id=:meeting_id", {"meeting_id": meeting_id}),
        ]
        if smoke_identity:
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
    if args.execute and args.meeting_id and args.session_id:
        database_records_removed, object_keys_removed = asyncio.run(
            cleanup_smoke_artifacts(args.meeting_id, args.session_id)
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
