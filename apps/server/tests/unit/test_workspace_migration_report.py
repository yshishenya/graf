from uuid import UUID

import pytest

from twobrain_rec_server.cli.workspace_migration_report import (
    LEGACY_BOOTSTRAP_REPORT_QUERY,
    MAINTENANCE_ROLE,
    build_workspace_migration_report,
    parse_args,
    workspace_migration_report,
)


def test_workspace_migration_report_emits_only_aggregate_read_only_metadata() -> None:
    report = build_workspace_migration_report(
        {
            "bootstrap_workspace_count": 1,
            "bootstrap_user_count": 4,
            "bootstrap_active_user_count": 4,
            "bootstrap_inactive_user_count": 0,
            "bootstrap_users_with_personal_space_count": 1,
            "bootstrap_users_without_personal_space_count": 3,
            "bootstrap_workspace_recording_count": 7,
            "bootstrap_workspace_recording_owner_count": 2,
        }
    )

    assert report == {
        "report_schema": "workspace_migration_report.v1",
        "report_result": "pass",
        "mode": "read_only_metadata_only",
        "bootstrap_user_count": 4,
        "bootstrap_active_user_count": 4,
        "bootstrap_inactive_user_count": 0,
        "bootstrap_users_with_personal_space_count": 1,
        "bootstrap_users_without_personal_space_count": 3,
        "bootstrap_workspace_recording_count": 7,
        "bootstrap_workspace_recording_owner_count": 2,
        "membership_changes": 0,
        "recording_reassignments": 0,
        "write_operations": 0,
    }


def test_workspace_migration_report_rejects_an_unknown_bootstrap_workspace() -> None:
    with pytest.raises(ValueError, match="bootstrap workspace"):
        build_workspace_migration_report(
            {
                "bootstrap_workspace_count": 0,
                "bootstrap_user_count": 0,
                "bootstrap_active_user_count": 0,
                "bootstrap_inactive_user_count": 0,
                "bootstrap_users_with_personal_space_count": 0,
                "bootstrap_users_without_personal_space_count": 0,
                "bootstrap_workspace_recording_count": 0,
                "bootstrap_workspace_recording_owner_count": 0,
            }
        )


def test_workspace_migration_report_requires_the_maintenance_role() -> None:
    with pytest.raises(ValueError, match="maintenance database URL"):
        import asyncio

        asyncio.run(
            workspace_migration_report(
                "postgresql+asyncpg://twobrain_rec_app:password@localhost/test",
                bootstrap_workspace_id=UUID("10000000-0000-0000-0000-000000000001"),
            )
        )


def test_workspace_migration_report_query_has_no_write_statement() -> None:
    query = str(LEGACY_BOOTSTRAP_REPORT_QUERY).lower()

    assert query.lstrip().startswith("with")
    assert not any(statement in query for statement in (" insert ", " update ", " delete ", " merge "))


def test_workspace_migration_report_cli_arguments_are_explicit() -> None:
    args = parse_args(
        [
            "--database-url",
            f"postgresql+asyncpg://{MAINTENANCE_ROLE}:password@localhost/test",
            "--bootstrap-workspace-id",
            "10000000-0000-0000-0000-000000000001",
        ]
    )

    assert args.bootstrap_workspace_id == UUID("10000000-0000-0000-0000-000000000001")
