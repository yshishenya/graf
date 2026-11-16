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
from sqlalchemy.orm import Session, SessionTransactionOrigin

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
async def _postgres_response_gate(url, *, eof_gate=None, eof_seen=None, streams=None):
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
        stream = None
        if streams is not None:
            stream = {"root": asyncio.current_task(), "eof_gate": asyncio.Event(),
                      "eof_seen": asyncio.Event(), "client_eof_seen": asyncio.Event(),
                      "done": asyncio.Event(), "writers": [writer],
                      "response_gate": asyncio.Event(), "response_held": asyncio.Event()}
            stream["eof_gate"].set()
            stream["response_gate"].set()
            streams.append(stream)
        writers.add(writer)
        try:
            upstream_reader, upstream_writer = await asyncio.open_connection(upstream.host, upstream.port)
            writers.add(upstream_writer)
            if stream is not None:
                stream["writers"].append(upstream_writer)

            async def copy(source, target, held=False):
                while data := await source.read(65536):
                    if held:
                        await gate.wait()
                        if stream is not None:
                            if not stream["response_gate"].is_set():
                                stream["response_held"].set()
                            await stream["response_gate"].wait()
                    target.write(data)
                    await target.drain()
                if not held and stream is not None:
                    stream["client_eof_seen"].set()
                if held and stream is not None:
                    stream["eof_seen"].set()
                    await stream["eof_gate"].wait()
                if held and eof_gate is not None:
                    eof_seen.set()
                    await eof_gate.wait()

            pumps = [start(copy(reader, upstream_writer)), start(copy(upstream_reader, writer, True))]
            if stream is not None:
                stream["pumps"] = pumps
            await asyncio.wait(pumps, return_when=asyncio.FIRST_COMPLETED)
        finally:
            for task in pumps:
                task.cancel()
            await asyncio.gather(*pumps, return_exceptions=True)
            own_writers = [writer] + ([upstream_writer] if upstream_writer is not None else [])
            for target in own_writers:
                target.close()
            closing = [start(target.wait_closed()) for target in own_writers]
            if stream is not None:
                stream["wait_closed"] = closing
            await asyncio.gather(*closing, return_exceptions=True)
            writers.difference_update(own_writers)
            if stream is not None:
                stream["done"].set()

    server = await asyncio.start_server(lambda r, w: start(relay(r, w), root=True), "127.0.0.1", 0)
    try:
        yield upstream.set(host="127.0.0.1", port=server.sockets[0].getsockname()[1]), gate, tasks
    finally:
        server.close()
        await server.wait_closed()
        gate.set()
        if eof_gate is not None:
            eof_gate.set()
        for stream in streams or ():
            stream["eof_gate"].set()
            stream["response_gate"].set()
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


@pytest.mark.parametrize("fault", [False, True])
def test_native_driver_close_finishes_with_its_socket_within_the_request_budget(
    postgres_seeded_database_url, fault,
):
    async def scenario(engine):
        eof_gate, eof_seen = asyncio.Event(), asyncio.Event()
        eof_gate.set()
        async with _postgres_response_gate(
            postgres_seeded_database_url, eof_gate=eof_gate, eof_seen=eof_seen,
        ) as (url, data_gate, relay_tasks):
            request_engine = create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
            target, connections, invalidations, closes, observed = {}, [], [], [], {}
            foreign = observer = watchdog = None
            watchdog_fired = []

            async def native_close():
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                    pid = await db.scalar(text("SELECT pg_backend_pid()"))
                    await db.commit()
                    proxy = db.sync_connection.connection
                    owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                    entry, lease = next((entry, lease) for entry, lease in owner.items()
                                        if lease[1] is proxy.dbapi_connection)
                    assert lease[2] is proxy.driver_connection and lease[3] is asyncio.current_task()
                    assert not owner.transactions and not proxy.driver_connection.is_closed()
                    assert not proxy.driver_connection.is_in_transaction()
                    target.update(owner=owner, task=asyncio.current_task(), entry=entry, lease=lease,
                                  dbapi=proxy.dbapi_connection, driver=proxy.driver_connection, pid=pid)
                    if fault:
                        eof_gate.clear()
                    await db.invalidate(exception=None)
                    target["invalidate_returned"] = True

            app, sessions, session_id = await _setup(engine, before_response=native_close)

            def connected(dbapi, entry):
                connections.append(dbapi)

            def invalidated(dbapi, entry, exception):
                assert dbapi is target["dbapi"] and entry is target["entry"] and exception is None
                invalidations.append(monotonic())

            def closing(dbapi, entry):
                if dbapi is not target.get("dbapi") or closes:
                    return
                assert entry is target["entry"] and connections == [dbapi]
                assert entry.dbapi_connection is dbapi and entry.driver_connection is target["driver"]
                assert guard_module._RESULT_VIEW_TASK_OWNER.get() is target["owner"]
                assert asyncio.current_task() is target["task"] and entry.in_use
                assert target["owner"].get(entry) is target["lease"]
                assert entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] is target["lease"]
                target["preempted"] = target["driver"].is_closed()
                if not target["preempted"]:
                    assert not target["driver"].is_in_transaction()
                assert len(invalidations) == 1
                closes.append(monotonic())
                if fault:
                    eof_gate.clear()

            async def observe():
                assert guard_module._RESULT_VIEW_TASK_OWNER.get() is None
                async with asyncio.timeout(1):
                    # A client abort can finish both relay pumps before upstream EOF is published.
                    while not eof_seen.is_set() and not (closes and not relay_tasks):
                        await asyncio.sleep(0)
                    assert data_gate.is_set() and (eof_gate.is_set() is not fault)
                    async with engine.connect() as db:
                        while await db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE pid=:pid"),
                                              {"pid": target["pid"]}):
                            await db.rollback()
                            await asyncio.sleep(0)
                        assert await db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                               {"pid": target["pid"]}) == 0
                    assert target["task"].cancelling() == 0
                    observed.update(at=monotonic(), closed_flag=target["driver"].is_closed())
                    if fault and not target["preempted"]:
                        assert observed["closed_flag"] and relay_tasks
                        assert not target["task"].done() and "invalidate_returned" not in target

            event.listen(request_engine.sync_engine, "connect", connected)
            event.listen(request_engine.sync_engine, "invalidate", invalidated)
            event.listen(request_engine.sync_engine, "close", closing)
            try:
                foreign = await engine.connect()
                foreign_pid = await foreign.scalar(text("SELECT pg_backend_pid()"))
                observer = asyncio.create_task(observe(), context=Context())
                before = set(asyncio.all_tasks())

                def release_watchdog():
                    watchdog_fired.append(True)
                    eof_gate.set()

                watchdog = asyncio.get_running_loop().call_later(3, release_watchdog)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    began = monotonic()
                    try:
                        response = await client.post(f"/meetings/{MEETING_ID}/result-viewed",
                                                     json={"proof": "synthetic"}, headers=_headers(session_id))
                    finally:
                        await observer
                        assert len(invalidations) == len(closes) == 1 and observed["at"] >= closes[0]
                        print({"native_close_fault": fault, "elapsed": round(monotonic() - began, 3),
                               "upstream_eof": eof_seen.is_set(), "backend_gone_before_cancel": True,
                               "close_path": "preemptive_abort" if target["preempted"] else "native_grace",
                               "early_closed_flag": observed["closed_flag"],
                               "watchdog_fired": bool(watchdog_fired)})
                    async with asyncio.timeout_at(asyncio.get_running_loop().time() + max(0, 2 - (monotonic() - began))):
                        while relay_tasks:
                            await asyncio.sleep(0)
                    assert monotonic() - began < 2 and not watchdog_fired
                assert response.status_code == 200
                assert target["preempted"]
                assert response.json() in ([{"status": "accepted"}, {"status": "unavailable"}]
                                           if fault else [{"status": "accepted"}])
                assert data_gate.is_set() and (eof_gate.is_set() is not fault)
                assert target["driver"].is_closed() and not target["owner"] and not target["owner"].transactions
                assert not [task for task in asyncio.all_tasks()
                            if task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is target["owner"]]
                assert not relay_tasks and set(asyncio.all_tasks()) <= before
                assert request_engine.pool.checkedout() == 0
                if response.json() == {"status": "accepted"}:
                    assert target["invalidate_returned"]
                    assert "x-graf-auth-expires-at" in response.headers
                async with sessions() as db:
                    if response.json() == {"status": "accepted"}:
                        expiry = await db.scalar(select(AuthSession.expires_at).where(AuthSession.id == session_id))
                        assert expiry > datetime.now(UTC) + timedelta(days=29)
                    assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
                assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_pid
                assert await foreign.scalar(text("SELECT 1")) == 1
                eof_gate.set()
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                    assert await db.scalar(text("SELECT pg_backend_pid()")) != target["pid"]
                    assert db.sync_connection.connection.driver_connection is not target["driver"]
            finally:
                if watchdog is not None:
                    watchdog.cancel()
                eof_gate.set()
                if observer is not None:
                    observer.cancel()
                    await asyncio.gather(observer, return_exceptions=True)
                if "owner" in target:
                    await asyncio.gather(*(task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                                           and task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER)
                                           is target["owner"]), return_exceptions=True)
                if foreign is not None:
                    await foreign.close()
                await request_engine.dispose()
    _run(postgres_seeded_database_url, scenario, pool_size=3)


@pytest.mark.parametrize("fault", [False, True])
def test_pool_generation_replacement_before_checkout_is_bounded(postgres_seeded_database_url, fault):
    async def scenario(engine):
        streams, generations, invalidations, returns, target = [], [], [], [], {}
        close_seen = asyncio.Event()
        request_roots = []
        close_armed = True
        async with _postgres_response_gate(postgres_seeded_database_url, streams=streams) as (url, gate, relay_tasks):
            request_engine = create_async_engine(url, pool_size=3, max_overflow=0, pool_pre_ping=True)
            app, sessions, session_id = await _setup(engine)
            app.state.db_sessionmaker = async_sessionmaker(request_engine, expire_on_commit=False)
            foreign = primer = old_target = observer_db = observer = watchdog = post = None
            watchdog_fired = []
            held = []

            def connected(dbapi, entry):
                assert len(streams) == len(generations) + 1
                generations.append({"dbapi": dbapi, "entry": entry, "driver": entry.driver_connection,
                                    "stream": streams[-1]})

            def invalidated(dbapi, entry, exception):
                invalidations.append((dbapi, entry, exception))

            def reset(dbapi, entry, state):
                returns.append(("reset", dbapi, entry, state.asyncio_safe,
                                state.terminate_only, state.transaction_was_reset))

            def checkin(dbapi, entry):
                returns.append(("checkin", dbapi, entry))

            def created(session, transaction):
                if session.bind is request_engine.sync_engine and transaction.parent is None:
                    owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                    if owner is not None:
                        request_roots.append((owner, transaction, asyncio.current_task()))

            def closing(dbapi, entry):
                nonlocal close_armed
                if not close_armed or dbapi is not target.get("dbapi"):
                    return
                close_armed = False
                try:
                    task, owner = asyncio.current_task(), guard_module._RESULT_VIEW_TASK_OWNER.get()
                    root = next(iter(owner.transactions.values())) if owner is not None and owner.transactions else None
                    transaction = root[1] if root is not None else None
                    session = transaction.session if transaction is not None else None
                    witness = owner.unbound_roots.get(transaction) if owner is not None else None
                    target.update(owner=owner, task=task, root=root, close_at=monotonic(),
                                  root_flags=(transaction.is_active, session.is_active) if session is not None else None,
                                  witness=witness, native_closed=target["driver"].is_closed())
                    target["close_checks"] = [
                        entry is target["entry"], not entry.in_use, entry.dbapi_connection is dbapi,
                        entry.driver_connection is target["driver"], dbapi.driver_connection is target["driver"],
                        owner is not None and not owner and not owner.failed and len(owner.transactions) == 1,
                        root is not None and root[0] is owner and root[2] is task,
                        task is not None and not task.cancelling()
                        and task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is owner,
                        witness is not None and witness[0] is root and witness[1] is task,
                        session is not None and session.get_transaction() is transaction and session.in_transaction()
                        and not session.in_nested_transaction()
                        and session.info.get(guard_module._RESULT_VIEW_TRANSACTION_OWNER) is root,
                        transaction is not None and transaction.parent is None and not transaction.nested
                        and transaction.origin is SessionTransactionOrigin.AUTOBEGIN,
                        target["root_flags"] == (False, False), len(generations) == 4,
                        not any(key in entry.info for key in (
                            guard_module._RESULT_VIEW_CONNECTION_OWNER, guard_module._RESULT_VIEW_INITIALIZATION_OWNER,
                            guard_module._RESULT_VIEW_TRANSACTION_OWNER,
                        )),
                        any(saved_owner is owner and saved_root is transaction and saved_task is task
                            for saved_owner, saved_root, saved_task in request_roots),
                    ]
                except Exception as error:
                    target["snapshot_error"] = type(error).__name__
                finally:
                    close_seen.set()

            async def observe():
                assert guard_module._RESULT_VIEW_TASK_OWNER.get() is None
                async with asyncio.timeout_at(deadline):
                    await close_seen.wait()
                    assert all(target.get("close_checks", ())) and "snapshot_error" not in target
                    # terminate() ends the client pump; FIRST_COMPLETED may cancel server EOF observation.
                    await target["stream"]["client_eof_seen"].wait()
                    await target["stream"]["done"].wait()
                    assert gate.is_set() and (target["stream"]["eof_gate"].is_set() is not fault)
                    while await observer_db.scalar(text("SELECT count(*) FROM pg_stat_activity WHERE pid=:pid"),
                                                  {"pid": target["pid"]}):
                        await observer_db.rollback()
                        await asyncio.sleep(0)
                    assert await observer_db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                    {"pid": target["pid"]}) == 0
                    await observer_db.rollback()
                    assert target["task"].cancelling() == 0
                    assert target["driver"].is_closed()
                    target["observed"] = True

            for name, callback in [("connect", connected), ("invalidate", invalidated), ("reset", reset),
                                   ("checkin", checkin), ("close", closing)]:
                event.listen(request_engine.sync_engine, name, callback)
            event.listen(Session, "after_transaction_create", created)
            try:
                for _ in range(3):
                    db = await request_engine.connect()
                    held.append(db)
                    generations[-1]["pid"] = await db.scalar(text("SELECT pg_backend_pid()"))
                    assert await db.scalar(text("SELECT 1")) == 1
                    await db.commit()
                foreign, primer, old_target = held
                foreign_generation, primer_generation = generations[:2]
                target.update(generations[2])
                await primer.close()
                primer = None
                await old_target.close()
                old_target = None
                assert not target["entry"].in_use and not target["entry"].info
                observer_db = await engine.connect()
                row = (await observer_db.execute(text(
                    "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                ), {"pid": target["pid"]})).one()
                assert row.state == "idle" and row.xact_start is None
                assert await observer_db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                {"pid": target["pid"]}) == 0
                assert await observer_db.scalar(text("SELECT pg_terminate_backend(:pid)"),
                                                {"pid": primer_generation["pid"]}) is True
                await observer_db.rollback()
                primer = await request_engine.connect()
                assert len(generations) == 4 and generations[-1]["entry"] is primer_generation["entry"]
                assert len(invalidations) == 1 and invalidations[0][0] is primer_generation["dbapi"]
                assert invalidations[0][1] is primer_generation["entry"] and invalidations[0][2] is not None
                primer_pid = await primer.scalar(text("SELECT pg_backend_pid()"))
                assert primer_pid != primer_generation["pid"]
                await primer.commit()
                async with asyncio.timeout(1):
                    await primer_generation["stream"]["done"].wait()
                    while not primer_generation["stream"]["root"].done():
                        await asyncio.sleep(0)
                assert request_engine.pool.checkedout() == 2 and not target["entry"].in_use
                returns.clear()
                if fault:
                    target["stream"]["eof_gate"].clear()
                began = monotonic()
                deadline = asyncio.get_running_loop().time() + 2
                observer = asyncio.create_task(observe(), context=Context())
                before = set(asyncio.all_tasks())

                def release_watchdog():
                    watchdog_fired.append(True)
                    target["stream"]["eof_gate"].set()

                watchdog = asyncio.get_running_loop().call_later(3, release_watchdog)
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                    try:
                        post = asyncio.create_task(client.post(f"/meetings/{MEETING_ID}/result-viewed",
                                                              json={"proof": "synthetic"}, headers=_headers(session_id)))
                        response = await post
                    finally:
                        print({"pool_replacement_fault": fault, "elapsed": round(monotonic() - began, 3),
                               "close_before_checkout": close_seen.is_set(), "upstream_eof": target["stream"]["eof_seen"].is_set(),
                               "client_eof": target["stream"]["client_eof_seen"].is_set(),
                               "root_flags": target.get("root_flags"), "close_checks": target.get("close_checks"),
                               "snapshot_error": target.get("snapshot_error"), "native_closed": target.get("native_closed"),
                               "backend_gone_before_cancel": target.get("observed", False),
                               "watchdog_fired": bool(watchdog_fired)})
                    async with asyncio.timeout_at(deadline):
                        await observer
                        assert target["close_checks"] and all(target["close_checks"])
                        assert target["native_closed"]
                        await target["stream"]["done"].wait()
                        while not target["stream"]["root"].done():
                            await asyncio.sleep(0)
                        assert response.status_code == 200
                        # Physical disposal bypasses the held graceful-close EOF before it can wait.
                        assert response.json() == {"status": "accepted"}
                        assert not target["owner"] and not target["owner"].transactions and not target["owner"].unbound_roots
                        assert not target["root"][1].session.in_transaction()
                        assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in target["root"][1].session.info
                        assert not [task for task in asyncio.all_tasks()
                                    if task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is target["owner"]]
                        assert request_engine.pool.checkedout() == 2
                        stream = target["stream"]
                        assert all(task.done() for task in stream["pumps"] + stream["wait_closed"])
                        assert all(writer.is_closing() for writer in stream["writers"])
                        assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_generation["pid"]
                        assert await foreign.scalar(text("SELECT 1")) == 1
                        await foreign.commit()
                        assert await primer.scalar(text("SELECT pg_backend_pid()")) == primer_pid
                        assert await primer.scalar(text("SELECT 1")) == 1
                        await primer.commit()
                        assert gate.is_set() and (stream["eof_gate"].is_set() is not fault)
                        new_target = generations[-1]
                        assert new_target["entry"] is target["entry"] and new_target["driver"] is not target["driver"]
                        assert not new_target["entry"].in_use and not new_target["driver"].is_closed()
                        assert not new_target["driver"].is_in_transaction()
                        new_pid = new_target["driver"].get_server_pid()
                        row = (await observer_db.execute(text(
                            "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                        ), {"pid": new_pid})).one()
                        assert row.state == "idle" and row.xact_start is None
                        assert await observer_db.scalar(text("SELECT count(*) FROM pg_locks WHERE pid=:pid"),
                                                        {"pid": new_pid}) == 0
                        assert [(r[0], *r[3:]) for r in returns if r[1] is new_target["dbapi"]] == [
                            ("reset", True, False, False), ("checkin",),
                            ("reset", True, False, False), ("checkin",),
                            ("reset", True, False, False), ("checkin",),
                        ]
                        assert "x-graf-auth-expires-at" in response.headers
                        assert await observer_db.scalar(select(AuthSession.expires_at).where(
                            AuthSession.id == session_id)) > datetime.now(UTC) + timedelta(days=29)
                        assert await observer_db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
                        await observer_db.rollback()
                        assert not watchdog_fired and monotonic() - began < 2
                assert set(asyncio.all_tasks()) - relay_tasks <= before
                target["stream"]["eof_gate"].set()
                async with request_engine.connect() as db:
                    assert await db.scalar(text("SELECT 1")) == 1
                    assert await db.scalar(text("SELECT pg_backend_pid()")) != target["pid"]
                    await db.commit()
            finally:
                close_armed = False
                event.remove(request_engine.sync_engine, "close", closing)
                event.remove(Session, "after_transaction_create", created)
                if watchdog is not None:
                    watchdog.cancel()
                gate.set()
                for stream in streams:
                    stream["eof_gate"].set()
                own_tasks = {task for task in (post, observer) if task is not None}
                own_tasks.update(task for task in asyncio.all_tasks() if task is not asyncio.current_task()
                                 and any(task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is owner
                                         for owner, _, _ in request_roots))
                for task in own_tasks:
                    if not task.done():
                        task.cancel()
                if own_tasks:
                    _, pending = await asyncio.wait(own_tasks, timeout=2)
                    assert not pending, "separate cleanup timeout: own request/observer tasks"

                async def close_handles():
                    for db in (primer, observer_db, *held):
                        if db is not None:
                            await db.close()
                    await request_engine.dispose()

                cleanup = asyncio.create_task(close_handles(), context=Context())
                _, pending = await asyncio.wait({cleanup}, timeout=2)
                if pending:
                    cleanup.cancel()
                    pytest.fail("separate cleanup timeout: own handles/dispose")
                cleanup.result()
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


@pytest.mark.parametrize("phase", ["auth", "renewal"])
@pytest.mark.parametrize("fault", [False, True])
def test_cold_dialect_initialization_is_bounded_after_native_connect(
    postgres_seeded_database_url, phase, fault,
):
    async def scenario(engine):
        async with _postgres_response_gate(postgres_seeded_database_url) as (url, gate, relay_tasks):
            request_engine = create_async_engine(url, pool_size=1, max_overflow=0, pool_pre_ping=True)
            request_sessions = async_sessionmaker(request_engine, expire_on_commit=False)
            target, stages, checkouts, observations = {}, [], [], []
            entered = asyncio.Event()
            original_initialize = request_engine.sync_engine.dialect.initialize

            async def use_cold_engine():
                app.state.db_sessionmaker = request_sessions

            app, sessions, session_id = await _setup(engine, before_response=use_cold_engine)
            if phase == "auth":
                app.state.db_sessionmaker = request_sessions

            def connected(dbapi, entry):
                if target:
                    return
                owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                task = asyncio.current_task()
                driver = entry.driver_connection
                assert owner is not None and task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is owner
                assert entry.dbapi_connection is dbapi and dbapi.driver_connection is driver
                assert not driver.is_closed() and not entry.in_use and not checkouts
                assert len(owner.transactions) == 1
                root = next(iter(owner.transactions.values()))
                assert root[0] is owner and root[2] is task
                target.update(dbapi=dbapi, entry=entry, driver=driver, pid=driver.get_server_pid(),
                              owner=owner, task=task, root=root, session=root[1].session)
                stages.append((driver, "connected"))
                if fault:
                    gate.clear()

            def initialize(connection):
                driver = connection.connection.driver_connection
                if driver is target["driver"]:
                    assert connection.connection.dbapi_connection is target["dbapi"]
                    assert target["entry"].dbapi_connection is target["dbapi"]
                    assert asyncio.current_task() is target["task"]
                    assert guard_module._RESULT_VIEW_TASK_OWNER.get() is target["owner"]
                    lease = target["owner"][target["entry"]]
                    assert lease == [target["owner"], target["dbapi"], driver, target["task"], target["entry"]]
                    assert target["entry"].info[guard_module._RESULT_VIEW_CONNECTION_OWNER] is lease
                    assert target["entry"].info[guard_module._RESULT_VIEW_INITIALIZATION_OWNER] is lease
                    assert not checkouts
                stages.append((driver, "entered"))
                entered.set()
                try:
                    result = original_initialize(connection)
                    stages.append((driver, "returned"))
                    return result
                finally:
                    stages.append((driver, "exited"))

            event.listen(request_engine.sync_engine, "connect", connected, insert=True)
            request_engine.sync_engine.dialect.initialize = initialize
            event.listen(request_engine.sync_engine, "connect", lambda dbapi, entry: stages.append(
                (entry.driver_connection, "completed")))
            event.listen(request_engine.sync_engine, "checkout", lambda dbapi, entry, proxy: checkouts.append(
                entry.driver_connection))

            async def observe_initialization():
                async with asyncio.timeout(1):
                    await entered.wait()
                    async with engine.connect() as observer:
                        while True:
                            row = (await observer.execute(text(
                                "SELECT state, xact_start FROM pg_stat_activity WHERE pid=:pid"
                            ), {"pid": target["pid"]})).first()
                            if row is not None and row.xact_start is not None:
                                assert row.state in {"active", "idle in transaction"}
                                observations.append((row.state, True))
                                return
                            await asyncio.sleep(0.01)

            observer_task = None
            watchdog = None
            try:
                async with engine.connect() as foreign:
                    foreign_pid = await foreign.scalar(text("SELECT pg_backend_pid()"))
                    before = set(asyncio.all_tasks())
                    if fault:
                        observer_task = asyncio.create_task(observe_initialization(), context=Context())
                    watchdog = asyncio.get_running_loop().call_later(3, gate.set)
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="https://test") as client:
                        began = monotonic()
                        try:
                            response = await client.post(
                                f"/meetings/{MEETING_ID}/result-viewed", json={"proof": "synthetic"},
                                headers=_headers(session_id),
                            )
                        except AssertionError as error:
                            assert target and (target["driver"], "entered") in stages
                            if observer_task is not None:
                                await observer_task
                                assert observations
                            error.add_note("native DBAPI connect and dialect.initialize entry confirmed before response failure")
                            raise
                        assert monotonic() - began < 2
                    if observer_task is not None:
                        await observer_task
                        assert observations
                    assert response.status_code == 200
                    assert response.json() == {"status": "unavailable" if fault else "accepted"}
                    assert response.headers["cache-control"] == "private, no-store"
                    assert request_engine.pool.checkedout() == 0
                    assert not target["owner"] and not target["owner"].transactions
                    assert guard_module._RESULT_VIEW_INITIALIZATION_OWNER not in target["entry"].info
                    assert guard_module._RESULT_VIEW_CONNECTION_OWNER not in target["entry"].info
                    assert not target["session"].in_transaction()
                    assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in target["session"].info
                    assert not [task for task in asyncio.all_tasks()
                                if task.get_context().get(guard_module._RESULT_VIEW_TASK_OWNER) is target["owner"]]
                    initial_stages = [stage for driver, stage in stages if driver is target["driver"]]
                    if fault:
                        assert initial_stages == ["connected", "entered", "exited"]
                        assert not checkouts and target["driver"].is_closed()
                        async with engine.connect() as observer:
                            assert await observer.scalar(text(
                                "SELECT count(*) FROM pg_stat_activity WHERE pid=:pid"
                            ), {"pid": target["pid"]}) == 0
                            assert await observer.scalar(text(
                                "SELECT count(*) FROM pg_locks WHERE pid=:pid"
                            ), {"pid": target["pid"]}) == 0
                        assert not relay_tasks
                    else:
                        assert initial_stages == ["connected", "entered", "returned", "exited", "completed"]
                        assert checkouts and all(driver is target["driver"] for driver in checkouts)
                        assert "x-graf-auth-expires-at" in response.headers
                        async with sessions() as db:
                            expiry = await db.scalar(select(AuthSession.expires_at).where(AuthSession.id == session_id))
                            assert expiry > datetime.now(UTC) + timedelta(days=29)
                    assert set(asyncio.all_tasks()) - relay_tasks <= before
                    assert await foreign.scalar(text("SELECT pg_backend_pid()")) == foreign_pid
                    assert await foreign.scalar(text("SELECT 1")) == 1
                    async with sessions() as db:
                        assert await db.scalar(select(func.count()).select_from(ProductActivationMilestone)) == 0
                    gate.set()
                    async with request_engine.connect() as db:
                        assert await db.scalar(text("SELECT 1")) == 1
                        if fault:
                            assert db.sync_connection.connection.driver_connection is not target["driver"]
                            assert await db.scalar(text("SELECT pg_backend_pid()")) != target["pid"]
                    assert request_engine.pool.checkedout() == 0
            finally:
                if watchdog is not None:
                    watchdog.cancel()
                # Teardown unblocks RED only; it never supplies successful cleanup evidence.
                gate.set()
                if observer_task is not None:
                    observer_task.cancel()
                    await asyncio.gather(observer_task, return_exceptions=True)
                if target and not target["driver"].is_closed():
                    target["driver"].terminate()
                request_engine.sync_engine.dialect.initialize = original_initialize
                await request_engine.dispose()
    _run(postgres_seeded_database_url, scenario, pool_size=2)


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
