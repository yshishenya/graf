"""Read-only owner for the real result reader; this does not open admission."""

import asyncio
from contextlib import asynccontextmanager, contextmanager

from sqlalchemy import event, func, select, text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
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


class ResultProjectionSession:
    def __init__(self, db, deadline):
        self.db = db
        self.deadline = deadline
        self.budget = ProjectionReadBudget()
        self.sql_count = 0
        self.failed = False
        self._task = asyncio.current_task()
        self._connection = None
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
        try:
            yield
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

    def _forbid_write(self, *args):
        self._refuse()

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
        self._connection = connection.sync_connection
        self._driver = self._connection.connection.driver_connection
        self._listen(self._connection, "before_execute", self._before_execute)
        self._listen(self._connection, "before_cursor_execute", self._before_cursor)
        self._listen(self._connection, "rollback", self._transaction_ended)
        self._listen(self._connection, "commit", self._forbid_write)
        self._listen(self.db.sync_session, "do_orm_execute", self._read)
        self._listen(self.db.sync_session, "before_flush", self._forbid_write)
        self._listen(self.db.sync_session, "before_commit", self._forbid_write)
        for statement in (text("SET LOCAL lock_timeout = '250ms'"),
                          text("SET LOCAL statement_timeout = '500ms'")):
            with self._permit(statement):
                await connection.execute(statement)
        self.checkpoint()


@asynccontextmanager
async def result_projection_session(sessionmaker, *, deadline=None):
    """Own one fresh read-only RR snapshot, with no shielded close task.

    The caller must checkpoint around synchronous projection/digest work.
    Admission, writer freshness and HTTP ownership are separate required gates.
    """
    if (not isinstance(sessionmaker, async_sessionmaker) or sessionmaker.class_ is not AsyncSession
            or not isinstance(sessionmaker.kw.get("bind"), AsyncEngine)):
        raise ProjectionBudgetExceeded  # Never adopt a caller's Session or begun connection.
    loop = asyncio.get_running_loop()
    deadline = min(loop.time() + 2, deadline) if deadline is not None else loop.time() + 2
    db = sessionmaker(autoflush=False, expire_on_commit=False)
    owner = ResultProjectionSession(db, deadline - 0.5)
    try:
        async with asyncio.timeout_at(owner.deadline):
            await owner.start()
            yield owner
            owner.checkpoint()
    except Exception:
        owner.failed = owner.budget.failed = True
        raise ProjectionBudgetExceeded from None
    finally:
        owner.detach()
        try:
            async with asyncio.timeout_at(deadline):
                await db.close()
        except BaseException:
            # Close must not retain an in-flight owned connection past the budget.
            connection = owner._connection
            if (connection is not None and not connection.closed and not connection.invalidated
                    and connection.connection.driver_connection is owner._driver):
                owner._driver.terminate()
                await db.invalidate()
            raise
