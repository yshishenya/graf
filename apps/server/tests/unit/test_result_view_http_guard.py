"""The outer ASGI boundary, not proof of a rendered result or T113 readiness."""

import asyncio
import json
from contextlib import asynccontextmanager
from contextvars import Context
from time import monotonic
from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, SessionTransactionOrigin, mapped_column
from sqlalchemy.pool import QueuePool

from twobrain_rec_server.api import product_analytics_guard as guard_module
from twobrain_rec_server.api.product_analytics_guard import ProductAnalyticsIngressGuard
from twobrain_rec_server.auth import session_renewal

PATHS = [
    "/meetings/70000000-0000-0000-0000-000000000001/result-viewed",
    "/desktop/meetings/70000000-0000-0000-0000-000000000001/result-viewed",
]


@pytest.mark.parametrize("outcome", ["success", "error", "cancel"])
def test_unbound_root_public_lifecycle_tracks_real_provisioning_and_cleans_every_exit(outcome):
    async def scenario():
        class Base(DeclarativeBase):
            pass

        class Row(Base):
            __tablename__ = "synthetic_root"
            id: Mapped[int] = mapped_column(primary_key=True)

        engine = create_engine("sqlite://")
        owner, observations = guard_module._ResultViewOwner(), []
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        db = Session(engine)

        def snapshot(stage, root):
            lease = owner.transactions[root]
            witness = owner.unbound_roots.get(root)
            observations.append((stage, root.is_active, db.is_active,
                                 db.get_transaction() is root, db.in_transaction(),
                                 root.parent is None, not db.in_nested_transaction(),
                                 witness is not None and witness[0] is lease,
                                 witness is not None and witness[1] is asyncio.current_task()))
            assert len(lease) == 3

        event.listen(db, "after_transaction_create", lambda session, root: snapshot("create", root))
        event.listen(engine, "do_connect", lambda *args: snapshot("connect", db.get_transaction()))
        event.listen(db, "after_begin", lambda session, root, connection: snapshot("begin", root))
        try:
            db.add(Row(id=1))
            root = db.get_transaction()
            assert root.origin is SessionTransactionOrigin.AUTOBEGIN
            assert db.scalar(text("SELECT 1")) == 1
            snapshot("returned", root)
            assert observations == [
                ("create", True, True, True, True, True, True, True, True),
                ("connect", False, False, True, True, True, True, True, True),
                ("begin", False, False, True, True, True, True, False, False),
                ("returned", True, True, True, True, True, True, False, False),
            ]
            if outcome == "error":
                raise RuntimeError("synthetic")
            if outcome == "cancel":
                asyncio.current_task().cancel()
                await asyncio.sleep(0)
        except (RuntimeError, asyncio.CancelledError):
            pass
        finally:
            db.close()
            assert not owner and not owner.transactions and not owner.unbound_roots
            assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in db.info
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
            engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["nested", "foreign_context_nested", "commit", "rollback", "partial_rollback"])
def test_real_session_events_revoke_unbound_root_without_rearming_it(phase):
    async def scenario():
        class Base(DeclarativeBase):
            pass

        class Row(Base):
            __tablename__ = "synthetic_root"
            id: Mapped[int] = mapped_column(primary_key=True)

        engine = create_engine("sqlite://")
        Base.metadata.create_all(engine)
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        try:
            with Session(engine, autoflush=False) as db:
                db.add(Row(id=1))
                root = db.get_transaction()
                lease = owner.transactions[root]
                assert owner.unbound_roots[root] == (lease, asyncio.current_task())
                revoked = []

                def observe(session, *args):
                    revoked.append(root not in owner.unbound_roots)

                name = ("after_transaction_create" if "nested" in phase or phase == "partial_rollback" else
                        "before_commit" if phase == "commit" else "after_rollback")
                event.listen(db, name, observe)
                if "nested" in phase:
                    async def nested():
                        with db.begin_nested():
                            pass
                    if phase.startswith("foreign"):
                        await asyncio.create_task(nested(), context=Context())
                    else:
                        await nested()
                elif phase == "commit":
                    db.commit()
                elif phase == "rollback":
                    db.rollback()
                else:
                    db.add(Row(id=1))
                    with pytest.raises(IntegrityError):
                        db.flush()
                    assert not db.is_active and not root.is_active and db.get_transaction() is root
                assert revoked and all(revoked) and root not in owner.unbound_roots
                if db.get_transaction() is root:
                    assert owner.transactions[root] is lease
                    assert root not in owner.unbound_roots
                db.rollback()
                event.remove(db, name, observe)
                db.add(Row(id=2))
                replacement = db.get_transaction()
                assert replacement is not root and owner.unbound_roots[replacement][0] is owner.transactions[replacement]
                assert len(owner.transactions[replacement]) == 3
            assert not owner and not owner.transactions and not owner.unbound_roots
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
            engine.dispose()
    asyncio.run(scenario())


def test_real_begin_in_another_context_revokes_history_before_binding_can_return_early():
    async def scenario():
        class Base(DeclarativeBase):
            pass

        class Row(Base):
            __tablename__ = "synthetic_root"
            id: Mapped[int] = mapped_column(primary_key=True)

        engine, owner = create_engine("sqlite://"), guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        try:
            with Session(engine, autoflush=False) as db:
                db.add(Row(id=1))
                root = db.get_transaction()
                lease = owner.transactions[root]
                assert owner.unbound_roots[root][0] is lease

                async def query():
                    assert guard_module._RESULT_VIEW_TASK_OWNER.get() is None
                    assert db.scalar(text("SELECT 1")) == 1

                await asyncio.create_task(query(), context=Context())
                assert owner.transactions[root] is lease and not owner.unbound_roots
                assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in db.connection().info
                # A late active snapshot or replayed callback cannot rearm this root.
                assert root.is_active and db.is_active
                guard_module._track_result_transaction(db, root)
                assert not owner.unbound_roots and owner.transactions[root] is lease
            assert not owner and not owner.transactions and not owner.unbound_roots
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
            engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "owned", "no_owner", "failed", "connection_held", "two_roots", "no_task", "wrong_task",
    "wrong_context", "cancelling", "stale_lease", "foreign_owner", "lease_root", "session_info",
    "missing_witness", "stale_witness", "witness_task", "current_root", "other_session", "parent",
    "short_lease", "tuple_lease", "nonsequence_lease", "short_witness", "list_witness", "nonsequence_witness",
    "nested", "explicit_begin", "not_in_transaction", "nested_session", "active_root", "active_session",
    "in_use", "callback_dbapi", "entry_dbapi", "entry_driver", "wrapper_driver", "driver_type",
    "connection_key", "initialization_key", "root_key", "closed", "native_transaction",
])
def test_idle_pool_close_requires_exact_unbound_history_and_native_generation(case, monkeypatch):
    async def scenario():
        checks = []

        class Driver:
            calls = 0

            def is_closed(self):
                checks.append("closed")
                return case == "closed"

            def is_in_transaction(self):
                checks.append("transaction")
                return case == "native_transaction"

            def terminate(self):
                self.calls += 1

        class Root:
            parent, nested, origin = None, False, SessionTransactionOrigin.AUTOBEGIN
            is_active = case == "active_root"

        class Entry:
            pass

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        task = asyncio.current_task()
        owner, root, entry, driver = guard_module._ResultViewOwner(), Root(), Entry(), Driver()
        session = SimpleNamespace(info={}, get_transaction=lambda: root, in_transaction=lambda: True,
                                  in_nested_transaction=lambda: False, is_active=case == "active_session")
        root.session = session
        lease = [owner, root, task]
        owner.transactions[root] = lease
        owner.unbound_roots[root] = (lease, task)
        session.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = lease
        wrapper = SimpleNamespace(driver_connection=driver)
        entry.info, entry.dbapi_connection, entry.driver_connection, entry.in_use = {}, wrapper, driver, False
        callback_dbapi = wrapper
        if case == "failed":
            owner.failed = True
        if case == "connection_held":
            owner[object()] = object()
        if case == "two_roots":
            owner.transactions[object()] = object()
        if case == "wrong_task":
            lease[2] = object()
        if case == "stale_lease":
            owner.transactions[root] = lease.copy()
        for name, value in [("short_lease", lease[:1]), ("tuple_lease", tuple(lease)),
                            ("nonsequence_lease", object())]:
            if case == name:
                owner.transactions[root] = value
        for name, value in [("short_witness", (lease,)), ("list_witness", [lease, task]),
                            ("nonsequence_witness", object())]:
            if case == name:
                owner.unbound_roots[root] = value
        if case == "foreign_owner":
            lease[0] = guard_module._ResultViewOwner()
        if case == "lease_root":
            lease[1] = object()
        if case == "session_info":
            session.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = lease.copy()
        if case == "missing_witness":
            owner.unbound_roots.clear()
        if case == "stale_witness":
            owner.unbound_roots[root] = (lease.copy(), task)
        if case == "witness_task":
            owner.unbound_roots[root] = (lease, object())
        if case == "current_root":
            session.get_transaction = object
        if case == "other_session":
            session.get_transaction = lambda: None
        if case == "parent":
            root.parent = object()
        if case == "nested":
            root.nested = True
        if case == "explicit_begin":
            root.origin = SessionTransactionOrigin.BEGIN
        if case == "not_in_transaction":
            session.in_transaction = lambda: False
        if case == "nested_session":
            session.in_nested_transaction = lambda: True
        if case == "in_use":
            entry.in_use = True
        if case == "callback_dbapi":
            callback_dbapi = object()
        if case == "entry_dbapi":
            entry.dbapi_connection = object()
        if case == "entry_driver":
            entry.driver_connection = object()
        if case == "wrapper_driver":
            wrapper.driver_connection = object()
        if case == "driver_type":
            monkeypatch.setattr(guard_module, "AsyncpgConnection", type("Unsupported", (), {}))
        for name, key in [("connection_key", guard_module._RESULT_VIEW_CONNECTION_OWNER),
                          ("initialization_key", guard_module._RESULT_VIEW_INITIALIZATION_OWNER),
                          ("root_key", guard_module._RESULT_VIEW_TRANSACTION_OWNER)]:
            if case == name:
                entry.info[key] = object()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "no_owner" else owner)
        before = (owner.copy(), owner.transactions.copy(), owner.unbound_roots.copy(), entry.info.copy(), owner.failed)
        try:
            with monkeypatch.context() as patch:
                if case == "no_task":
                    patch.setattr(guard_module.asyncio, "current_task", lambda: None)
                if case in {"wrong_context", "cancelling"}:
                    other = SimpleNamespace(get_context=lambda: Context() if case == "wrong_context" else task.get_context(),
                                            cancelling=lambda: int(case == "cancelling"))
                    lease[2] = other
                    owner.unbound_roots[root] = (lease, other)
                    patch.setattr(guard_module.asyncio, "current_task", lambda: other)
                    before = (owner.copy(), owner.transactions.copy(), owner.unbound_roots.copy(), entry.info.copy(), owner.failed)
                QueuePool(lambda: None).dispatch.close(callback_dbapi, entry)
            assert driver.calls == (1 if case == "owned" else 0)
            assert (owner, owner.transactions, owner.unbound_roots, entry.info, owner.failed) == before
            assert checks == (["closed"] if case == "closed" else ["closed", "transaction"]
                              if case in {"owned", "native_transaction"} else [])
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("case", ["short_lease", "tuple_lease", "nonsequence_lease", "foreign_owner",
                                  "wrong_root", "short_witness", "list_witness", "nonsequence_witness"])
def test_public_revocation_rejects_malformed_history_without_touching_saved_state(case):
    async def scenario():
        owner, db = guard_module._ResultViewOwner(), Session()

        class Root:
            session = db

        root = Root()
        task = asyncio.current_task()
        lease = [owner, root, task]
        owner.transactions[root] = lease
        owner.unbound_roots[root] = (lease, task)
        db.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = lease
        for name, value in [("short_lease", lease[:1]), ("tuple_lease", tuple(lease)),
                            ("nonsequence_lease", object())]:
            if case == name:
                db.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = value
        if case == "foreign_owner":
            lease[0] = object()
        if case == "wrong_root":
            lease[1] = object()
        for name, value in [("short_witness", (lease,)), ("list_witness", [lease, task]),
                            ("nonsequence_witness", object())]:
            if case == name:
                owner.unbound_roots[root] = value
        before = (owner.transactions.copy(), owner.unbound_roots.copy(), db.info.copy())
        db.dispatch.before_commit(db)
        assert (owner.transactions, owner.unbound_roots, db.info) == before
        db.close()
    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "precheckout", "checkout", "no_owner", "not_cancelling", "not_in_use",
    "other_dbapi", "other_driver", "foreign_lease", "stale_lease", "wrong_lease_driver", "not_cancelled_error",
])
def test_cancelled_precheckout_terminates_only_its_exact_current_driver(case, monkeypatch):
    async def scenario():
        class Entry:
            pass

        class Driver:
            calls = 0

            def terminate(self):
                self.calls += 1

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        owner = {}
        driver = Driver()
        wrapper = SimpleNamespace(driver_connection=driver)
        entry = Entry()
        entry.info = {}
        entry.dbapi_connection = wrapper
        entry.driver_connection = driver
        entry.in_use = case != "not_in_use"
        if case in {"checkout", "foreign_lease", "stale_lease", "wrong_lease_driver"}:
            lease = ({} if case == "foreign_lease" else owner, wrapper,
                     object() if case == "wrong_lease_driver" else driver, None)
            entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] = lease
            if case != "stale_lease":
                owner[entry] = lease
        if case == "other_dbapi":
            entry.dbapi_connection = object()
        if case == "other_driver":
            entry.driver_connection = object()

        async def operation():
            token = guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "no_owner" else owner)
            try:
                if case == "not_cancelling":
                    guard_module._terminate_cancelled_result_connection(wrapper, entry, asyncio.CancelledError())
                    return
                try:
                    await asyncio.Event().wait()
                except asyncio.CancelledError as error:
                    guard_module._terminate_cancelled_result_connection(
                        wrapper, entry, RuntimeError("synthetic") if case == "not_cancelled_error" else error,
                    )
            finally:
                guard_module._RESULT_VIEW_TASK_OWNER.reset(token)

        task = asyncio.create_task(operation())
        await asyncio.sleep(0)
        if case != "not_cancelling":
            task.cancel()
        await task
        assert driver.calls == (1 if case in {"precheckout", "checkout"} else 0)
    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "owned", "no_owner", "no_task", "task_context", "wrong_task", "not_in_use",
    "callback_dbapi", "entry_dbapi", "entry_driver", "wrapper_driver", "driver_type",
    "missing_lease", "missing_registry", "stale_registry", "foreign_owner", "lease_dbapi",
    "lease_driver", "lease_entry", "initialization", "root", "active_transaction", "closed",
    "other_reason", "cancelled_reason",
])
def test_hard_invalidation_aborts_only_an_exact_open_idle_owned_generation(case, monkeypatch):
    async def scenario():
        class Driver:
            calls = 0

            def is_closed(self):
                checks.append("closed")
                return case == "closed"

            def is_in_transaction(self):
                assert case != "closed", "must not read a released native protocol"
                checks.append("transaction")
                return case == "active_transaction"

            def terminate(self):
                self.calls += 1

        class Entry:
            pass

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        owner, foreign, entry, driver, checks = (guard_module._ResultViewOwner(),
                                               guard_module._ResultViewOwner(), Entry(), Driver(), [])
        wrapper = SimpleNamespace(driver_connection=driver)
        task = asyncio.current_task()
        lease = [owner, wrapper, driver, task, entry]
        owner[entry] = lease
        entry.info = {guard_module._RESULT_VIEW_CONNECTION_OWNER: lease}
        entry.dbapi_connection, entry.driver_connection, entry.in_use = wrapper, driver, case != "not_in_use"
        callback_dbapi = wrapper
        if case == "callback_dbapi":
            callback_dbapi = object()
        if case == "entry_dbapi":
            entry.dbapi_connection = object()
        if case == "entry_driver":
            entry.driver_connection = object()
        if case == "wrapper_driver":
            wrapper.driver_connection = object()
        if case == "driver_type":
            monkeypatch.setattr(guard_module, "AsyncpgConnection", type("Unsupported", (), {}))
        if case == "missing_lease":
            entry.info.clear()
        if case == "missing_registry":
            owner.clear()
        if case == "stale_registry":
            owner[entry] = lease.copy()
        for name, index in [("foreign_owner", 0), ("lease_dbapi", 1), ("lease_driver", 2), ("lease_entry", 4)]:
            if case == name:
                lease[index] = foreign if index == 0 else object()
        if case == "wrong_task":
            lease[3] = object()
        if case == "initialization":
            entry.info[guard_module._RESULT_VIEW_INITIALIZATION_OWNER] = lease
        if case == "root":
            entry.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = object()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "no_owner" else owner)
        before_info, before_registry = entry.info.copy(), owner.copy()
        try:
            with monkeypatch.context() as patch:
                if case == "no_task":
                    patch.setattr(guard_module.asyncio, "current_task", lambda: None)
                if case == "task_context":
                    other = SimpleNamespace(get_context=lambda: Context())
                    lease[3] = other
                    patch.setattr(guard_module.asyncio, "current_task", lambda: other)
                reason = (RuntimeError("synthetic") if case == "other_reason" else
                          asyncio.CancelledError() if case == "cancelled_reason" else None)
                guard_module._terminate_cancelled_result_connection(callback_dbapi, entry, reason)
            assert driver.calls == (1 if case in {"owned", "cancelled_reason"} else 0)
            assert entry.info == before_info and owner == before_registry and not foreign.failed
            assert owner.failed is (case not in {
                "owned", "no_owner", "active_transaction", "closed", "other_reason", "cancelled_reason",
            })
            assert checks == (["closed", "transaction"] if case in {"owned", "active_transaction"} else
                              ["closed"] if case == "closed" else [])
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("case", ["owned", "nested", "foreign", "close_in_another_context"])
def test_session_root_owner_is_known_before_checkout_and_removed_at_its_exact_end(case):
    async def scenario():
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "foreign" else owner)
        try:
            with Session() as db:
                transaction = db.begin()
                assert len(owner.transactions) == (0 if case == "foreign" else 1)
                if case != "foreign":
                    assert owner.transactions[transaction][2] is asyncio.current_task()
                    assert not owner.unbound_roots  # Explicit BEGIN is never a mint event.
                    if case == "nested":
                        with db.begin_nested():
                            assert list(owner.transactions) == [transaction]
                        assert list(owner.transactions) == [transaction]
                if case == "close_in_another_context":
                    async def close():
                        db.close()
                    await asyncio.create_task(close(), context=Context())
                else:
                    transaction.rollback()
                assert not owner.transactions and guard_module._RESULT_VIEW_TRANSACTION_OWNER not in db.info
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "owned", "raw", "repeat", "no_owner", "closed", "invalidated", "foreign_lease",
    "stale_entry", "other_dbapi", "other_entry_dbapi", "other_driver", "other_entry_driver",
    "not_in_use", "foreign_entry_lease", "foreign_root", "missing_root", "stale_root", "wrong_bound_lease",
])
def test_operation_handoff_requires_the_exact_connection_and_root_generation(case):
    async def scenario():
        owner = guard_module._ResultViewOwner()
        old_task, dbapi, driver, transaction = object(), object(), object(), object()

        class Entry:
            pass

        class Connection:
            closed = case == "closed"
            invalidated = case == "invalidated"

            @property
            def connection(self):
                assert not self.closed and not self.invalidated, "must not reconnect"
                return proxy

            @property
            def info(self):
                assert not self.closed and not self.invalidated, "must not revalidate"
                return entry.info

        entry = Entry()
        lease = [owner, dbapi, driver, old_task, entry]
        root = [owner, transaction, old_task]
        entry.info = {guard_module._RESULT_VIEW_CONNECTION_OWNER: lease}
        entry.dbapi_connection, entry.driver_connection, entry.in_use = dbapi, driver, True
        proxy = SimpleNamespace(dbapi_connection=dbapi, driver_connection=driver)
        owner[entry], owner.transactions[transaction] = lease, root
        if case != "raw":
            entry.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = (root, lease)
        if case == "foreign_lease":
            lease[0] = guard_module._ResultViewOwner()
        if case == "stale_entry":
            owner[entry] = lease.copy()
        if case == "other_dbapi":
            proxy.dbapi_connection = object()
        if case == "other_entry_dbapi":
            entry.dbapi_connection = object()
        if case == "other_driver":
            proxy.driver_connection = object()
        if case == "other_entry_driver":
            entry.driver_connection = object()
        if case == "not_in_use":
            entry.in_use = False
        if case == "foreign_entry_lease":
            entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] = lease.copy()
        if case == "foreign_root":
            root[0] = guard_module._ResultViewOwner()
        if case == "missing_root":
            owner.transactions.clear()
        if case == "stale_root":
            owner.transactions[transaction] = root.copy()
        if case == "wrong_bound_lease":
            entry.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = (root, lease.copy())
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "no_owner" else owner)
        try:
            guard_module._handoff_result_connection(Connection())
            if case == "repeat":
                guard_module._handoff_result_connection(Connection(), object(), "SQL", {}, None, False)
            accepted = case in {"owned", "raw", "repeat"}
            assert lease[3] is (asyncio.current_task() if accepted else old_task)
            assert root[2] is (asyncio.current_task() if accepted and case != "raw" else old_task)
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


def test_global_connection_hooks_leave_synchronous_unowned_sessions_unchanged():
    engine = create_engine("sqlite://")
    try:
        with Session(engine) as db:
            assert db.scalar(text("SELECT 1")) == 1
            assert guard_module._RESULT_VIEW_CONNECTION_OWNER not in db.connection().info
            db.commit()
    finally:
        engine.dispose()


@pytest.mark.parametrize("phase", ["terminate", "cleanup"])
@pytest.mark.parametrize("case", [
    "owned", "no_owner", "no_init", "stale_init", "foreign_key", "stale_registry",
    "foreign_owner", "wrong_entry", "other_dbapi", "other_driver", "wrapper_driver",
    "unsupported_driver", "in_use", "foreign_task_context", "foreign_context", "root_association",
    "not_cancelled", "outside_cancelled_set", "pending", "open",
])
def test_initialization_cancellation_and_cleanup_require_exact_ownership(phase, case, monkeypatch):
    async def scenario():
        class Driver:
            calls = 0
            closed = False

            def terminate(self):
                self.calls += 1

            def is_closed(self):
                return self.closed

        class Entry:
            pass

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        task = asyncio.create_task(asyncio.Event().wait(),
                                   context=Context() if case == "foreign_task_context" else None)
        await asyncio.sleep(0)
        if case != "not_cancelled":
            task.cancel()
        if phase == "cleanup" and case != "pending":
            if not task.cancelling():
                task.cancel()
            await asyncio.gather(task, return_exceptions=True)
        driver = Driver()
        driver.closed = phase == "cleanup" and case != "open"
        wrapper = SimpleNamespace(driver_connection=driver)
        entry = Entry()
        lease = [owner, wrapper, driver, task, entry]
        entry.dbapi_connection, entry.driver_connection, entry.in_use = wrapper, driver, case == "in_use"
        entry.info = {guard_module._RESULT_VIEW_CONNECTION_OWNER: lease,
                      guard_module._RESULT_VIEW_INITIALIZATION_OWNER: lease}
        owner[entry] = lease
        if case == "no_init":
            entry.info.pop(guard_module._RESULT_VIEW_INITIALIZATION_OWNER)
        if case == "stale_init":
            entry.info[guard_module._RESULT_VIEW_INITIALIZATION_OWNER] = lease.copy()
        if case == "foreign_key":
            entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] = lease.copy()
        if case == "stale_registry":
            owner[entry] = lease.copy()
        if case == "foreign_owner":
            lease[0] = guard_module._ResultViewOwner()
        if case == "wrong_entry":
            lease[4] = object()
        if case == "other_dbapi":
            entry.dbapi_connection = object()
        if case == "other_driver":
            entry.driver_connection = object()
        if case == "wrapper_driver":
            wrapper.driver_connection = object()
        if case == "unsupported_driver":
            monkeypatch.setattr(guard_module, "AsyncpgConnection", type("OtherDriver", (), {}))
        if case == "root_association":
            entry.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = object()
        if case in {"no_owner", "foreign_context"}:
            guard_module._RESULT_VIEW_TASK_OWNER.set(None if case == "no_owner" else {})
        before_info, before_registry = entry.info.copy(), owner.copy()
        try:
            if phase == "terminate":
                guard_module._terminate_initializing_result_connections(
                    owner, set() if case == "outside_cancelled_set" else {task},
                )
                allowed = case in {"owned", "pending", "open"}
                assert driver.calls == int(allowed)
                assert entry.info == before_info and owner == before_registry
            else:
                guard_module._forget_finished_result_initializations(owner)
                allowed = case in {"owned", "not_cancelled", "outside_cancelled_set"}
                assert driver.calls == 0
                if allowed:
                    assert not owner and not entry.info
                    guard_module._forget_finished_result_initializations(owner)
                else:
                    assert entry.info == before_info and owner == before_registry
        finally:
            task.cancel()
            await asyncio.gather(task, return_exceptions=True)
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["connect", "checkout", "checkin"])
@pytest.mark.parametrize("case", [
    "owned", "no_owner", "foreign_owner", "stale_init", "foreign_key", "stale_registry",
    "other_dbapi", "other_driver", "wrapper_driver", "root_association", "wrong_task",
])
def test_early_initialization_hooks_preserve_contradictory_metadata(phase, case, monkeypatch):
    async def scenario():
        class Driver:
            pass

        class Entry:
            pass

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        driver = Driver()
        wrapper = SimpleNamespace(driver_connection=driver)
        entry = Entry()
        entry.info = {}
        entry.dbapi_connection, entry.driver_connection, entry.in_use = wrapper, driver, False
        lease = [owner, wrapper, driver, asyncio.current_task(), entry]
        child = asyncio.create_task(asyncio.sleep(0))
        if phase != "connect" or case != "owned":
            entry.info = {guard_module._RESULT_VIEW_CONNECTION_OWNER: lease,
                          guard_module._RESULT_VIEW_INITIALIZATION_OWNER: lease}
            owner[entry] = lease
        if case == "no_owner":
            guard_module._RESULT_VIEW_TASK_OWNER.set(None)
        if case == "foreign_owner":
            lease[0] = {}
        if case == "stale_init":
            entry.info[guard_module._RESULT_VIEW_INITIALIZATION_OWNER] = lease.copy()
        if case == "foreign_key":
            entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] = lease.copy()
        if case == "stale_registry":
            owner[entry] = lease.copy()
        if case == "other_dbapi":
            entry.dbapi_connection = object()
        if case == "other_driver":
            entry.driver_connection = object()
        if case == "wrapper_driver":
            wrapper.driver_connection = object()
        if case == "root_association":
            entry.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = object()
        if case == "wrong_task":
            lease[3] = child
        before_info, before_registry = entry.info.copy(), owner.copy()
        try:
            if phase == "checkin":
                guard_module._untrack_result_connection(wrapper, entry)
            else:
                entry.in_use = phase == "checkout"
                guard_module._track_result_connection(wrapper, entry, object() if entry.in_use else None)
            allowed = case == "owned" or (phase == "checkin" and case == "wrong_task")
            if not allowed:
                assert entry.info == before_info and owner == before_registry
            elif phase == "checkin":
                assert not owner and not entry.info
            else:
                current = owner[entry]
                assert entry.info[guard_module._RESULT_VIEW_CONNECTION_OWNER] is current
                assert current[0] is owner and current[1] is wrapper and current[2] is driver
                assert current[3] is asyncio.current_task() and current[4] is entry
                if phase == "connect":
                    assert entry.info[guard_module._RESULT_VIEW_INITIALIZATION_OWNER] is current
                    entry.in_use = True
                    guard_module._track_result_connection(wrapper, entry, object())
                    assert owner[entry] is not current
                assert guard_module._RESULT_VIEW_INITIALIZATION_OWNER not in entry.info
                guard_module._untrack_result_connection(wrapper, entry)
                assert not owner and not entry.info
        finally:
            await child
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["connect", "checkout", "checkin"])
@pytest.mark.parametrize("has_owner", [False, True])
def test_rejected_initialization_hook_marks_only_current_owner(phase, has_owner, monkeypatch):
    async def scenario():
        class Driver:
            pass

        class Entry:
            pass

        monkeypatch.setattr(guard_module, "AsyncpgConnection", Driver)
        owner, foreign, entry, driver = guard_module._ResultViewOwner(), guard_module._ResultViewOwner(), Entry(), Driver()
        wrapper = SimpleNamespace(driver_connection=driver)
        lease = [foreign, wrapper, driver, asyncio.current_task(), entry]
        foreign[entry] = lease
        entry.info = {guard_module._RESULT_VIEW_INITIALIZATION_OWNER: lease,
                      guard_module._RESULT_VIEW_CONNECTION_OWNER: lease}
        entry.dbapi_connection, entry.driver_connection, entry.in_use = wrapper, driver, phase == "checkout"
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner if has_owner else None)
        before = entry.info.copy()
        try:
            if phase == "checkin":
                guard_module._untrack_result_connection(wrapper, entry)
            else:
                guard_module._track_result_connection(wrapper, entry, object() if phase == "checkout" else None)
            assert getattr(owner, "failed", False) is has_owner
            assert not owner and entry.info == before and foreign[entry] is lease
            assert entry.driver_connection is driver
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


@pytest.mark.parametrize("phase", ["checkout", "checkin"])
@pytest.mark.parametrize("path", PATHS)
def test_contradictory_initialization_with_absent_current_entry_cannot_release_accepted(phase, path):
    async def scenario():
        engine, clean_engine = create_engine("sqlite://"), create_engine("sqlite://")
        entries, owners = [], []
        event.listen(engine, "checkout", lambda dbapi, entry, proxy: entries.append(entry))
        foreign = guard_module._ResultViewOwner()
        try:
            with engine.connect() as db:
                assert db.scalar(text("SELECT 1")) == 1
            with clean_engine.connect() as db:
                assert db.scalar(text("SELECT 1")) == 1
            entry = entries[0]
            driver = entry.driver_connection
            lease = [foreign, entry.dbapi_connection, driver, asyncio.current_task(), entry]
            foreign[entry] = lease
            foreign_info = {guard_module._RESULT_VIEW_INITIALIZATION_OWNER: lease,
                            guard_module._RESULT_VIEW_CONNECTION_OWNER: lease}
            if phase == "checkout":
                entry.info.update(foreign_info)

            async def app(scope, receive, send):
                owner = guard_module._RESULT_VIEW_TASK_OWNER.get()
                owners.append(owner)
                assert entry not in owner and owner is not foreign
                with Session(engine) as db:
                    assert db.scalar(text("SELECT 1")) == 1
                    if phase == "checkin":
                        owner.pop(entry)
                        entry.info.clear()
                        entry.info.update(foreign_info)
                    db.commit()
                assert not owner and not owner.transactions
                with Session(clean_engine) as db:
                    assert db.scalar(text("SELECT 1")) == 1
                    db.commit()
                assert not owner and not owner.transactions
                await send({"type": "http.response.start", "status": 200, "headers": []})
                await send({"type": "http.response.body", "body": b'{"status":"accepted"}'})

            before = set(asyncio.all_tasks())
            start, body, elapsed, _ = await _request(ProductAnalyticsIngressGuard(app), path=path)
            assert start["status"] == 200 and body == b'{"status":"unavailable"}'
            assert elapsed < 2 and set(asyncio.all_tasks()) == before
            assert len(owners) == 1 and owners[0].failed
            assert not owners[0] and not owners[0].transactions and not foreign.failed
            assert entry.info == foreign_info and foreign[entry] is lease
            assert entry.driver_connection is driver
            with engine.connect() as db:
                assert db.scalar(text("SELECT 1")) == 1
                assert db.connection.driver_connection is driver
            assert entry.info == foreign_info and foreign[entry] is lease
        finally:
            engine.dispose()
            clean_engine.dispose()
    asyncio.run(scenario())


def test_root_association_survives_nested_work_and_is_cleared_before_reuse_or_reconnect():
    async def scenario():
        engine = create_engine("sqlite://")
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        try:
            with Session(engine) as db:
                db.execute(text("SELECT 1"))
                connection = db.connection()
                original = connection.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER]
                with db.begin_nested():
                    db.execute(text("SELECT 1"))
                    assert connection.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] is original
                assert connection.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] is original
                db.commit()
                assert not owner and not owner.transactions
                db.execute(text("SELECT 1"))
                replacement = db.connection().info[guard_module._RESULT_VIEW_TRANSACTION_OWNER]
                assert replacement[0] is not original[0] and replacement[1] is not original[1]
            assert not owner and not owner.transactions

            async def foreign():
                with engine.connect() as connection:
                    assert guard_module._RESULT_VIEW_TRANSACTION_OWNER not in connection.info
                    assert guard_module._RESULT_VIEW_CONNECTION_OWNER not in connection.info
                    assert connection.scalar(text("SELECT 1")) == 1

            await asyncio.create_task(foreign(), context=Context())
            with engine.connect() as connection:
                old = connection.connection.driver_connection
                connection.invalidate()
            assert not owner and not owner.transactions
            with Session(engine) as db:
                db.execute(text("SELECT 1"))
                assert db.connection().connection.driver_connection is not old
                association = db.connection().info[guard_module._RESULT_VIEW_TRANSACTION_OWNER]
                assert association[0][0] is owner and association[0][2] is asyncio.current_task()
            assert not owner and not owner.transactions
        finally:
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
            engine.dispose()
    asyncio.run(scenario())


@pytest.mark.parametrize("case", [
    "owned", "pending_task", "connection_held", "foreign_owner", "other_transaction",
    "foreign_session_info", "session_active", "stale_mapping", "foreign_context",
])
def test_cancelled_cleanup_forgets_only_finished_unbound_root_metadata(case):
    async def scenario():
        owner = guard_module._ResultViewOwner()
        token = guard_module._RESULT_VIEW_TASK_OWNER.set(owner)
        task = asyncio.create_task(asyncio.sleep(10 if case == "pending_task" else 0))
        if case != "pending_task":
            await task
        session = SimpleNamespace(info={}, in_transaction=lambda: case == "session_active")
        class Transaction:
            pass
        transaction = Transaction()
        transaction.session = session
        lease = [owner, transaction, task]
        owner.transactions[transaction] = lease
        owner.unbound_roots[transaction] = (lease, task)
        session.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = lease
        if case == "connection_held":
            owner[object()] = object()
        if case == "foreign_owner":
            lease[0] = guard_module._ResultViewOwner()
        if case == "other_transaction":
            lease[1] = object()
        if case == "foreign_session_info":
            session.info[guard_module._RESULT_VIEW_TRANSACTION_OWNER] = object()
        if case == "stale_mapping":
            owner.transactions[transaction] = lease.copy()
        if case == "foreign_context":
            guard_module._RESULT_VIEW_TASK_OWNER.set(guard_module._ResultViewOwner())
        try:
            guard_module._forget_finished_result_transactions(owner)
            assert bool(owner.transactions) is (case != "owned")
            assert bool(owner.unbound_roots) is (case != "owned")
            assert bool(session.info) is (case != "owned")
        finally:
            if not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            guard_module._RESULT_VIEW_TASK_OWNER.reset(token)
    asyncio.run(scenario())


async def _request(app, *, path=PATHS[0], chunks=None, headers=None, method="POST", delay=0):
    chunks = list(chunks if chunks is not None else [b'{"proof":"synthetic"}'])
    output = []
    consumed = 0
    ended = asyncio.Event()

    async def receive():
        nonlocal consumed
        if chunks:
            if delay:
                await asyncio.sleep(delay)
            value = chunks.pop(0)
            consumed += len(value)
            return {"type": "http.request", "body": value, "more_body": bool(chunks)}
        await ended.wait()
        return {"type": "http.disconnect"}

    async def send(message):
        output.append(message.copy())
        if message["type"] == "http.response.body" and not message.get("more_body", False):
            ended.set()

    scope = dict(type="http", asgi={"version": "3.0"}, http_version="1.1", method=method,
                 scheme="https", path=path, raw_path=path.encode(), query_string=b"",
                 headers=headers if headers is not None else [(b"content-type", b"application/json")],
                 client=("127.0.0.1", 1), server=("test", 443), state={})
    began = monotonic()
    await app(scope, receive, send)
    elapsed = monotonic() - began
    start = [m for m in output if m["type"] == "http.response.start"]
    assert len(start) == 1
    body = b"".join(m.get("body", b"") for m in output if m["type"] == "http.response.body")
    return start[0], body, elapsed, consumed


def _accepted(calls):
    async def app(scope, receive, send):
        calls.append(scope)
        body = bytearray()
        while True:
            message = await receive()
            body.extend(message.get("body", b""))
            if not message.get("more_body", False):
                break
        assert json.loads(body)["proof"]
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"status":"accepted"}'})
    return app


@pytest.mark.parametrize("path", PATHS)
def test_valid_json_replays_only_its_bounded_body_and_keeps_private_response(path):
    calls = []
    start, body, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), path=path,
        chunks=[b'{"proof":', b'"synthetic"}'],
    ))
    assert start["status"] == 200 and json.loads(body) == {"status": "accepted"}
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"
    assert len(calls) == 1
    state = calls[0]["state"]
    assert state["result_view_cleanup_deadline"] - state["result_view_deadline"] == 0.5


@pytest.mark.parametrize("body", [
    b"", b"null", b"[]", b"5", b'{"proof":5}', b'{"proof":null}',
    b'{"proof":""}', b'{"proof":"x","owner":"forged"}',
    b'{"proof":"x","proof":"y"}', b'{"proof":"\\u0410"}',
    b'{"proof":"x"} trailing', b'{"proof":NaN}',
    json.dumps({"proof": "x" * 1537}).encode(),
])
def test_ambiguous_or_non_ascii_json_is_rejected_before_downstream(body):
    calls = []
    start, raw, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[body]))
    assert start["status"] == 400
    assert json.loads(raw) == {"status": "unavailable"}
    assert not calls


@pytest.mark.parametrize("media", [b"application/x-www-form-urlencoded", b"multipart/form-data; boundary=x", b"text/plain"])
def test_non_json_never_enters_body_form_or_auth(media):
    calls = []
    start, body, _, consumed = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[b"proof=synthetic"],
        headers=[(b"content-type", media)],
    ))
    assert start["status"] == 415 and json.loads(body) == {"status": "unavailable"}
    assert not calls and consumed == 0


@pytest.mark.parametrize("declared", [None, b"1", b"2049"])
def test_actual_size_limit_cannot_be_bypassed_by_content_length(declared):
    calls = []
    headers = [(b"content-type", b"application/json")]
    if declared is not None:
        headers.append((b"content-length", declared))
    start, body, _, consumed = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), headers=headers,
        chunks=[b'{"proof":"x"}', b" " * 2048],
    ))
    assert start["status"] == 413 and json.loads(body) == {"status": "unavailable"}
    assert consumed == (0 if declared == b"2049" else 2061)
    assert not calls


def test_exact_body_and_proof_limits_are_accepted():
    calls = []
    value = json.dumps({"proof": "x" * 1536}).encode()
    start, _, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), chunks=[value + b" " * (2048 - len(value))],
    ))
    assert start["status"] == 200 and len(calls) == 1


def test_slow_receive_uses_the_outer_deadline_without_a_live_request_tail():
    async def scenario():
        before = set(asyncio.all_tasks())
        calls = []
        start, body, elapsed, _ = await _request(
            ProductAnalyticsIngressGuard(_accepted(calls)), delay=3,
        )
        assert elapsed < 2 and start["status"] == 200
        assert json.loads(body) == {"status": "unavailable"} and not calls
        assert set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("path", PATHS)
def test_outer_deadline_covers_real_post_response_renewal(monkeypatch, path):
    async def scenario():
        calls, exited = [], []

        async def commit():
            calls.append("commit")

        @asynccontextmanager
        async def sessions():
            try:
                yield SimpleNamespace(commit=commit)
            finally:
                await asyncio.sleep(0.05)
                exited.append(True)

        async def apply(*args):
            pass

        async def activity(*args, **kwargs):
            calls.append("renewal")
            await asyncio.sleep(3)

        monkeypatch.setattr(session_renewal, "apply_tenant_context", apply)
        monkeypatch.setattr(session_renewal, "record_session_activity", activity)
        app = FastAPI()
        app.state.db_sessionmaker = sessions
        app.state.settings = SimpleNamespace(auth_session_ttl_seconds=3600)
        app.middleware("http")(session_renewal.session_renewal_middleware)

        @app.post(path)
        async def endpoint(request: Request):
            request.state.auth_session_renewal = ("synthetic", object(), object(), object())
            return JSONResponse({"status": "accepted"})

        before = set(asyncio.all_tasks())
        start, body, elapsed, _ = await _request(ProductAnalyticsIngressGuard(app), path=path)
        assert elapsed < 2
        assert calls == ["renewal"] and exited == [True]
        assert start["status"] == 200 and json.loads(body) == {"status": "unavailable"}
        assert set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


@pytest.mark.parametrize("status", [401, 403, 422])
def test_auth_and_csrf_failures_keep_their_status(status):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": []})
        await send({"type": "http.response.body", "body": b'{"code":"synthetic_auth_refusal"}'})

    start, body, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(app)))
    assert start["status"] == status and json.loads(body)["code"] == "synthetic_auth_refusal"
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"


@pytest.mark.parametrize("failure", ["raise_after_start", "large_body", "many_parts", "incomplete", "two_starts"])
def test_partial_oversized_or_failed_internal_response_cannot_leak_accepted(failure):
    async def app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": []})
        if failure == "raise_after_start":
            raise RuntimeError("synthetic private exception must not be echoed")
        if failure == "two_starts":
            await send({"type": "http.response.start", "status": 200, "headers": []})
        if failure == "many_parts":
            for _ in range(33):
                await send({"type": "http.response.body", "body": b"", "more_body": True})
        await send({"type": "http.response.body", "body": b"x" * 4097 if failure == "large_body" else b"",
                    "more_body": failure == "incomplete"})

    start, body, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(app)))
    assert start["status"] == 200 and json.loads(body) == {"status": "unavailable"}


def test_send_failure_never_starts_a_second_response():
    async def scenario():
        starts = 0

        async def send(message):
            nonlocal starts
            if message["type"] == "http.response.start":
                starts += 1
            raise OSError("synthetic disconnected transport")

        guard = ProductAnalyticsIngressGuard(_accepted([]))

        async def receive():
            return {"type": "http.request", "body": b'{"proof":"x"}', "more_body": False}

        await guard(dict(type="http", method="POST", path=PATHS[0],
                         headers=[(b"content-type", b"application/json")]), receive, send)
        assert starts == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("refusal", ["media", "length", "timeout"])
@pytest.mark.parametrize("blocked_message", ["http.response.start", "http.response.body"])
def test_own_refusal_send_keeps_the_original_hard_deadline(refusal, blocked_message):
    async def scenario():
        calls, messages, cancelled = [], [], []

        async def app(scope, receive, send):
            calls.append(True)
            await asyncio.sleep(10)

        async def receive():
            return {"type": "http.request", "body": b'{"proof":"x"}', "more_body": False}

        async def send(message):
            messages.append(message.copy())
            if message["type"] == blocked_message:
                try:
                    await asyncio.Event().wait()
                finally:
                    cancelled.append(True)

        headers = [(b"content-type", b"text/plain" if refusal == "media" else b"application/json")]
        if refusal == "length":
            headers.append((b"content-length", b"2049"))
        scope = dict(type="http", method="POST", path=PATHS[0], headers=headers)
        before = set(asyncio.all_tasks())
        began = monotonic()
        completed = False
        try:
            # The test watchdog stops the old unbounded send; it is not a request budget.
            await asyncio.wait_for(ProductAnalyticsIngressGuard(app)(scope, receive, send), timeout=2.3)
            completed = True
        except TimeoutError:
            pass
        elapsed = monotonic() - began
        assert completed and elapsed < 2.15
        assert calls == ([True] if refusal == "timeout" else [])
        starts = [m for m in messages if m["type"] == "http.response.start"]
        assert len(starts) == 1 and starts[0]["status"] == {"media": 415, "length": 413, "timeout": 200}[refusal]
        assert cancelled == [True] and set(asyncio.all_tasks()) == before
    asyncio.run(scenario())


def test_disconnect_during_body_returns_without_reply_or_downstream_work():
    async def scenario():
        calls, messages = [], []

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            messages.append(message)

        await ProductAnalyticsIngressGuard(_accepted(calls))(
            dict(type="http", method="POST", path=PATHS[0],
                 headers=[(b"content-type", b"application/json")]), receive, send,
        )
        assert not calls and not messages
    asyncio.run(scenario())


@pytest.mark.parametrize("path,method", [("/unrelated", "POST"), (PATHS[0], "GET"),
                                        (PATHS[0] + "/", "POST")])
def test_other_routes_and_methods_are_passed_through(path, method):
    calls = []
    start, _, _, _ = asyncio.run(_request(ProductAnalyticsIngressGuard(_accepted(calls)), path=path, method=method))
    assert start["status"] == 200 and len(calls) == 1
    assert b"cache-control" not in dict(start["headers"])


@pytest.mark.parametrize("component", ["70000000000000000000000000000001", "{70000000-0000-0000-0000-000000000001}", "not-uuid"])
def test_noncanonical_uuid_or_invalid_component_cannot_bypass_the_route_boundary(component):
    calls = []
    start, _, _, _ = asyncio.run(_request(
        ProductAnalyticsIngressGuard(_accepted(calls)), path=f"/meetings/{component}/result-viewed",
    ))
    assert start["status"] == 200 and len(calls) == 1
    assert dict(start["headers"])[b"cache-control"] == b"private, no-store"
