"""Owned result snapshots and a fixed pair operation; runtime T113 stays closed."""

import asyncio
import math
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from twobrain_rec_server.cabinet.result_projection_budget import (
    ProjectionBudgetExceeded,
    ProjectionReadBudget,
)
from twobrain_rec_server.db.tenant_context import (
    TenantDatabaseContext,
    WorkspaceAuthContext,
    apply_tenant_context,
    tenant_context_settings,
    workspace_auth_context_settings,
)


class _ProjectionSession(Session):
    def get_bind(self, *args, **kwargs):
        bind = super().get_bind(*args, **kwargs)
        self._projection_owner._check_bind(bind)
        return bind

    def connection(self, bind_arguments=None, execution_options=None):
        if bind_arguments and bind_arguments.get("bind") is not None:
            self._projection_owner._check_bind(bind_arguments["bind"])
        return super().connection(bind_arguments=bind_arguments, execution_options=execution_options)


class ResultProjectionSession:
    def __init__(self, db, deadline):
        self.db = db
        self._engine = db.bind.sync_engine
        db.sync_session._projection_owner = self
        self.deadline = deadline
        self.budget = ProjectionReadBudget()
        self.sql_count = 0
        self.failed = False
        self._task = asyncio.current_task()
        self._connection = None
        self._async_connection = None
        self._driver = None
        self._expected = None
        self._cursor_pending = False
        self._control = None
        self._numeric = False
        self._reading = False
        self._statement_ms = 500
        self._listeners = []

    def _refuse(self):
        self.failed = self.budget.failed = True
        raise ProjectionBudgetExceeded

    def _check_bind(self, bind):
        self.checkpoint()
        if bind is not self._engine:
            self._refuse()

    def checkpoint(self):
        if (self.failed or (self.budget.failed and not self._numeric)
                or asyncio.current_task() is not self._task
                or asyncio.get_running_loop().time() >= self.deadline
                or self.db.new or self.db.dirty or self.db.deleted):
            self._refuse()

    def _listen(self, target, name, callback):
        event.listen(target, name, callback)
        self._listeners.append((target, name, callback))

    def detach(self):
        for target, name, callback in reversed(self._listeners):
            event.remove(target, name, callback)
        self._listeners.clear()
        self.failed = True

    @contextmanager
    def _permit(self, statement):
        self.checkpoint()
        if self._expected is not None:
            self._refuse()
        self._expected = statement
        before = self.sql_count
        try:
            yield
            if self.sql_count != before + 1 or self._cursor_pending:
                self._refuse()
        except BaseException:
            self.failed = self.budget.failed = True
            raise
        finally:
            self._expected = None
            self._cursor_pending = False

    def _before_execute(self, connection, statement, multiparams, params, options):
        self.checkpoint()
        if (connection is not self._connection or statement is not self._expected
                or self._cursor_pending or multiparams):
            self._refuse()
        self._cursor_pending = True

    def _before_cursor(self, connection, cursor, sql, params, context, many):
        self.checkpoint()
        if (connection is not self._connection or not self._cursor_pending
                or context.compiled is None or many or self.sql_count >= 128):
            self._refuse()
        self._cursor_pending = False
        self.sql_count += 1

    def _transaction_ended(self, *args):
        # A reader cannot end the snapshot and continue in a new transaction.
        self.failed = self.budget.failed = True

    def _after_begin(self, session, transaction, connection):
        self.checkpoint()
        if connection is not self._connection:
            self._refuse()

    def _forbid_write(self, *args):
        self._refuse()

    def _before_commit(self, *args):
        self._refuse()

    def _commit_event(self, *args):
        self._refuse()

    def finish(self):
        self.checkpoint()

    def _limit_statement(self):
        self.checkpoint()
        milliseconds = min(500, int((self.deadline - asyncio.get_running_loop().time()) * 1000))
        if milliseconds < 1:
            self._refuse()
        if milliseconds < self._statement_ms:
            statement = text(f"SET LOCAL statement_timeout = '{milliseconds}ms'")
            with self._permit(statement):
                self._connection.execute(statement)
            self._statement_ms = milliseconds

    def execute(self, statement, parameters):
        """The numeric helper's connection interface, unavailable to the reader."""
        if not self._numeric or not isinstance(statement, Select):
            self._refuse()
        self._limit_statement()
        with self._permit(statement):
            result = self._connection.execute(statement, parameters)
        self.checkpoint()
        return result

    def _read(self, state):
        self.checkpoint()
        if state.bind_arguments.get("bind") is not None:
            self._refuse()
        if self._control is not None:
            expected, self._control = self._control, None
            if state.parameters or not expected.compare(state.statement):
                self._refuse()
        else:
            if (self._reading or not state.is_select or state.is_relationship_load
                    or state.execution_options.get("stream_results")
                    or state.execution_options.get("yield_per")):
                self._refuse()
            self._reading = self._numeric = True
            try:
                self.budget.check(self, state.statement, state.parameters)
            finally:
                self._numeric = False
                self._reading = False
        self._limit_statement()
        with self._permit(state.statement):
            result = state.invoke_statement()
        self.checkpoint()
        return result

    async def tenant(self, context):
        """Authorize only the fixed tenant setup produced by the shared helper."""
        self.checkpoint()
        if isinstance(context, TenantDatabaseContext):
            settings = tenant_context_settings(context)
        elif isinstance(context, WorkspaceAuthContext):
            settings = workspace_auth_context_settings(context)
        else:
            self._refuse()
        self._control = select(*(func.set_config(key, value, True) for key, value in settings.items()))
        try:
            await apply_tenant_context(self.db, context)
            if self._control is not None:
                self._refuse()
        finally:
            self._control = None
        self.checkpoint()

    async def start(self):
        if (self.db.in_transaction() or self.db.identity_map
                or self.db.info.get("tenant_context")):
            self._refuse()
        self.checkpoint()
        connection = await self.db.connection(execution_options={"isolation_level": "REPEATABLE READ"})
        self._async_connection = connection
        self._connection = connection.sync_connection
        self._driver = self._connection.connection.driver_connection
        self._listen(self._connection, "before_execute", self._before_execute)
        self._listen(self._connection, "before_cursor_execute", self._before_cursor)
        self._listen(self._connection, "rollback", self._transaction_ended)
        self._listen(self._connection, "commit", self._commit_event)
        self._listen(self.db.sync_session, "do_orm_execute", self._read)
        self._listen(self.db.sync_session, "after_begin", self._after_begin)
        self._listen(self.db.sync_session, "before_flush", self._forbid_write)
        self._listen(self.db.sync_session, "before_commit", self._before_commit)
        for statement in (text("SET LOCAL lock_timeout = '250ms'"),
                          text("SET LOCAL statement_timeout = '500ms'")):
            with self._permit(statement):
                await connection.execute(statement)
        self.checkpoint()


class ResultInspectionSession(ResultProjectionSession):
    """Locked account reads; no event admission or commit authority."""

    def __init__(self, db, deadline):
        super().__init__(db, deadline)
        self._account_source = None
        self._ready = False

    async def start(self):
        await super().start()
        statement = select(func.pg_try_advisory_xact_lock_shared(273, 3))
        await self.db.run_sync(lambda _: self._limit_statement())
        with self._permit(statement):
            acquired = await self._async_connection.scalar(statement)
        if not acquired:
            self._refuse()
        self._ready = True
        self.checkpoint()

    def bind_account(self, account_id, source_kind):
        self.checkpoint()
        if (not self._ready or self._account_source is not None
                or source_kind not in {"browser", "desktop"}):
            self._refuse()
        self._account_source = (account_id, source_kind)


class ResultAdmissionSession(ResultInspectionSession):
    """Only the fixed result/value pair may write inside this owned snapshot."""

    def __init__(self, db, deadline):
        super().__init__(db, deadline)
        self._phase = 0
        self._admitting = False
        self._committing = False
        self._commit_seen = False
        self._terminal = False
        self._committed = False

    def checkpoint(self):
        if self._terminal:
            self._refuse()
        super().checkpoint()

    async def admit_event(self, event, *, account_id, source_kind, before_insert):
        from twobrain_rec_server.product_analytics.milestones import admit_account_milestone

        self.checkpoint()
        names = ("first_result_viewed", "first_value_session_completed")
        if (self._admitting or self._phase >= len(names) or self._account_source != (account_id, source_kind)
                or event.event_name != names[self._phase]):
            self._refuse()
        self._admitting = True
        inserted = False
        providers = None

        def prepare_insert():
            nonlocal providers
            providers = before_insert()
            self.checkpoint()
            return providers

        async def execute_insert(statement):
            nonlocal inserted
            self.checkpoint()
            if inserted:
                self._refuse()
            await self.db.run_sync(lambda _: self._limit_statement())
            if providers is None or before_insert() != providers:
                self._refuse()
            self.checkpoint()
            self.budget.reserve_uuid()
            inserted = True
            with self._permit(statement):
                result = await self._async_connection.execute(statement)
            self.checkpoint()
            return result

        try:
            result = await admit_account_milestone(
                self.db, event, account_id=account_id, source_kind=source_kind,
                before_insert=prepare_insert, _execute_insert=execute_insert,
            )
            self.checkpoint()
            if not inserted:
                self._refuse()
            self._phase += 1
            return result
        except BaseException:
            self.failed = self.budget.failed = True
            raise
        finally:
            self._admitting = False

    def _before_commit(self, *args):
        self.checkpoint()
        if not self._committing or self._phase != 2 or self._commit_seen:
            self._refuse()

    def _commit_event(self, *args):
        self._before_commit()
        self._commit_seen = True

    async def commit_pair(self, recheck):
        self.checkpoint()
        if self._phase != 2 or self._admitting or self._committing or self.sql_count >= 128:
            self._refuse()
        try:
            recheck()
            self.checkpoint()
            self.sql_count += 1  # COMMIT has no before_cursor_execute event.
            self._committing = True
            await self.db.commit()
            self.checkpoint()
            if not self._commit_seen:
                self._refuse()
            self._committed = True
        except BaseException:
            self.failed = self.budget.failed = True
            raise
        finally:
            self._terminal = True
            self._committing = False

    def finish(self):
        if (not self._committed or self.failed or self.budget.failed
                or asyncio.get_running_loop().time() >= self.deadline):
            self._refuse()


def validate_result_deadlines(work_deadline, cleanup_deadline):
    now = asyncio.get_running_loop().time()
    if (any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            for value in (work_deadline, cleanup_deadline))
            or work_deadline <= now or cleanup_deadline > now + 2
            or cleanup_deadline - work_deadline < 0.5 - 1e-9):
        raise ProjectionBudgetExceeded


@asynccontextmanager
async def _result_session_context(sessionmaker, owner_type, *, work_deadline, cleanup_deadline):
    validate_result_deadlines(work_deadline, cleanup_deadline)
    if (not isinstance(sessionmaker, async_sessionmaker) or sessionmaker.class_ is not AsyncSession
            or not isinstance(sessionmaker.kw.get("bind"), AsyncEngine)
            or sessionmaker.kw.get("binds")
            or sessionmaker.kw.get("sync_session_class") not in (None, Session)):
        raise ProjectionBudgetExceeded  # Never adopt a caller's Session or begun connection.
    db = sessionmaker(autoflush=False, expire_on_commit=False, sync_session_class=_ProjectionSession)
    owner = owner_type(db, work_deadline)
    try:
        async with asyncio.timeout_at(owner.deadline):
            await owner.start()
            yield owner
            owner.finish()
    except Exception:
        owner.failed = owner.budget.failed = True
        raise ProjectionBudgetExceeded from None
    finally:
        owner.detach()
        try:
            async with asyncio.timeout_at(cleanup_deadline):
                await db.close()
        except BaseException:
            # Close must not retain an in-flight owned connection past the budget.
            connection = owner._connection
            if (connection is not None and not connection.closed and not connection.invalidated
                    and connection.connection.driver_connection is owner._driver):
                owner._driver.terminate()
                await db.invalidate()
            raise


@asynccontextmanager
async def result_projection_session(sessionmaker, *, deadline=None):
    """Own one fresh read-only RR snapshot; deadline remains the cleanup end."""
    end = asyncio.get_running_loop().time() + 2
    if deadline is not None:
        end = min(end, deadline)
    async with _result_session_context(
        sessionmaker, ResultProjectionSession, work_deadline=end - 0.5, cleanup_deadline=end,
    ) as owner:
        yield owner


@asynccontextmanager
async def result_admission_session(sessionmaker, *, work_deadline, cleanup_deadline):
    async with _result_session_context(
        sessionmaker, ResultAdmissionSession, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
    ) as owner:
        yield owner


@asynccontextmanager
async def result_inspection_session(sessionmaker, *, work_deadline, cleanup_deadline):
    async with _result_session_context(
        sessionmaker, ResultInspectionSession, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
    ) as owner:
        yield owner
