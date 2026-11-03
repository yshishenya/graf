"""Real PostgreSQL proof for F270 FR-014/SC-007; no production data or roles."""

from __future__ import annotations

import asyncio
from uuid import UUID

import pytest
from sqlalchemy import event, func, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.fixtures.postgres_rls import validate_rls_test_database_url
from twobrain_rec_server.db import tenant_context as tenant

ORG, WORKSPACE, USER, DEVICE, AUTH, UPLOAD, SOURCE = (UUID(int=i) for i in range(1, 8))
TOKEN = "a" * 64
IDENTITY = {
    "app.organization_id": str(ORG),
    "app.workspace_id": str(WORKSPACE),
    "app.user_id": str(USER),
}
OPTIONAL = {
    "app.device_id": str(DEVICE),
    "app.auth_session_id": str(AUTH),
    "app.upload_session_id": str(UPLOAD),
    "app.auth_session_token_hash": TOKEN,
}

CONTEXTS = (
    [
        pytest.param(
            tenant.TenantDatabaseContext(ORG, WORKSPACE, USER, context_kind=kind),
            {**IDENTITY, "app.context_kind": kind},
            id=f"{kind}-minimal",
        )
        for kind in ("request", "worker")
    ]
    + [
        pytest.param(
            tenant.TenantDatabaseContext(ORG, WORKSPACE, USER, DEVICE, AUTH, UPLOAD, kind, TOKEN),
            {**IDENTITY, **OPTIONAL, "app.context_kind": kind},
            id=f"{kind}-full",
        )
        for kind in ("request", "worker")
    ]
    + [
        pytest.param(
            tenant.WorkspaceAuthContext(WORKSPACE, context_kind=kind),
            {"app.context_kind": kind, "app.workspace_id": str(WORKSPACE)},
            id=f"{kind}-minimal",
        )
        for kind in ("auth_public", "auth_bootstrap")
    ]
    + [
        pytest.param(
            tenant.WorkspaceAuthContext(WORKSPACE, ORG, USER, kind),
            {**IDENTITY, "app.context_kind": kind},
            id=f"{kind}-full",
        )
        for kind in ("auth_public", "auth_bootstrap")
    ]
    + [
        pytest.param(
            tenant.MaintenanceTenantContext("account_merge", "synthetic", "test", "account_merge"),
            {
                "app.context_kind": "maintenance",
                "app.maintenance_operation": "account_merge",
                "app.maintenance_actor": "synthetic",
                "app.maintenance_reason": "test",
                "app.maintenance_feature_area": "account_merge",
            },
            id="maintenance",
        ),
        pytest.param(
            tenant.AccountMergeTenantContext(AUTH, WORKSPACE, USER, SOURCE),
            {
                "app.context_kind": "account_merge",
                "app.workspace_id": str(WORKSPACE),
                "app.account_merge_intent_id": str(AUTH),
                "app.account_merge_survivor_user_id": str(USER),
                "app.account_merge_source_user_id": str(SOURCE),
            },
            id="account-merge",
        ),
        pytest.param(
            tenant.AuthSessionLookupContext(TOKEN),
            {"app.context_kind": "auth_session_lookup", "app.auth_session_token_hash": TOKEN},
            id="session-lookup",
        ),
        pytest.param(
            tenant.AuthProviderUnlinkContext(WORKSPACE, ORG, USER),
            {**IDENTITY, "app.context_kind": "auth_provider_unlink"},
            id="provider-unlink",
        ),
        pytest.param(
            tenant.AuthCallbackLookupContext("synthetic-nonce"),
            {
                "app.context_kind": "auth_callback_lookup",
                "app.auth_callback_state_nonce": "synthetic-nonce",
            },
            id="callback-lookup",
        ),
        pytest.param(
            tenant.AuthReferralLookupContext(WORKSPACE, USER, TOKEN),
            {
                "app.context_kind": "auth_referral_lookup",
                "app.workspace_id": str(WORKSPACE),
                "app.user_id": str(USER),
                "app.referral_token_hash": TOKEN,
            },
            id="referral-minimal",
        ),
        pytest.param(
            tenant.AuthReferralLookupContext(WORKSPACE, USER, TOKEN, AUTH),
            {
                "app.context_kind": "auth_referral_lookup",
                "app.workspace_id": str(WORKSPACE),
                "app.user_id": str(USER),
                "app.referral_token_hash": TOKEN,
                "app.referral_link_id": str(AUTH),
            },
            id="referral-full",
        ),
        pytest.param(
            tenant.AuthReferralUserLookupContext(USER),
            {"app.context_kind": "auth_referral_user_lookup", "app.user_id": str(USER)},
            id="referral-user",
        ),
        pytest.param(
            tenant.ReferralLandingLookupContext(TOKEN),
            {"app.context_kind": "referral_landing_lookup", "app.referral_token_hash": TOKEN},
            id="referral-landing",
        ),
        pytest.param(
            tenant.ShareInvitationLookupContext(WORKSPACE, "synthetic-nonce"),
            {
                "app.context_kind": "share_invitation_lookup",
                "app.workspace_id": str(WORKSPACE),
                "app.share_invitation_continuation_nonce": "synthetic-nonce",
            },
            id="share-invitation",
        ),
        pytest.param(
            tenant.SharedWithMeLookupContext(USER),
            {"app.context_kind": "shared_with_me_lookup", "app.user_id": str(USER)},
            id="shared-with-me",
        ),
    ]
)


@pytest.fixture
async def context_database(postgres_worker_database_url):
    url = validate_rls_test_database_url(
        postgres_worker_database_url, variable_name="test database"
    )
    engine = create_async_engine(url, pool_size=2, max_overflow=0)
    statements = []

    def count(_connection, _cursor, statement, _parameters, _context, _many):
        statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", count)
    try:
        yield engine, statements
    finally:
        await engine.dispose()


async def _settings(database, names):
    row = (
        await database.execute(select(*(func.current_setting(name, True) for name in names)))
    ).one()
    return dict(zip(names, row, strict=True))


@pytest.mark.parametrize(("context", "expected"), CONTEXTS)
@pytest.mark.parametrize("entry", ["session", "connection"])
async def test_context_values_and_query_budget(context_database, context, expected, entry):
    engine, statements = context_database
    factory = async_sessionmaker(engine) if entry == "session" else engine.connect
    async with factory() as database:
        if entry == "session":
            await tenant.apply_tenant_context(database, context)
        else:
            await tenant.apply_tenant_context_to_connection(database, context)
        assert database.info["tenant_context"] == expected
        assert len(statements) == (2 if entry == "session" else 1), entry
        assert await _settings(database, expected) == expected
        if entry == "session":
            statements.clear()
            await tenant.rehydrate_tenant_context(database)
            assert len(statements) == 1, "rehydrate inside an existing transaction"
            assert await _settings(database, expected) == expected


@pytest.mark.parametrize("boundary", ["commit", "rollback"])
@pytest.mark.parametrize("rehydrate", [False, True])
async def test_session_replays_before_read_after_transaction(context_database, boundary, rehydrate):
    engine, statements = context_database
    expected = {**IDENTITY, **OPTIONAL, "app.context_kind": "worker"}
    async with async_sessionmaker(engine)() as database:
        await tenant.apply_tenant_context(
            database,
            tenant.TenantDatabaseContext(
                ORG, WORKSPACE, USER, DEVICE, AUTH, UPLOAD, "worker", TOKEN
            ),
        )
        await getattr(database, boundary)()
        statements.clear()
        if rehydrate:
            await tenant.rehydrate_tenant_context(database)
        assert await _settings(database, expected) == expected
        assert len(statements) == (3 if rehydrate else 2)  # Includes the value probe.


async def test_replacing_context_applies_before_next_read(context_database):
    engine, statements = context_database
    async with async_sessionmaker(engine)() as database:
        await tenant.apply_tenant_context(
            database, tenant.TenantDatabaseContext(ORG, WORKSPACE, USER)
        )
        statements.clear()
        await tenant.apply_tenant_context(
            database, tenant.TenantDatabaseContext(SOURCE, DEVICE, AUTH)
        )
        assert len(statements) == 1
        assert await _settings(database, IDENTITY) == {
            "app.organization_id": str(SOURCE),
            "app.workspace_id": str(DEVICE),
            "app.user_id": str(AUTH),
        }


@pytest.mark.parametrize("saved", [None, {}])
async def test_absent_or_empty_context_does_not_issue_settings_sql(context_database, saved):
    engine, statements = context_database
    async with async_sessionmaker(engine)() as database:
        if saved is not None:
            database.info["tenant_context"] = saved
        await tenant.rehydrate_tenant_context(database)
        assert not statements
        assert await database.scalar(select(1)) == 1
        assert len(statements) == 1  # after_begin must not emit an empty SELECT.


@pytest.mark.parametrize("boundary", ["commit", "rollback"])
async def test_transaction_local_settings_do_not_leak_on_physical_connection_reuse(
    context_database, boundary
):
    engine, _ = context_database
    # Hold one of two slots so the next two checkouts must reuse the same backend.
    async with engine.connect(), engine.connect() as first:
        pid = await first.scalar(select(func.pg_backend_pid()))
        await tenant.apply_tenant_context_to_connection(
            first,
            tenant.TenantDatabaseContext(
                ORG, WORKSPACE, USER, DEVICE, AUTH, UPLOAD, "request", TOKEN
            ),
        )
        await getattr(first, boundary)()
        await first.close()
        async with engine.connect() as second:
            assert await second.scalar(select(func.pg_backend_pid())) == pid
            assert all(
                value in (None, "")
                for value in (
                    await _settings(second, {**IDENTITY, **OPTIONAL, "app.context_kind": ""})
                ).values()
            )
            await tenant.apply_tenant_context_to_connection(
                second, tenant.TenantDatabaseContext(SOURCE, DEVICE, AUTH)
            )
            assert await _settings(second, IDENTITY) == {
                "app.organization_id": str(SOURCE),
                "app.workspace_id": str(DEVICE),
                "app.user_id": str(AUTH),
            }
            assert all(
                value in (None, "") for value in (await _settings(second, OPTIONAL)).values()
            )


async def test_concurrent_sessions_keep_distinct_contexts(context_database):
    engine, _ = context_database
    ready = [asyncio.Event(), asyncio.Event()]

    async def read(index, context):
        async with async_sessionmaker(engine)() as database:
            await tenant.apply_tenant_context(database, context)
            ready[index].set()
            await asyncio.wait_for(ready[1 - index].wait(), timeout=5)
            return await _settings(database, IDENTITY)

    first, second = await asyncio.gather(
        read(0, tenant.TenantDatabaseContext(ORG, WORKSPACE, USER)),
        read(1, tenant.TenantDatabaseContext(SOURCE, DEVICE, AUTH)),
    )
    assert first == IDENTITY
    assert second == {
        "app.organization_id": str(SOURCE),
        "app.workspace_id": str(DEVICE),
        "app.user_id": str(AUTH),
    }


async def test_failed_settings_sql_requires_rollback_before_read(context_database):
    engine, _ = context_database
    async with async_sessionmaker(engine)() as database:
        await tenant.apply_tenant_context(
            database, tenant.TenantDatabaseContext(ORG, WORKSPACE, USER)
        )
        saved = dict(database.info["tenant_context"])
        database.info["tenant_context"] = {**saved, "invalid_setting": "synthetic"}
        with pytest.raises(DBAPIError):
            await tenant.rehydrate_tenant_context(database)
        database.info["tenant_context"] = saved
        with pytest.raises(DBAPIError):
            await database.execute(text("select 1"))
        await database.rollback()
        assert await _settings(database, saved) == saved
