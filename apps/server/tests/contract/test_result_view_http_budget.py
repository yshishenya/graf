"""Real auth/renewal and pool cancellation, with a synthetic non-ledger handler."""

import asyncio
from contextvars import Context
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID, DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.api.problems import ProblemDetail, problem_exception_handler
from twobrain_rec_server.api.product_analytics_guard import ProductAnalyticsIngressGuard
from twobrain_rec_server.auth import dependencies, session_renewal
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.cabinet.web_routes.support import (
    PrincipalDependency,
    WebCSRFDependency,
    WebTenantDependency,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    ProductActivationMilestone,
)

TOKEN = "synthetic-outer-budget-session"
SECRET = "synthetic-outer-budget-csrf-secret"
MEETING_ID = "70000000-0000-0000-0000-000000000001"


async def _setup(engine, *, before_response=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    session_id = uuid4()
    async with sessions() as db:
        db.add(AuthSession(
            id=session_id, user_id=USER_ID, workspace_id=WORKSPACE_ID, device_id=DEVICE_ID,
            provider="email", session_token_hash=hash_token(TOKEN), status="active",
            issued_at=datetime.now(UTC) - timedelta(days=1),
            last_seen_at=datetime.now(UTC) - timedelta(minutes=10),
            expires_at=datetime.now(UTC) + timedelta(minutes=10),
        ))
        await db.flush()
        db.add(AuthSessionDeviceBinding(auth_session_id=session_id, registered_device_id=DEVICE_ID,
                                       device_state="trusted"))
        await db.commit()
    app = FastAPI()
    app.state.settings = Settings(web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID, web_csrf_secret=SECRET)
    app.state.web_csrf_secret = SECRET
    app.state.db_sessionmaker = sessions
    app.add_exception_handler(ProblemDetail, problem_exception_handler)
    app.middleware("http")(session_renewal.session_renewal_middleware)
    app.add_middleware(ProductAnalyticsIngressGuard)

    @app.post(f"/meetings/{MEETING_ID}/result-viewed", dependencies=[WebCSRFDependency])
    @app.post(f"/desktop/meetings/{MEETING_ID}/result-viewed", dependencies=[WebCSRFDependency])
    async def endpoint(request: Request, tenant: TenantScope = WebTenantDependency,
                       principal: AuthenticatedPrincipal = PrincipalDependency):
        assert tenant.workspace_id == WORKSPACE_ID and principal.session_id == session_id
        assert await request.json() == {"proof": "synthetic"}
        if before_response is not None:
            await before_response()
        # This is deliberately not the future T112 ledger handler.
        return JSONResponse({"status": "accepted"})

    return app, sessions, session_id


def _headers(session_id, transport="native", csrf=True):
    if transport == "native":
        return {"X-Auth-Session": TOKEN, "Accept": "application/json"}
    return {"Cookie": f"{AUTH_SESSION_COOKIE_NAME}={TOKEN}", "Accept": "application/json",
            **({"X-CSRF-Token": issue_csrf_token(session_id=session_id, secret=SECRET)} if csrf else {})}


def _run(url, scenario, *, pool_size=1):
    async def run():
        engine = create_async_engine(url, pool_size=pool_size, max_overflow=0, pool_timeout=10)
        try:
            await scenario(engine)
        finally:
            await engine.dispose()
    asyncio.run(run())


@pytest.mark.parametrize("embedded,transport", [(False, "native"), (True, "native"),
                                               (False, "cookie"), (True, "cookie")])
def test_bounded_alias_keeps_real_auth_csrf_and_committed_renewal(
    postgres_seeded_database_url, embedded, transport,
):
    async def scenario(engine):
        app, sessions, session_id = await _setup(engine)
        path = ("/desktop" if embedded else "") + f"/meetings/{MEETING_ID}/result-viewed"
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            response = await client.post(path, json={"proof": "synthetic"}, headers=_headers(session_id, transport))
        assert response.status_code == 200, response.text
        assert response.json() == {"status": "accepted"}
        assert response.headers["cache-control"] == "private, no-store"
        assert ("set-cookie" if transport == "cookie" else "x-graf-auth-expires-at") in response.headers
        async with sessions() as db:
            expiry = await db.scalar(select(AuthSession.expires_at).where(AuthSession.id == session_id))
            assert expiry > datetime.now(UTC) + timedelta(days=29)
            assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
        assert engine.pool.checkedout() == 0
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("auth", ["missing", "csrf"])
def test_guard_preserves_real_missing_auth_or_csrf_refusal(postgres_seeded_database_url, auth):
    async def scenario(engine):
        app, _, session_id = await _setup(engine)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                         headers={} if auth == "missing" else _headers(session_id, "cookie", False))
        assert response.status_code == (401 if auth == "missing" else 403), response.text
        assert response.headers["cache-control"] == "private, no-store"
        assert "set-cookie" not in response.headers and "x-graf-auth-expires-at" not in response.headers
        assert engine.pool.checkedout() == 0
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("phase", ["auth", "renewal"])
def test_real_small_pool_wait_is_cancelled_without_holding_an_extra_connection(
    postgres_seeded_database_url, phase,
):
    async def scenario(engine):
        held = None

        async def hold_pool():
            nonlocal held

            async def acquire_as_another_request():
                return await engine.connect()

            held = await asyncio.create_task(acquire_as_another_request(), context=Context())

        app, _, session_id = await _setup(engine, before_response=hold_pool if phase == "renewal" else None)
        if phase == "auth":
            await hold_pool()
        before = set(asyncio.all_tasks())
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                began = monotonic()
                response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                             headers=_headers(session_id))
                assert monotonic() - began < 2
                assert response.json() == {"status": "unavailable"}
            assert engine.pool.checkedout() == 1
            assert set(asyncio.all_tasks()) == before
        finally:
            await held.close()
        assert engine.pool.checkedout() == 0
        async with engine.connect() as db:
            assert await db.scalar(text("SELECT 1")) == 1
    _run(postgres_seeded_database_url, scenario)


def test_cancelled_request_cannot_terminate_a_parallel_foreign_connection(
    postgres_seeded_database_url, monkeypatch,
):
    async def scenario(engine):
        app, _, session_id = await _setup(engine)
        original = dependencies.apply_tenant_context

        async def slow(db, context):
            await original(db, context)
            await db.execute(text("SELECT pg_sleep(10)"))

        monkeypatch.setattr(dependencies, "apply_tenant_context", slow)
        async with engine.connect() as foreign:
            foreign_pid = await foreign.scalar(text("SELECT pg_backend_pid()"))
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                             headers=_headers(session_id))
            assert response.json() == {"status": "unavailable"}
            assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_pid
            assert await foreign.scalar(text("SELECT 1")) == 1
            assert engine.pool.checkedout() == 1
        assert engine.pool.checkedout() == 0
    _run(postgres_seeded_database_url, scenario, pool_size=2)


def test_renewal_commit_before_timeout_is_not_repeated_or_reported_as_rolled_back(
    postgres_seeded_database_url,
):
    async def scenario(engine):
        slow_commit = False
        commits = []

        async def start_slow_commit():
            nonlocal slow_commit
            slow_commit = True

        class SlowCommitSession(AsyncSession):
            async def commit(self):
                await super().commit()
                if slow_commit:
                    commits.append(True)
                    await asyncio.sleep(10)

        app, sessions, session_id = await _setup(engine, before_response=start_slow_commit)
        app.state.db_sessionmaker = async_sessionmaker(engine, expire_on_commit=False, class_=SlowCommitSession)
        before = set(asyncio.all_tasks())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            began = monotonic()
            response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                         headers=_headers(session_id))
            assert monotonic() - began < 2
            assert response.json() == {"status": "unavailable"}
        assert commits == [True] and engine.pool.checkedout() == 0
        assert set(asyncio.all_tasks()) == before
        async with sessions() as db:
            expiry = await db.scalar(select(AuthSession.expires_at).where(AuthSession.id == session_id))
            assert expiry > datetime.now(UTC) + timedelta(days=29)
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("phase", ["auth", "renewal"])
def test_actual_sleeping_sql_is_cancelled_and_pool_remains_usable(
    postgres_seeded_database_url, monkeypatch, phase,
):
    async def scenario(engine):
        app, _, session_id = await _setup(engine)
        module = dependencies if phase == "auth" else session_renewal
        original = module.apply_tenant_context
        entered = []

        async def slow(db, context):
            await original(db, context)
            entered.append(True)
            await db.execute(text("SELECT pg_sleep(10)"))

        monkeypatch.setattr(module, "apply_tenant_context", slow)
        before = set(asyncio.all_tasks())
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
            began = monotonic()
            response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                         headers=_headers(session_id))
            assert monotonic() - began < 2
            assert response.json() == {"status": "unavailable"}
        assert entered and engine.pool.checkedout() == 0
        assert set(asyncio.all_tasks()) == before
        async with engine.connect() as db:
            assert await db.scalar(text("SELECT 1")) == 1
    _run(postgres_seeded_database_url, scenario)
