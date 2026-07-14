from __future__ import annotations

import asyncio
import os

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from twobrain_rec_server.config import get_settings

APP_ROLE = "twobrain_rec_app"
MAINTENANCE_ROLE = "twobrain_rec_maintenance"
MEDIA_ROLE = "twobrain_rec_media"
ALLOWED_ROLES = frozenset({APP_ROLE, MAINTENANCE_ROLE, MEDIA_ROLE})


async def _verify() -> tuple[str, bool, bool]:
    expected_role = os.environ.get("TWOBRAIN_EXPECTED_DATABASE_ROLE", "").strip()
    if expected_role not in ALLOWED_ROLES:
        raise RuntimeError("expected runtime database role is invalid")

    settings = get_settings()
    engine = create_async_engine(settings.database_url, pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            role = await connection.scalar(text("select current_user"))
            attributes = (
                await connection.execute(
                    text(
                        "select rolcanlogin, rolsuper, rolcreatedb, rolcreaterole, "
                        "rolinherit, rolreplication, rolbypassrls "
                        "from pg_roles where rolname = current_user"
                    )
                )
            ).one()
            row_security = await connection.scalar(text("show row_security"))
            workspace_execute = bool(
                await connection.scalar(
                    text(
                        "select has_function_privilege(current_user, "
                        "'rec_playback_normalization_workspace_page(uuid, integer)', "
                        "'execute')"
                    )
                )
            )
            cleanup_execute = bool(
                await connection.scalar(
                    text(
                        "select has_function_privilege(current_user, "
                        "'rec_playback_normalization_cleanup_page(integer)', 'execute')"
                    )
                )
            )
            for name, value in (
                ("app.context_kind", "maintenance"),
                ("app.maintenance_operation", "operator_diagnostics"),
                ("app.maintenance_actor", "runtime-identity-probe"),
                ("app.maintenance_reason", "runtime_identity"),
                ("app.maintenance_feature_area", "deployment"),
            ):
                await connection.execute(
                    text("select set_config(:name, :value, true)"),
                    {"name": name, "value": value},
                )
            legacy_maintenance_access = bool(
                await connection.scalar(text("select rec_maintenance_allowed()"))
            )
    finally:
        await engine.dispose()

    if role != expected_role:
        raise RuntimeError("runtime database role mismatch")
    if (
        not attributes.rolcanlogin
        or attributes.rolsuper
        or attributes.rolcreatedb
        or attributes.rolcreaterole
        or attributes.rolinherit
        or attributes.rolreplication
        or attributes.rolbypassrls
        or row_security != "on"
    ):
        raise RuntimeError("runtime database role attributes are unsafe")
    scheduler_access = workspace_execute and cleanup_execute
    if workspace_execute != cleanup_execute:
        raise RuntimeError("runtime database scheduler privileges are inconsistent")
    if scheduler_access != (expected_role == MEDIA_ROLE):
        raise RuntimeError("runtime database scheduler privileges are unsafe")
    if legacy_maintenance_access != (expected_role == MAINTENANCE_ROLE):
        raise RuntimeError("runtime database maintenance privileges are unsafe")
    return expected_role, scheduler_access, legacy_maintenance_access


def main() -> None:
    try:
        role, scheduler_access, maintenance_access = asyncio.run(_verify())
    except Exception:
        print("runtime_database_identity_result=fail")
        raise SystemExit(1) from None
    print("runtime_database_identity_result=pass")
    print(f"runtime_database_role={role}")
    print("scheduler_function_access=" + ("allowed" if scheduler_access else "denied"))
    print("legacy_maintenance_access=" + ("allowed" if maintenance_access else "denied"))


if __name__ == "__main__":
    main()
