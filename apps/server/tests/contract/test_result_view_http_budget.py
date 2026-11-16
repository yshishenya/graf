"""Real auth/renewal and pool cancellation, with a synthetic non-ledger handler."""

import asyncio
from contextlib import asynccontextmanager
from contextvars import Context
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import event, func, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID, DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.api import product_analytics_guard as guard_module
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
        engine = create_async_engine(url, pool_size=pool_size, max_overflow=0, pool_timeout=10,
                                     pool_pre_ping=True)
        try:
            await scenario(engine)
        finally:
            await engine.dispose()
    asyncio.run(run())


@asynccontextmanager
async def _postgres_response_gate(url):
    """Hold real PostgreSQL replies without replacing the driver's ping/close."""
    upstream = make_url(url)
    gate, tasks, relays, writers = asyncio.Event(), set(), set(), set()
    gate.set()

    def start(coro, *, root=False):
        task = asyncio.create_task(coro, context=Context())
        tasks.add(task)
        task.add_done_callback(tasks.discard)
        if root:
            relays.add(task)
            task.add_done_callback(relays.discard)
        return task

    async def relay(reader, writer):
        upstream_writer = None
        pumps = []
        writers.add(writer)
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(upstream.host, upstream.port)
            writers.add(upstream_writer)

            async def copy(source, target, held=False):
                while data := await source.read(65536):
                    if held:
                        await gate.wait()
                    target.write(data)
                    await target.drain()

            pumps = [start(copy(reader, upstream_writer)), start(copy(upstream_reader, writer, True))]
            await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in pumps:
                task.cancel()
            await asyncio.gather(*pumps, return_exceptions=True)
            own_writers = [writer] + ([upstream_writer] if upstream_writer is not None else [])
            for target in own_writers:
                target.close()
            await asyncio.gather(*(start(target.wait_closed()) for target in own_writers), return_exceptions=True)
            writers.difference_update(own_writers)

    server = await asyncio.start_server(lambda r, w: start(relay(r, w), root=True), "127.0.0.1", 0)
    try:
        yield upstream.set(host="127.0.0.1", port=server.sockets[0].getsockname()[1]), gate, tasks
    finally:
        server.close()
        await server.wait_closed()
        gate.set()
        for writer in list(writers):
            writer.close()
        async with asyncio.timeout(2):
            await asyncio.gather(*list(relays), return_exceptions=True)


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


@pytest.mark.parametrize("phase", ["auth", "renewal"])
def test_real_pre_ping_is_bounded_before_checkout_and_leaves_no_database_work(
    postgres_seeded_database_url, phase,
):
    async def scenario(engine):
        async with _postgres_response_gate(postgres_seeded_database_url) as (url, gate, relay_tasks):
            checkouts, invalidations = [], []

            async def begin_renewal_ping():
                gate.clear()

            app, _, session_id = await _setup(engine, before_response=begin_renewal_ping)
            request_engine = create_async_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True)
            foreign = None
            try:
                async with asyncio.timeout(5):
                    foreign = await request_engine.connect()
                    foreign_pid = await foreign.scalar(text("SELECT pg_backend_pid()"))
                    async with request_engine.connect() as db:
                        pid = await db.scalar(text("SELECT pg_backend_pid()"))
                app.state.db_sessionmaker = async_sessionmaker(request_engine, expire_on_commit=False)
                event.listen(request_engine.sync_engine, "checkout", lambda *args: checkouts.append(True))
                def invalidated(dbapi, record, error):
                    owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                    task = asyncio.current_task()
                    invalidations.append((type(error).__name__, owner is not None, task.cancelling(),
                                          record.in_use, record.dbapi_connection is dbapi,
                                          record.driver_connection is dbapi.driver_connection,
                                          bool(record.info.get(guard_module._RESULT_VIEW_CONNECTION_OWNER)),
                                          record.driver_connection.is_closed()))
                event.listen(request_engine.sync_engine, "invalidate", invalidated)
                if phase == "auth":
                    gate.clear()
                before = set(asyncio.all_tasks())
                # Release the synthetic outage if old cleanup cannot cancel it.
                watchdog = asyncio.get_running_loop().call_later(3, gate.set)
                try:
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                        began = monotonic()
                        response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                                     headers=_headers(session_id))
                        assert monotonic() - began < 2
                        assert response.json() == {"status": "unavailable"}
                finally:
                    watchdog.cancel()
                assert len(checkouts) == (0 if phase == "auth" else 2)
                assert invalidations == [("CancelledError", True, 1, True, True, True, False, True)]
                assert request_engine.pool.checkedout() == 1
                async with engine.connect() as observer:
                    row = (await observer.execute(text(
                        "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                    ), {"pid": pid})).first()
                    assert row is None or (row.state == "idle" and row.xact_start is None)
                    assert await observer.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                 {"pid": pid}) == 0
                assert set(asyncio.all_tasks()) - relay_tasks <= before
                gate.set()
                assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_pid
                assert await foreign.scalar(text("SELECT 1")) == 1
                await foreign.close()
                assert request_engine.pool.checkedout() == 0
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
            finally:
                gate.set()
                if foreign is not None:
                    await foreign.close()
                await request_engine.dispose()
    _run(postgres_seeded_database_url, scenario)


def test_real_physical_connect_cancellation_releases_its_socket_and_pool(postgres_seeded_database_url):
    async def scenario(engine):
        app, _, session_id = await _setup(engine)
        async with _postgres_response_gate(postgres_seeded_database_url) as (url, gate, relay_tasks):
            request_engine = create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
            app.state.db_sessionmaker = async_sessionmaker(request_engine, expire_on_commit=False)
            connected = []
            event.listen(request_engine.sync_engine, "connect", lambda *args: connected.append(True))
            gate.clear()
            before = set(asyncio.all_tasks())
            watchdog = asyncio.get_running_loop().call_later(3, gate.set)
            try:
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    began = monotonic()
                    response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                                 headers=_headers(session_id))
                    assert monotonic() - began < 2
                    assert response.json() == {"status": "unavailable"}
                assert not connected and request_engine.pool.checkedout() == 0
                # A separate database roundtrip also lets peer EOF finish in the relay.
                async with engine.connect() as observer:
                    assert await observer.scalar(text("SELECT 1")) == 1
                assert not relay_tasks and set(asyncio.all_tasks()) <= before
                gate.set()
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                assert connected == [True]
            finally:
                watchdog.cancel()
                gate.set()
                await request_engine.dispose()
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("phase", ["handler", "auth", "renewal"])
@pytest.mark.parametrize("fault", [False, True])
def test_session_close_rollback_is_bounded_in_its_real_child_task(
    postgres_seeded_database_url, monkeypatch, phase, fault,
):
    async def scenario(engine):
        async with _postgres_response_gate(postgres_seeded_database_url) as (url, gate, relay_tasks):
            request_engine = create_async_engine(url, pool_size=2, max_overflow=0, pool_pre_ping=True)
            foreign, target, rollbacks, checkins = None, {}, [], []

            async def locked(db):
                pid = await db.scalar(text("SELECT pg_backend_pid()"))
                await db.execute(select(AuthSession).where(AuthSession.id == session_id).with_for_update())
                connection = (await db.connection()).sync_connection
                proxy = connection.connection
                owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                transaction = db.sync_session.get_transaction()
                target.update(connection=connection, dbapi=proxy.dbapi_connection,
                              driver=proxy.driver_connection, owner=owner,
                              task=asyncio.current_task(), transaction=transaction, pid=pid, session=db.sync_session)
                target["entry"] = next(entry for entry, lease in owner.items()
                                       if lease[1] is proxy.dbapi_connection and lease[2] is proxy.driver_connection)
                target["awaiting_checkin"] = True
                assert owner.transactions[transaction][2] is target["task"]
                async with engine.connect() as observer:
                    row = (await observer.execute(text(
                        "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                    ), {"pid": pid})).one()
                    assert row.state == "idle in transaction" and row.xact_start is not None
                    assert await observer.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                 {"pid": pid}) > 0

            async def handler_close():
                async with app.state.db_sessionmaker() as db:
                    await locked(db)

            app, _, session_id = await _setup(engine, before_response=handler_close if phase == "handler" else None)
            app.state.db_sessionmaker = async_sessionmaker(request_engine, expire_on_commit=False)
            if phase != "handler":
                module = dependencies if phase == "auth" else session_renewal
                original = module.apply_tenant_context

                async def interrupted(db, context):
                    await original(db, context)
                    await locked(db)
                    if phase == "auth":
                        raise ProblemDetail(status=503, code="synthetic_auth_interrupted", title="Synthetic interruption")
                    raise SQLAlchemyError("synthetic renewal interrupted")

                monkeypatch.setattr(module, "apply_tenant_context", interrupted)

            def rollback(connection):
                if connection is not target.get("connection"):
                    return
                proxy = connection.connection
                assert proxy.dbapi_connection is target["dbapi"]
                assert proxy.driver_connection is target["driver"]
                assert guard_module._RESULT_VIEW_TASK_OWNER.get() is target["owner"]
                assert asyncio.current_task() is not target["task"]
                lease = connection.info[guard_module._RESULT_VIEW_CONNECTION_OWNER]
                root = target["owner"].transactions[target["transaction"]]
                assert lease[3] is asyncio.current_task() and root[2] is asyncio.current_task()
                rollbacks.append(asyncio.current_task())
                if fault:
                    gate.clear()

            def checkin(dbapi, record):
                if record is target.get("entry") and target.pop("awaiting_checkin", False):
                    checkins.append(dbapi is target["dbapi"] or dbapi is None)

            event.listen(request_engine.sync_engine, "rollback", rollback)
            event.listen(request_engine.sync_engine, "checkin", checkin)
            watchdog = None
            try:
                foreign = await request_engine.connect()
                foreign_pid = await foreign.scalar(text("SELECT pg_backend_pid()"))
                # Warm the second slot before the fault can be armed.
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                before = set(asyncio.all_tasks())
                watchdog = asyncio.get_running_loop().call_later(3, gate.set)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    began = monotonic()
                    response = await client.post(f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                                 headers=_headers(session_id))
                    assert monotonic() - began < 2
                assert len(rollbacks) == 1
                if fault:
                    assert response.status_code == 200 and response.json() == {"status": "unavailable"}
                elif phase == "auth":
                    assert response.status_code == 503 and response.json()["code"] == "synthetic_auth_interrupted"
                else:
                    assert response.status_code == 200 and response.json() == {"status": "accepted"}
                assert request_engine.pool.checkedout() == 1
                assert checkins == [True]
                assert not target["session"].in_transaction()
                assert not target["owner"]
                assert not [task for task in asyncio.all_tasks()
                            if task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is target["owner"]]
                assert set(asyncio.all_tasks()) - relay_tasks <= before
                async with engine.connect() as observer:
                    row = (await observer.execute(text(
                        "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                    ), {"pid": target["pid"]})).first()
                    assert row is None or (row.state == "idle" and row.xact_start is None)
                    assert await observer.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                 {"pid": target["pid"]}) == 0
                assert not target["owner"].transactions
                assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in target["session"].info
                gate.set()
                assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_pid
                assert await foreign.scalar(text("SELECT 1")) == 1
                await foreign.close()
                foreign = None
                assert request_engine.pool.checkedout() == 0
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
            finally:
                if watchdog is not None:
                    watchdog.cancel()
                gate.set()
                if foreign is not None:
                    await foreign.close()
                await request_engine.dispose()
    _run(postgres_seeded_database_url, scenario)
