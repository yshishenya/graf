#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import importlib.util
import os
import sys
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

SERVER_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVER_ROOT / "src"))

RLS_VALIDATION_PATH = SERVER_ROOT / "src/twobrain_rec_server/db/rls_validation.py"
spec = importlib.util.spec_from_file_location("rls_validation", RLS_VALIDATION_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError("unable to load rls validation module")
rls_validation = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = rls_validation
spec.loader.exec_module(rls_validation)
REQUIRED_RLS_PROBES = rls_validation.REQUIRED_RLS_PROBES
RLSProbeEvidence = rls_validation.RLSProbeEvidence
RLSValidationReport = rls_validation.RLSValidationReport

command = None
Config = None
text = None
make_url = None
create_async_engine = None
get_settings = None
MaintenanceTenantContext = None
TenantDatabaseContext = None
apply_tenant_context_to_connection = None


def _load_probe_dependencies() -> None:
    global command
    global Config
    global text
    global make_url
    global create_async_engine
    global get_settings
    global MaintenanceTenantContext
    global TenantDatabaseContext
    global apply_tenant_context_to_connection

    if create_async_engine is not None:
        return

    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig
    from sqlalchemy import text as sqlalchemy_text
    from sqlalchemy.engine import make_url as sqlalchemy_make_url
    from sqlalchemy.ext.asyncio import create_async_engine as sqlalchemy_create_async_engine

    from twobrain_rec_server.config import get_settings as app_get_settings
    from twobrain_rec_server.db.tenant_context import (
        MaintenanceTenantContext as AppMaintenanceTenantContext,
    )
    from twobrain_rec_server.db.tenant_context import (
        TenantDatabaseContext as AppTenantDatabaseContext,
    )
    from twobrain_rec_server.db.tenant_context import (
        apply_tenant_context_to_connection as app_apply_tenant_context_to_connection,
    )

    command = alembic_command
    Config = AlembicConfig
    text = sqlalchemy_text
    make_url = sqlalchemy_make_url
    create_async_engine = sqlalchemy_create_async_engine
    get_settings = app_get_settings
    MaintenanceTenantContext = AppMaintenanceTenantContext
    TenantDatabaseContext = AppTenantDatabaseContext
    apply_tenant_context_to_connection = app_apply_tenant_context_to_connection


@dataclass(frozen=True, slots=True)
class MigratedPostgresUrls:
    migration_url: str
    probe_url: str
    probe_role: str | None = None


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _quote_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _print_report(report: RLSValidationReport) -> None:
    for line in report.evidence_lines():
        print(line)


async def _create_probe_role(migration_url: str) -> tuple[str, str]:
    role_name = f"twobrain_rls_probe_{uuid4().hex[:16]}"
    password = uuid4().hex
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier(role_name)
            await conn.execute(text(f"create role {quoted_role} login password {_quote_literal(password)}"))
            await conn.execute(text(f"grant usage on schema public to {quoted_role}"))
            await conn.execute(
                text(f"grant select, insert, update, delete on all tables in schema public to {quoted_role}")
            )
            await conn.execute(text(f"grant usage, select on all sequences in schema public to {quoted_role}"))
    finally:
        await engine.dispose()
    return role_name, password


async def _drop_probe_role(migration_url: str, role_name: str) -> None:
    engine = create_async_engine(migration_url, isolation_level="AUTOCOMMIT")
    try:
        async with engine.begin() as conn:
            quoted_role = _quote_identifier(role_name)
            await conn.execute(text(f"drop owned by {quoted_role}"))
            await conn.execute(text(f"drop role if exists {quoted_role}"))
    finally:
        await engine.dispose()


def _run_migrations(database_url: str) -> None:
    previous_url = os.environ.get("TWOBRAIN_DATABASE_URL")
    os.environ["TWOBRAIN_DATABASE_URL"] = database_url
    get_settings.cache_clear()
    try:
        alembic_config = Config(str(SERVER_ROOT / "alembic.ini"))
        alembic_config.set_main_option(
            "script_location",
            str(SERVER_ROOT / "src/twobrain_rec_server/db/migrations"),
        )
        command.upgrade(alembic_config, "head")
    finally:
        if previous_url is None:
            os.environ.pop("TWOBRAIN_DATABASE_URL", None)
        else:
            os.environ["TWOBRAIN_DATABASE_URL"] = previous_url
        get_settings.cache_clear()


async def _prepare_urls(database_url: str) -> MigratedPostgresUrls:
    probe_url = os.getenv("RLS_TEST_PROBE_DATABASE_URL")
    if probe_url:
        return MigratedPostgresUrls(migration_url=database_url, probe_url=probe_url)
    probe_role, password = await _create_probe_role(database_url)
    return MigratedPostgresUrls(
        migration_url=database_url,
        probe_url=make_url(database_url)
        .set(username=probe_role, password=password)
        .render_as_string(hide_password=False),
        probe_role=probe_role,
    )


async def _seed_probe_rows(engine: Any) -> dict[str, UUID | str]:
    suffix = uuid4().hex[:12]
    ids: dict[str, UUID | str] = {
        "org_a": uuid4(),
        "org_b": uuid4(),
        "workspace_a": uuid4(),
        "workspace_b": uuid4(),
        "user_a": uuid4(),
        "user_b": uuid4(),
        "device_a": uuid4(),
        "device_b": uuid4(),
        "meeting_a": uuid4(),
        "meeting_b": uuid4(),
        "session_a": uuid4(),
        "session_hash_a": f"rls-session-{suffix}",
        "slug": suffix,
    }
    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="verify_rls_hardening",
                reason_category="rls_probe_seed",
                feature_area="security",
            ),
        )
        for label in ("a", "b"):
            await conn.execute(
                text(
                    """
                    insert into organizations (id, slug, name)
                    values (:org_id, :org_slug, :org_name)
                    """
                ),
                {
                    "org_id": ids[f"org_{label}"],
                    "org_slug": f"rls-org-{label}-{suffix}",
                    "org_name": f"RLS Org {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into workspaces (id, organization_id, slug, name)
                    values (:workspace_id, :org_id, :workspace_slug, :workspace_name)
                    """
                ),
                {
                    "workspace_id": ids[f"workspace_{label}"],
                    "org_id": ids[f"org_{label}"],
                    "workspace_slug": f"rls-workspace-{label}-{suffix}",
                    "workspace_name": f"RLS Workspace {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into user_identities (id, organization_id, external_subject, display_name)
                    values (:user_id, :org_id, :external_subject, :display_name)
                    """
                ),
                {
                    "user_id": ids[f"user_{label}"],
                    "org_id": ids[f"org_{label}"],
                    "external_subject": f"rls-user-{label}-{suffix}",
                    "display_name": f"RLS User {label.upper()}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into workspace_memberships (workspace_id, user_id, role, status)
                    values (:workspace_id, :user_id, 'owner', 'active')
                    """
                ),
                {"workspace_id": ids[f"workspace_{label}"], "user_id": ids[f"user_{label}"]},
            )
            await conn.execute(
                text(
                    """
                    insert into registered_devices
                        (id, workspace_id, user_id, device_public_id, status, registration_state)
                    values
                        (:device_id, :workspace_id, :user_id, :device_public_id, 'active', 'approved')
                    """
                ),
                {
                    "device_id": ids[f"device_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "user_id": ids[f"user_{label}"],
                    "device_public_id": f"rls-device-{label}-{suffix}",
                },
            )
            await conn.execute(
                text(
                    """
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         duration_seconds, status)
                    values
                        (:meeting_id, :workspace_id, :user_id, :device_id, :local_recording_id,
                         60, 'ingested_pending_processing')
                    """
                ),
                {
                    "meeting_id": ids[f"meeting_{label}"],
                    "workspace_id": ids[f"workspace_{label}"],
                    "user_id": ids[f"user_{label}"],
                    "device_id": ids[f"device_{label}"],
                    "local_recording_id": f"rls-meeting-{label}-{suffix}",
                },
            )
        await conn.execute(
            text(
                """
                insert into auth_sessions
                    (id, user_id, workspace_id, device_id, provider, session_token_hash, expires_at)
                values
                    (:session_id, :user_id, :workspace_id, :device_id, 'yandex',
                     :session_token_hash, :expires_at)
                """
            ),
            {
                "session_id": ids["session_a"],
                "user_id": ids["user_a"],
                "workspace_id": ids["workspace_a"],
                "device_id": ids["device_a"],
                "session_token_hash": ids["session_hash_a"],
                "expires_at": datetime.now(UTC) + timedelta(hours=1),
            },
        )
    return ids


def _request_context(ids: dict[str, UUID | str], label: str, *, context_kind: str = "request") -> TenantDatabaseContext:
    return TenantDatabaseContext(
        organization_id=ids[f"org_{label}"],
        workspace_id=ids[f"workspace_{label}"],
        user_id=ids[f"user_{label}"],
        device_id=ids[f"device_{label}"],
        context_kind=context_kind,  # type: ignore[arg-type]
    )


async def _probe_same_and_cross_tenant_reads(engine: Any) -> dict[str, bool]:
    ids = await _seed_probe_rows(engine)
    async with engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        visible_count = await conn.scalar(text("select count(*) from meetings"))
        foreign_count = await conn.scalar(
            text("select count(*) from meetings where id=:meeting_id"),
            {"meeting_id": ids["meeting_b"]},
        )
    return {
        "same_tenant_read": visible_count == 1,
        "cross_tenant_read_not_found_or_empty": foreign_count == 0,
    }


async def _probe_cross_tenant_mutation_and_missing_context(engine: Any) -> dict[str, bool]:
    ids = await _seed_probe_rows(engine)
    async with engine.begin() as conn:
        missing_count = await conn.scalar(text("select count(*) from meetings"))

    mutation_forbidden = False
    async with engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        try:
            await conn.execute(
                text(
                    """
                    insert into meetings
                        (id, workspace_id, created_by_user_id, device_id, local_recording_id,
                         duration_seconds, status)
                    values
                        (:meeting_id, :workspace_id, :user_id, :device_id, :local_recording_id,
                         60, 'draft')
                    """
                ),
                {
                    "meeting_id": uuid4(),
                    "workspace_id": ids["workspace_b"],
                    "user_id": ids["user_b"],
                    "device_id": ids["device_b"],
                    "local_recording_id": f"cross-insert-{ids['slug']}",
                },
            )
        except Exception:
            mutation_forbidden = True
    return {
        "cross_tenant_mutation_forbidden": mutation_forbidden,
        "missing_context_auth_or_context_error": missing_count == 0,
    }


async def _probe_worker_and_maintenance_context(engine: Any) -> dict[str, bool]:
    ids = await _seed_probe_rows(engine)

    async with engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a", context_kind="worker"))
        worker_count = await conn.scalar(text("select count(*) from meetings"))

    async with engine.connect() as conn:
        await conn.execute(text("select set_config('app.context_kind', 'maintenance', true)"))
        await conn.execute(text("select set_config('app.maintenance_operation', 'migration_verification', true)"))
        incomplete_maintenance_count = await conn.scalar(text("select count(*) from meetings"))

    async with engine.connect() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="verify_rls_hardening",
                reason_category="rls_probe",
                feature_area="security",
            ),
        )
        maintenance_count = await conn.scalar(text("select count(*) from meetings"))

    return {
        "worker_context": worker_count == 1,
        "maintenance_context": incomplete_maintenance_count == 0 and (maintenance_count or 0) >= 2,
    }


async def _run_probe(
    engine: Any,
    probe: Callable[[Any], Awaitable[dict[str, bool]]],
) -> dict[str, bool]:
    try:
        return await probe(engine)
    except Exception:
        return {}


async def _run_probes(database_url: str) -> list[RLSProbeEvidence]:
    urls = await _prepare_urls(database_url)
    engine = create_async_engine(urls.probe_url, pool_pre_ping=True)
    try:
        results: dict[str, bool] = {}
        for probe in (
            _probe_same_and_cross_tenant_reads,
            _probe_cross_tenant_mutation_and_missing_context,
            _probe_worker_and_maintenance_context,
        ):
            results.update(await _run_probe(engine, probe))
        return [
            RLSProbeEvidence(
                name=probe_name,
                result="pass" if results.get(probe_name) is True else "failed",
                environment="postgres_test",
            )
            for probe_name in REQUIRED_RLS_PROBES
        ]
    finally:
        await engine.dispose()
        if urls.probe_role is not None:
            await _drop_probe_role(urls.migration_url, urls.probe_role)


def main() -> int:
    database_url = os.getenv("RLS_TEST_DATABASE_URL")
    if not database_url:
        _print_report(RLSValidationReport(environment="postgres_test"))
        print("reason=postgres_test_database_required")
        return 0

    try:
        _load_probe_dependencies()
        _run_migrations(database_url)
        probes = asyncio.run(_run_probes(database_url))
    except Exception as exc:
        _print_report(RLSValidationReport(environment="postgres_test"))
        print("reason=rls_probe_command_failed")
        print(f"error_type={type(exc).__name__}")
        return 1

    report = RLSValidationReport(environment="postgres_test", probes=probes)
    _print_report(report)
    if report.validation_result != "pass":
        print("reason=rls_probe_failed")
        print(f"failed_probe_names={','.join(report.blocking_reasons)}")
        return 1
    print("probe_suite=direct_sql_rls_probes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
