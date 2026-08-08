from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.fixtures.postgres_test_database import prepare_schema
from twobrain_rec_server.config import get_settings

REPO_ROOT = Path(__file__).resolve().parents[4]

TENANT_TABLES = (
    "summary_templates",
    "meeting_share_invitations",
)
WORKER_ONLY_TABLES = ("generation_calls",)
OPERATOR_ONLY_TABLES = (
    "prompt_optimization_runs",
    "prompt_optimization_call_ledger",
)
EXISTING_TENANT_TABLES = ("meeting_share_grants",)

pytestmark = pytest.mark.strict_rls


def _alembic_config(database_url: str, monkeypatch: pytest.MonkeyPatch) -> Config:
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", database_url)
    get_settings.cache_clear()
    config = Config(str(REPO_ROOT / "apps/server/alembic.ini"))
    config.set_main_option(
        "script_location",
        str(REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations"),
    )
    return config


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


@pytest.fixture(scope="module")
def recording_workflow_rls_urls(
    postgres_advisory_lock: None,
    postgres_worker_database_url: str,
) -> Iterator[tuple[str, str, dict[str, object]]]:
    prepare_schema(postgres_worker_database_url)
    role = f"twobrain_rec_feature121_{uuid4().hex[:12]}"
    password = uuid4().hex

    async def provision() -> tuple[str, dict[str, object]]:
        owner = create_async_engine(postgres_worker_database_url, isolation_level="AUTOCOMMIT")
        try:
            async with owner.begin() as conn:
                quoted = _quote_identifier(role)
                quoted_password = await conn.scalar(
                    text("select quote_literal(:password)"), {"password": password}
                )
                await conn.execute(
                    text(
                        f"create role {quoted} login password {quoted_password} "
                        "nosuperuser nocreatedb nocreaterole noinherit noreplication nobypassrls"
                    )
                )
                await conn.execute(text(f"alter role {quoted} set row_security = on"))
                await conn.execute(text(f"grant usage on schema public to {quoted}"))
                await conn.execute(
                    text(
                        "grant select, insert, update, delete on "
                        + ", ".join(
                            f"public.{name}"
                            for name in (
                                TENANT_TABLES
                                + WORKER_ONLY_TABLES
                                + OPERATOR_ONLY_TABLES
                                + EXISTING_TENANT_TABLES
                            )
                        )
                        + f" to {quoted}"
                    )
                )
                ids: dict[str, object] = {
                    name: uuid4()
                    for name in (
                        "organization",
                        "workspace_a",
                        "workspace_b",
                        "user_a",
                        "user_b",
                        "device_a",
                        "device_b",
                        "meeting_a",
                        "meeting_b",
                        "generation_meeting",
                        "run",
                    )
                }
                await conn.execute(
                    text(
                        "insert into organizations (id, slug, name) "
                        "values (:id, 'feature-121-rls', 'Feature 121 RLS')"
                    ),
                    {"id": ids["organization"]},
                )
                for suffix in ("a", "b"):
                    await conn.execute(
                        text(
                            "insert into workspaces (id, organization_id, slug, name) "
                            "values (:id, :organization_id, :slug, :name)"
                        ),
                        {
                            "id": ids[f"workspace_{suffix}"],
                            "organization_id": ids["organization"],
                            "slug": f"feature-121-{suffix}",
                            "name": f"Feature 121 {suffix.upper()}",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into user_identities (id, organization_id, external_subject) "
                            "values (:id, :organization_id, :subject)"
                        ),
                        {
                            "id": ids[f"user_{suffix}"],
                            "organization_id": ids["organization"],
                            "subject": f"feature-121-{suffix}@example.test",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into registered_devices "
                            "(id, workspace_id, user_id, device_public_id, status, registration_state) "
                            "values (:id, :workspace_id, :user_id, :device, 'active', 'approved')"
                        ),
                        {
                            "id": ids[f"device_{suffix}"],
                            "workspace_id": ids[f"workspace_{suffix}"],
                            "user_id": ids[f"user_{suffix}"],
                            "device": f"feature-121-device-{suffix}",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into meetings "
                            "(id, workspace_id, created_by_user_id, device_id, local_recording_id, "
                            "duration_seconds, status) values "
                            "(:id, :workspace_id, :user_id, :device_id, :recording_id, 60, 'ready')"
                        ),
                        {
                            "id": ids[f"meeting_{suffix}"],
                            "workspace_id": ids[f"workspace_{suffix}"],
                            "user_id": ids[f"user_{suffix}"],
                            "device_id": ids[f"device_{suffix}"],
                            "recording_id": f"feature-121-meeting-{suffix}",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into summary_templates "
                            "(id, workspace_id, template_key, kind, name, purpose, sections_json, "
                            "output_language, detail_level, version, status) values "
                            "(:id, :workspace_id, :template_key, 'builtin', 'Synthetic', "
                            "'Synthetic', '[\"summary\"]', 'ru', 'standard', 1, 'active')"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": ids[f"workspace_{suffix}"],
                            "template_key": f"synthetic-{suffix}",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into meeting_share_grants "
                            "(id, workspace_id, meeting_id, grant_type, grantee_user_id, "
                            "created_by_user_id, status, audience_type, audience_id, content_scope, "
                            "can_download, can_export, share_token_hash) values "
                            "(:id, :workspace_id, :meeting_id, 'user', :user_id, :user_id, "
                            "'active', 'user', :user_id, 'summary_only', false, false, :token)"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": ids[f"workspace_{suffix}"],
                            "meeting_id": ids[f"meeting_{suffix}"],
                            "user_id": ids[f"user_{suffix}"],
                            "token": f"share-token-{suffix}",
                        },
                    )
                    await conn.execute(
                        text(
                            "insert into meeting_share_invitations "
                            "(id, workspace_id, meeting_id, invited_by_user_id, "
                            "normalized_address_hash, encrypted_delivery_address, token_hash, "
                            "status, expires_at) values "
                            "(:id, :workspace_id, :meeting_id, :user_id, :address_hash, "
                            ":address, :token, 'pending', now() + interval '1 day')"
                        ),
                        {
                            "id": uuid4(),
                            "workspace_id": ids[f"workspace_{suffix}"],
                            "meeting_id": ids[f"meeting_{suffix}"],
                            "user_id": ids[f"user_{suffix}"],
                            "address_hash": f"address-hash-{suffix}",
                            "address": f"encrypted-{suffix}",
                            "token": f"invitation-token-{suffix}",
                        },
                    )
                await conn.execute(
                    text(
                        "insert into meetings "
                        "(id, workspace_id, created_by_user_id, device_id, local_recording_id, "
                        "duration_seconds, status) values "
                        "(:id, :workspace_id, :user_id, :device_id, 'feature-121-generation', "
                        "60, 'ready')"
                    ),
                    {
                        "id": ids["generation_meeting"],
                        "workspace_id": ids["workspace_a"],
                        "user_id": ids["user_a"],
                        "device_id": ids["device_a"],
                    },
                )
                candidate_id = uuid4()
                await conn.execute(
                    text(
                        "insert into generation_calls "
                        "(id, workspace_id, meeting_id, candidate_id, provider_attempt, "
                        "call_sequence, trace_id, observation_id, call_state, started_at) values "
                        "(:id, :workspace_id, :meeting_id, :candidate_id, 1, 1, 'trace-a', "
                        "'observation-a', 'reserved', now())"
                    ),
                    {
                        "id": uuid4(),
                        "workspace_id": ids["workspace_a"],
                        "meeting_id": ids["generation_meeting"],
                        "candidate_id": candidate_id,
                    },
                )
                await conn.execute(
                    text("delete from meetings where id = :meeting_id"),
                    {"meeting_id": ids["generation_meeting"]},
                )
                await conn.execute(
                    text(
                        "insert into prompt_optimization_runs "
                        "(id, initiated_by_actor_id, prompt_name, source_prompt_version, "
                        "source_config_hash, train_dataset_ref, development_dataset_ref, "
                        "heldout_dataset_ref, optimizer_version, adapter_version, "
                        "reflection_prompt_name, reflection_prompt_version, reflection_config_hash, "
                        "deadline_at, workflow_id, rollback_prompt_version) values "
                        "(:id, 'operator', 'graf/synthetic', 1, :hash, 'train', 'dev', 'heldout', "
                        "'0.1.4', 'v1', 'graf/reflection', 1, :hash, now() + interval '1 day', "
                        "'prompt-optimization/synthetic', 1)"
                    ),
                    {"id": ids["run"], "hash": "a" * 64},
                )
                await conn.execute(
                    text(
                        "insert into prompt_optimization_call_ledger "
                        "(run_id, call_key, phase, prompt_version, config_hash, model_route, "
                        "reserved_token_ceiling, reserved_cost_ceiling, activity_attempt, "
                        "activity_fence, lease_expires_at) values "
                        "(:run_id, 'call', 'task', 1, :hash, 'synthetic', 10, '1.00', 1, "
                        ":fence, now() + interval '1 minute')"
                    ),
                    {"run_id": ids["run"], "hash": "a" * 64, "fence": uuid4()},
                )
            return (
                make_url(postgres_worker_database_url)
                .set(username=role, password=password)
                .render_as_string(hide_password=False)
            ), ids
        finally:
            await owner.dispose()

    probe_url, ids = asyncio.run(provision())
    try:
        yield postgres_worker_database_url, probe_url, ids
    finally:
        async def cleanup() -> None:
            owner = create_async_engine(postgres_worker_database_url, isolation_level="AUTOCOMMIT")
            try:
                async with owner.begin() as conn:
                    quoted = _quote_identifier(role)
                    await conn.execute(text(f"drop owned by {quoted}"))
                    await conn.execute(text(f"drop role if exists {quoted}"))
            finally:
                await owner.dispose()

        asyncio.run(cleanup())


async def test_recording_workflow_tables_have_forced_rls_and_expected_policy_shape(
    recording_workflow_rls_urls: tuple[str, str, dict[str, object]],
) -> None:
    owner_url, _, _ = recording_workflow_rls_urls
    engine = create_async_engine(owner_url)
    try:
        async with engine.connect() as conn:
            states = {
                row.table_name: (row.rls_enabled, row.rls_forced)
                for row in (
                    await conn.execute(
                        text(
                            "select c.relname as table_name, c.relrowsecurity as rls_enabled, "
                            "c.relforcerowsecurity as rls_forced "
                            "from pg_class c join pg_namespace n on n.oid = c.relnamespace "
                            "where n.nspname = 'public' and c.relname = any(:tables)"
                        ),
                        {
                            "tables": list(
                                TENANT_TABLES + WORKER_ONLY_TABLES + OPERATOR_ONLY_TABLES
                            )
                        },
                    )
                ).all()
            }
            assert states == {
                name: (True, True)
                for name in TENANT_TABLES + WORKER_ONLY_TABLES + OPERATOR_ONLY_TABLES
            }
            policies = {
                row.tablename: row.qual
                for row in (
                    await conn.execute(
                        text(
                            "select tablename, qual from pg_policies "
                            "where schemaname = 'public' and tablename = any(:tables)"
                        ),
                        {
                            "tables": list(
                                TENANT_TABLES + WORKER_ONLY_TABLES + OPERATOR_ONLY_TABLES
                            )
                        },
                    )
                ).all()
            }
    finally:
        await engine.dispose()

    for table_name in TENANT_TABLES:
        assert "rec_current_workspace_id()" in policies[table_name]
        assert "request" in policies[table_name]
        assert "worker" in policies[table_name]
    assert "rec_current_workspace_id()" in policies["generation_calls"]
    assert "worker" in policies["generation_calls"]
    assert "request" not in policies["generation_calls"]
    for table_name in OPERATOR_ONLY_TABLES:
        assert policies[table_name] == "rec_maintenance_allowed()"


async def test_request_and_worker_contexts_cannot_read_operator_control_plane(
    recording_workflow_rls_urls: tuple[str, str, dict[str, object]],
) -> None:
    _, probe_url, _ = recording_workflow_rls_urls
    engine = create_async_engine(probe_url)
    try:
        async with engine.begin() as conn:
            for context_kind in ("request", "worker"):
                await conn.execute(
                    text("select set_config('app.context_kind', :kind, true)"),
                    {"kind": context_kind},
                )
                await conn.execute(
                    text(
                        "select set_config('app.workspace_id', "
                        "'10000000-0000-0000-0000-000000000001', true)"
                    )
                )
                for table_name in OPERATOR_ONLY_TABLES:
                    count = await conn.scalar(text(f"select count(*) from {table_name}"))
                    assert count == 0
    finally:
        await engine.dispose()


async def test_request_context_cannot_read_retained_generation_calls(
    recording_workflow_rls_urls: tuple[str, str, dict[str, object]],
) -> None:
    _, probe_url, _ = recording_workflow_rls_urls
    engine = create_async_engine(probe_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("select set_config('app.context_kind', 'request', true)"))
            await conn.execute(
                text(
                    "select set_config('app.workspace_id', "
                    "'10000000-0000-0000-0000-000000000001', true)"
                )
            )
            assert await conn.scalar(text("select count(*) from generation_calls")) == 0
    finally:
        await engine.dispose()


async def test_request_tenant_scope_hides_foreign_templates_grants_invitations_and_tokens(
    recording_workflow_rls_urls: tuple[str, str, dict[str, object]],
) -> None:
    _, probe_url, ids = recording_workflow_rls_urls
    engine = create_async_engine(probe_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("select set_config('app.context_kind', 'request', true)"))
            await conn.execute(
                text("select set_config('app.workspace_id', :workspace_id, true)"),
                {"workspace_id": str(ids["workspace_a"])},
            )
            assert await conn.scalar(text("select count(*) from summary_templates")) == 1
            assert await conn.scalar(text("select count(*) from meeting_share_grants")) == 1
            assert await conn.scalar(text("select count(*) from meeting_share_invitations")) == 1
            assert (
                await conn.scalar(
                    text(
                        "select count(*) from meeting_share_grants "
                        "where share_token_hash = 'share-token-b'"
                    )
                )
                == 0
            )
            assert (
                await conn.scalar(
                    text(
                        "select count(*) from meeting_share_invitations "
                        "where token_hash = 'invitation-token-b'"
                    )
                )
                == 0
            )
    finally:
        await engine.dispose()


async def test_worker_can_read_retained_call_after_parent_deletion_only_in_its_workspace(
    recording_workflow_rls_urls: tuple[str, str, dict[str, object]],
) -> None:
    _, probe_url, ids = recording_workflow_rls_urls
    engine = create_async_engine(probe_url)
    try:
        async with engine.begin() as conn:
            await conn.execute(text("select set_config('app.context_kind', 'worker', true)"))
            await conn.execute(
                text("select set_config('app.workspace_id', :workspace_id, true)"),
                {"workspace_id": str(ids["workspace_a"])},
            )
            retained = (
                await conn.execute(
                    text("select meeting_id, export_status from generation_calls")
                )
            ).one()
            assert retained == (ids["generation_meeting"], "pending")
            await conn.execute(
                text("select set_config('app.workspace_id', :workspace_id, true)"),
                {"workspace_id": str(ids["workspace_b"])},
            )
            assert await conn.scalar(text("select count(*) from generation_calls")) == 0
    finally:
        await engine.dispose()


def test_upgrade_preserves_legacy_grant_and_downgrade_restores_0030_schema(
    postgres_clean_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _alembic_config(postgres_clean_database_url, monkeypatch)
    command.upgrade(config, "0030_expand_meeting_registry")
    ids = {
        name: uuid4()
        for name in (
            "organization",
            "workspace",
            "user",
            "device",
            "meeting",
            "grant",
            "revoked_one",
            "revoked_two",
        )
    }

    async def seed_legacy() -> None:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        "insert into organizations (id, slug, name) "
                        "values (:id, 'feature-121', 'Feature 121')"
                    ),
                    {"id": ids["organization"]},
                )
                await conn.execute(
                    text(
                        "insert into workspaces (id, organization_id, slug, name) "
                        "values (:id, :organization_id, 'feature-121', 'Feature 121')"
                    ),
                    {"id": ids["workspace"], "organization_id": ids["organization"]},
                )
                await conn.execute(
                    text(
                        "insert into user_identities (id, organization_id, external_subject) "
                        "values (:id, :organization_id, 'feature-121@example.test')"
                    ),
                    {"id": ids["user"], "organization_id": ids["organization"]},
                )
                await conn.execute(
                    text(
                        "insert into registered_devices "
                        "(id, workspace_id, user_id, device_public_id, status, registration_state) "
                        "values (:id, :workspace_id, :user_id, 'feature-121-device', 'active', 'approved')"
                    ),
                    {
                        "id": ids["device"],
                        "workspace_id": ids["workspace"],
                        "user_id": ids["user"],
                    },
                )
                await conn.execute(
                    text(
                        "insert into meetings "
                        "(id, workspace_id, created_by_user_id, device_id, local_recording_id, "
                        "duration_seconds, status) "
                        "values (:id, :workspace_id, :user_id, :device_id, "
                        "'feature-121-legacy', 60, 'ready')"
                    ),
                    {
                        "id": ids["meeting"],
                        "workspace_id": ids["workspace"],
                        "user_id": ids["user"],
                        "device_id": ids["device"],
                    },
                )
                await conn.execute(
                    text(
                        "insert into meeting_share_grants "
                        "(id, workspace_id, meeting_id, grant_type, grantee_user_id, "
                        "created_by_user_id, status) "
                        "values (:id, :workspace_id, :meeting_id, 'user', :user_id, "
                        ":user_id, 'active')"
                    ),
                    {
                        "id": ids["grant"],
                        "workspace_id": ids["workspace"],
                        "meeting_id": ids["meeting"],
                        "user_id": ids["user"],
                    },
                )
        finally:
            await engine.dispose()

    asyncio.run(seed_legacy())
    command.upgrade(config, "head")

    async def upgraded_state() -> tuple[tuple[str, object, str, bool, bool], set[str]]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as conn:
                grant = (
                    await conn.execute(
                        text(
                            "select audience_type, audience_id, content_scope, "
                            "can_download, can_export from meeting_share_grants where id = :id"
                        ),
                        {"id": ids["grant"]},
                    )
                ).one()
                tables = await conn.run_sync(
                    lambda sync_conn: set(inspect(sync_conn).get_table_names())
                )
                return tuple(grant), tables
        finally:
            await engine.dispose()

    grant, tables = asyncio.run(upgraded_state())
    assert grant == ("user", ids["user"], "full_meeting", True, True)
    assert set(TENANT_TABLES + WORKER_ONLY_TABLES + OPERATOR_ONLY_TABLES) <= tables

    async def seed_two_revoked_cycles() -> None:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.begin() as conn:
                for grant_id in (ids["revoked_one"], ids["revoked_two"]):
                    await conn.execute(
                        text(
                            "insert into meeting_share_grants "
                            "(id, workspace_id, meeting_id, grant_type, grantee_user_id, "
                            "created_by_user_id, status, audience_type, audience_id) "
                            "values (:id, :workspace_id, :meeting_id, 'user', :user_id, "
                            ":user_id, 'revoked', 'user', :user_id)"
                        ),
                        {
                            "id": grant_id,
                            "workspace_id": ids["workspace"],
                            "meeting_id": ids["meeting"],
                            "user_id": ids["user"],
                        },
                    )
        finally:
            await engine.dispose()

    asyncio.run(seed_two_revoked_cycles())

    command.downgrade(config, "0030_expand_meeting_registry")

    async def downgraded_state() -> tuple[int, int, set[str], set[str]]:
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.connect() as conn:
                count = int(
                    await conn.scalar(
                        text("select count(*) from meeting_share_grants where id = :id"),
                        {"id": ids["grant"]},
                    )
                )
                revoked_count = int(
                    await conn.scalar(
                        text(
                            "select count(*) from meeting_share_grants "
                            "where meeting_id = :meeting_id and grantee_user_id = :user_id "
                            "and status = 'revoked'"
                        ),
                        {"meeting_id": ids["meeting"], "user_id": ids["user"]},
                    )
                )
                return await conn.run_sync(
                    lambda sync_conn: (
                        count,
                        revoked_count,
                        set(inspect(sync_conn).get_table_names()),
                        {
                            column["name"]
                            for column in inspect(sync_conn).get_columns("meeting_share_grants")
                        },
                    )
                )
        finally:
            await engine.dispose()

    legacy_count, revoked_count, downgraded_tables, grant_columns = asyncio.run(
        downgraded_state()
    )
    get_settings.cache_clear()
    assert legacy_count == 1
    assert revoked_count == 1
    assert not set(TENANT_TABLES + WORKER_ONLY_TABLES + OPERATOR_ONLY_TABLES) & downgraded_tables
    assert "audience_type" not in grant_columns
