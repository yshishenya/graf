"""Produce a read-only aggregate report for pre-097 bootstrap users."""

from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Mapping, Sequence
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context_to_connection,
)

MAINTENANCE_ROLE = "twobrain_rec_maintenance"
REPORT_SCHEMA_VERSION = "workspace_migration_report.v1"

# This query is deliberately aggregate-only. It never selects a user, workspace,
# recording, invitation, or authentication identifier into the report output.
LEGACY_BOOTSTRAP_REPORT_QUERY = text(
    """
    with bootstrap_workspace as (
        select id, organization_id
        from workspaces
        where id = cast(:bootstrap_workspace_id as uuid)
    ),
    bootstrap_users as (
        select distinct membership.user_id
        from workspace_memberships membership
        join bootstrap_workspace workspace on workspace.id = membership.workspace_id
    ),
    active_bootstrap_users as (
        select distinct membership.user_id
        from workspace_memberships membership
        join bootstrap_workspace workspace on workspace.id = membership.workspace_id
        where membership.status = 'active'
    ),
    personal_space_owners as (
        select personal.owner_user_id as user_id
        from workspaces personal
        join bootstrap_workspace bootstrap
          on bootstrap.organization_id = personal.organization_id
        where personal.kind = 'personal'
          and personal.owner_user_id is not null
    ),
    bootstrap_recordings as (
        select meeting.created_by_user_id as user_id, count(*)::integer as recording_count
        from meetings meeting
        join bootstrap_workspace workspace on workspace.id = meeting.workspace_id
        group by meeting.created_by_user_id
    )
    select
        (select count(*)::integer from bootstrap_workspace) as bootstrap_workspace_count,
        count(*)::integer as bootstrap_user_count,
        (select count(*)::integer from active_bootstrap_users) as bootstrap_active_user_count,
        (count(*) - (select count(*) from active_bootstrap_users))::integer
          as bootstrap_inactive_user_count,
        count(personal.user_id)::integer as bootstrap_users_with_personal_space_count,
        (count(*) - count(personal.user_id))::integer as bootstrap_users_without_personal_space_count,
        coalesce(sum(recordings.recording_count), 0)::integer as bootstrap_workspace_recording_count,
        count(recordings.user_id)::integer as bootstrap_workspace_recording_owner_count
    from bootstrap_users bootstrap_user
    left join personal_space_owners personal on personal.user_id = bootstrap_user.user_id
    left join bootstrap_recordings recordings on recordings.user_id = bootstrap_user.user_id
    """
)


def build_workspace_migration_report(row: Mapping[str, Any]) -> dict[str, int | str]:
    """Return the explicitly allowlisted, metadata-only report payload."""

    if int(row["bootstrap_workspace_count"]) != 1:
        raise ValueError("configured bootstrap workspace was not found")
    return {
        "report_schema": REPORT_SCHEMA_VERSION,
        "report_result": "pass",
        "mode": "read_only_metadata_only",
        "bootstrap_user_count": int(row["bootstrap_user_count"]),
        "bootstrap_active_user_count": int(row["bootstrap_active_user_count"]),
        "bootstrap_inactive_user_count": int(row["bootstrap_inactive_user_count"]),
        "bootstrap_users_with_personal_space_count": int(
            row["bootstrap_users_with_personal_space_count"]
        ),
        "bootstrap_users_without_personal_space_count": int(
            row["bootstrap_users_without_personal_space_count"]
        ),
        "bootstrap_workspace_recording_count": int(row["bootstrap_workspace_recording_count"]),
        "bootstrap_workspace_recording_owner_count": int(
            row["bootstrap_workspace_recording_owner_count"]
        ),
        "membership_changes": 0,
        "recording_reassignments": 0,
        "write_operations": 0,
    }


def _require_maintenance_database_url(database_url: str) -> None:
    url = make_url(database_url)
    if url.drivername != "postgresql+asyncpg" or url.username != MAINTENANCE_ROLE:
        raise ValueError("report requires a PostgreSQL maintenance database URL")


async def workspace_migration_report(
    database_url: str,
    *,
    bootstrap_workspace_id: UUID,
) -> dict[str, int | str]:
    """Classify the configured legacy workspace without changing its data."""

    _require_maintenance_database_url(database_url)
    engine = create_async_engine(database_url)
    try:
        async with engine.begin() as connection:
            await apply_tenant_context_to_connection(
                connection,
                MaintenanceTenantContext(
                    operation_name="operator_diagnostics",
                    actor_id="workspace_migration_report.py",
                    reason_category="legacy_bootstrap_classification",
                    feature_area="workspace_onboarding",
                ),
            )
            if await connection.scalar(text("select current_user")) != MAINTENANCE_ROLE:
                raise RuntimeError("report requires the maintenance database role")
            row = (await connection.execute(
                LEGACY_BOOTSTRAP_REPORT_QUERY,
                {"bootstrap_workspace_id": bootstrap_workspace_id},
            )).mappings().one()
    finally:
        await engine.dispose()
    return build_workspace_migration_report(row)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Classify pre-097 bootstrap users with aggregate read-only metadata."
    )
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--bootstrap-workspace-id", required=True, type=UUID)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    report = asyncio.run(
        workspace_migration_report(
            args.database_url,
            bootstrap_workspace_id=args.bootstrap_workspace_id,
        )
    )
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
