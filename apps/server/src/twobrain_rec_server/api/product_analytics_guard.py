from __future__ import annotations

import asyncio
import json
import re
import time
from collections import deque
from collections.abc import Awaitable, Callable
from contextvars import ContextVar
from typing import Any

from asyncpg import Connection as AsyncpgConnection
from sqlalchemy import Engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import Pool

PRODUCT_ANALYTICS_POST_PATHS = frozenset(
    {
        "/api/v1/product-analytics/events",
        "/api/v1/product-analytics/posthog-web-capture",
        "/api/v1/product-analytics/posthog-desktop-capture",
    }
)

_RESULT_VIEW_PATH = re.compile(
    r"/(?:desktop/)?meetings/[^/]+/result-viewed"
)
_RESULT_VIEW_TASK_OWNER = ContextVar("result_view_task_owner", default=None)
_RESULT_VIEW_CONNECTION_OWNER = "graf_result_view_owner"
_RESULT_VIEW_INITIALIZATION_OWNER = "graf_result_view_initialization_owner"
_RESULT_VIEW_TRANSACTION_OWNER = "graf_result_view_transaction_owner"


class _ResultViewOwner(dict):
    def __init__(self):
        super().__init__()
        self.transactions = {}
        self.failed = False


@event.listens_for(Session, "after_transaction_create")
def _track_result_transaction(session, transaction):
    owner = _RESULT_VIEW_TASK_OWNER.get()
    if owner is not None and transaction.parent is None:
        lease = [owner, transaction, asyncio.current_task()]
        session.info[_RESULT_VIEW_TRANSACTION_OWNER] = lease
        owner.transactions[transaction] = lease


@event.listens_for(Session, "after_transaction_end")
def _untrack_result_transaction(session, transaction):
    lease = session.info.get(_RESULT_VIEW_TRANSACTION_OWNER)
    if lease is not None and lease[1] is transaction:
        session.info.pop(_RESULT_VIEW_TRANSACTION_OWNER)
        lease[0].transactions.pop(transaction, None)


def _initializing_result_connection(owner, entry):
    if owner is None or _RESULT_VIEW_TASK_OWNER.get() is not owner:
        return None
    lease = owner.get(entry)
    if (
        lease is None or entry.info.get(_RESULT_VIEW_INITIALIZATION_OWNER) is not lease
        or entry.info.get(_RESULT_VIEW_CONNECTION_OWNER) is not lease
        or _RESULT_VIEW_TRANSACTION_OWNER in entry.info
        or lease[0] is not owner or lease[4] is not entry
        or entry.dbapi_connection is not lease[1] or entry.driver_connection is not lease[2]
        or not isinstance(lease[2], AsyncpgConnection) or lease[1].driver_connection is not lease[2]
        or lease[3].get_context().get(_RESULT_VIEW_TASK_OWNER) is not owner
    ):
        return None
    return lease


@event.listens_for(Pool, "connect", insert=True)
@event.listens_for(Pool, "checkout")
def _track_result_connection(dbapi_connection, connection_record, connection_proxy=None):
    owner = _RESULT_VIEW_TASK_OWNER.get()
    if connection_proxy is None:
        if owner is None:
            return
        task = asyncio.current_task()
        driver = connection_record.driver_connection
        if (
            task is None or task.get_context().get(_RESULT_VIEW_TASK_OWNER) is not owner
            or connection_record.in_use or connection_record.dbapi_connection is not dbapi_connection
            or not isinstance(driver, AsyncpgConnection) or dbapi_connection.driver_connection is not driver
            or any(key in connection_record.info for key in (
                _RESULT_VIEW_CONNECTION_OWNER, _RESULT_VIEW_INITIALIZATION_OWNER, _RESULT_VIEW_TRANSACTION_OWNER,
            )) or connection_record in owner
        ):
            owner.failed = True
            return
        lease = [owner, dbapi_connection, driver, task, connection_record]
        connection_record.info[_RESULT_VIEW_INITIALIZATION_OWNER] = lease
        connection_record.info[_RESULT_VIEW_CONNECTION_OWNER] = lease
        owner[connection_record] = lease
        return
    if _RESULT_VIEW_INITIALIZATION_OWNER in connection_record.info:
        lease = _initializing_result_connection(owner, connection_record)
        if lease is None or lease[1] is not dbapi_connection or lease[3] is not asyncio.current_task():
            if owner is not None:
                owner.failed = True
            return
        connection_record.info.pop(_RESULT_VIEW_INITIALIZATION_OWNER)
    connection_record.info.pop(_RESULT_VIEW_TRANSACTION_OWNER, None)
    if owner is not None:
        lease = [owner, dbapi_connection, connection_record.driver_connection, asyncio.current_task(), connection_record]
        connection_record.info[_RESULT_VIEW_CONNECTION_OWNER] = lease
        owner[connection_record] = lease
    else:
        connection_record.info.pop(_RESULT_VIEW_CONNECTION_OWNER, None)


@event.listens_for(Pool, "checkin")
def _untrack_result_connection(dbapi_connection, connection_record):
    if _RESULT_VIEW_INITIALIZATION_OWNER in connection_record.info:
        lease = _initializing_result_connection(_RESULT_VIEW_TASK_OWNER.get(), connection_record)
        if lease is None or lease[1] is not dbapi_connection:
            owner = _RESULT_VIEW_TASK_OWNER.get()
            if owner is not None:
                owner.failed = True
            return
        connection_record.info.pop(_RESULT_VIEW_INITIALIZATION_OWNER)
    connection_record.info.pop(_RESULT_VIEW_TRANSACTION_OWNER, None)
    lease = connection_record.info.pop(_RESULT_VIEW_CONNECTION_OWNER, None)
    if lease is not None:
        lease[0].pop(connection_record, None)


def _terminate_initializing_result_connections(owner, cancelled_tasks):
    for entry in list(owner):
        lease = _initializing_result_connection(owner, entry)
        if (
            lease is not None and not entry.in_use
            and lease[3] in cancelled_tasks and lease[3].cancelling() > 0
        ):
            lease[2].terminate()


def _forget_finished_result_initializations(owner):
    for entry in list(owner):
        lease = _initializing_result_connection(owner, entry)
        if lease is not None and not entry.in_use and lease[3].done() and lease[2].is_closed():
            # A failed entry constructor can finish without a checkin event.
            entry.info.pop(_RESULT_VIEW_INITIALIZATION_OWNER)
            entry.info.pop(_RESULT_VIEW_CONNECTION_OWNER)
            owner.pop(entry)


def _result_connection_lease(connection):
    owner = _RESULT_VIEW_TASK_OWNER.get()
    if owner is None:
        return None
    task = asyncio.current_task()
    if task is None or task.get_context().get(_RESULT_VIEW_TASK_OWNER) is not owner:
        return None
    if connection.closed or connection.invalidated:
        return None
    proxy = connection.connection
    lease = connection.info.get(_RESULT_VIEW_CONNECTION_OWNER)
    if lease is None or lease[0] is not owner:
        return None
    entry = lease[4]
    if (
        not entry.in_use or owner.get(entry) is not lease
        or entry.info.get(_RESULT_VIEW_CONNECTION_OWNER) is not lease
        or proxy.dbapi_connection is not lease[1] or entry.dbapi_connection is not lease[1]
        or proxy.driver_connection is not lease[2] or entry.driver_connection is not lease[2]
    ):
        return None
    return lease


@event.listens_for(Session, "after_begin")
def _bind_result_transaction(session, transaction, connection):
    lease = _result_connection_lease(connection)
    root = session.info.get(_RESULT_VIEW_TRANSACTION_OWNER)
    if (
        lease is not None and root is not None and transaction.parent is None
        and root[0] is lease[0] and root[1] is transaction
        and root[0].transactions.get(transaction) is root
        and _RESULT_VIEW_TRANSACTION_OWNER not in connection.info
    ):
        connection.info[_RESULT_VIEW_TRANSACTION_OWNER] = (root, lease)


@event.listens_for(Engine, "before_cursor_execute")
@event.listens_for(Engine, "rollback")
@event.listens_for(Engine, "commit")
def _handoff_result_connection(connection, *args):
    lease = _result_connection_lease(connection)
    if lease is None:
        return
    association = connection.info.get(_RESULT_VIEW_TRANSACTION_OWNER)
    if association is not None:
        root, bound_lease = association
        if bound_lease is not lease or root[0] is not lease[0] or root[0].transactions.get(root[1]) is not root:
            return
    # Session.__aexit__ moves rollback into a shielded close task.
    lease[3] = asyncio.current_task()
    if association is not None:
        root[2] = lease[3]


def _forget_finished_result_transactions(owner):
    if owner or _RESULT_VIEW_TASK_OWNER.get() is not owner:
        return
    for transaction, lease in list(owner.transactions.items()):
        if (
            lease[0] is not owner or lease[1] is not transaction
            or owner.transactions.get(transaction) is not lease or not lease[2].done()
            or lease[2].get_context().get(_RESULT_VIEW_TASK_OWNER) is not owner
        ):
            continue
        session = transaction.session
        if session.in_transaction() or session.info.get(_RESULT_VIEW_TRANSACTION_OWNER) is not lease:
            continue
        # Cancelled close can skip after_transaction_end after releasing its connection.
        session.info.pop(_RESULT_VIEW_TRANSACTION_OWNER)
        owner.transactions.pop(transaction)


@event.listens_for(Pool, "invalidate")
def _terminate_cancelled_result_connection(dbapi_connection, connection_record, exception):
    owner = _RESULT_VIEW_TASK_OWNER.get()
    if owner is None or not isinstance(exception, asyncio.CancelledError):
        return
    task = asyncio.current_task()
    driver = connection_record.driver_connection
    if (
        task is None or not connection_record.in_use
        or connection_record.dbapi_connection is not dbapi_connection
        or not isinstance(driver, AsyncpgConnection)
        or dbapi_connection.driver_connection is not driver
    ):
        return
    lease = connection_record.info.get(_RESULT_VIEW_CONNECTION_OWNER)
    if lease is not None:
        owned = (lease[0] is owner and lease[1] is dbapi_connection and lease[2] is driver
                 and owner.get(connection_record) is lease)
    else:
        # Automatic pre-ping cancellation precedes checkout, but this exact
        # reserved entry is still owned by the cancelling callback task.
        owned = task.cancelling() > 0 and task.get_context().get(_RESULT_VIEW_TASK_OWNER) is owner
    if owned:
        # Its normal graceful close can outlive this request's cleanup reserve.
        driver.terminate()


class _ResultViewUnavailable(Exception):
    def __init__(self, status=200):
        self.status = status


class _RequestTooLarge(Exception):
    pass


class ProductAnalyticsIngressGuard:
    """Bound anonymous telemetry before FastAPI/Pydantic allocates its body.

    The process-local limiter is a last line of defence; the production edge
    must still apply a distributed limit when multiple API replicas are used.
    """

    def __init__(
        self,
        app: Callable[..., Awaitable[Any]],
        *,
        max_body_bytes: int = 262_144,
        max_requests: int = 120,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if (
            scope.get("type") == "http" and scope.get("method") == "POST"
            and _RESULT_VIEW_PATH.fullmatch(scope.get("path", ""))
        ):
            await _guard_result_view(self.app, scope, receive, send)
            return
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in PRODUCT_ANALYTICS_POST_PATHS
        ):
            await self.app(scope, receive, send)
            return
        if _content_length(scope) > self.max_body_bytes:
            await _send_problem(send, 413, "product_analytics_body_too_large")
            return
        client = scope.get("client")
        client_key = str(client[0]) if isinstance(client, (tuple, list)) and client else "unknown"
        if not await self._allow(client_key):
            await _send_problem(send, 429, "product_analytics_rate_limited")
            return
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            if message.get("type") == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    raise _RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLarge:
            await _send_problem(send, 413, "product_analytics_body_too_large")

    async def _allow(self, client_key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            hits = self._hits.setdefault(client_key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            if len(self._hits) > 4096:
                self._hits = {key: value for key, value in self._hits.items() if value and value[-1] > cutoff}
            return True


def _content_length(scope: dict[str, Any]) -> int:
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == b"content-length":
            try:
                return max(0, int(raw_value))
            except (TypeError, ValueError):
                return 0
    return 0


async def _send_problem(send, status_code: int, code: str) -> None:
    body = json.dumps({"code": code}, separators=(",", ":")).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ambiguous JSON")
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError("invalid JSON constant")


async def _result_view_unavailable(send, deadline, status=200):
    if asyncio.get_running_loop().time() >= deadline:
        return
    body = b'{"status":"unavailable"}'
    try:
        async with asyncio.timeout_at(deadline):
            await send({"type": "http.response.start", "status": status, "headers": [
                (b"content-type", b"application/json"), (b"content-length", str(len(body)).encode()),
                (b"cache-control", b"private, no-store"),
            ]})
            await send({"type": "http.response.body", "body": body})
    except (TimeoutError, OSError):
        # No time or transport remains for another response attempt.
        return


async def _run_result_view_app(app, scope, receive, send):
    owner = _ResultViewOwner()
    token = _RESULT_VIEW_TASK_OWNER.set(owner)

    def children():
        current = asyncio.current_task()
        return [task for task in asyncio.all_tasks() if task is not current
                and task.get_context().get(_RESULT_VIEW_TASK_OWNER) is owner]

    async def join():
        while pending := children():
            await asyncio.gather(*pending, return_exceptions=True)

    task = asyncio.create_task(app(scope, receive, send))
    try:
        await asyncio.shield(task)
        await join()
        if owner.failed or owner or owner.transactions:
            raise _ResultViewUnavailable
    except BaseException:
        # Cancel the DB owner first so parent task-group cancellation cannot
        # repeatedly interrupt SQLAlchemy's invalidation bookkeeping.
        db_tasks = {lease[3] for lease in owner.values() if not lease[3].done()}
        # Session autobegin precedes pool checkout and pre-ping.
        db_tasks.update(lease[2] for lease in owner.transactions.values() if not lease[2].done())
        for child in db_tasks or {task}:
            child.cancel()
        _terminate_initializing_result_connections(owner, db_tasks)
        # SQLAlchemy close uses shielded child tasks; join those as well as ASGI.
        await join()
        _forget_finished_result_initializations(owner)
        _forget_finished_result_transactions(owner)
        raise
    finally:
        _RESULT_VIEW_TASK_OWNER.reset(token)


async def _guard_result_view(app, scope, receive, send):
    """Include auth, dependency teardown and post-response renewal in one budget."""
    loop = asyncio.get_running_loop()
    deadline = loop.time() + 2
    work_deadline = deadline - 0.5
    scope.setdefault("state", {})["result_view_deadline"] = work_deadline
    content_types = [value for name, value in scope.get("headers", []) if name.lower() == b"content-type"]
    if len(content_types) != 1 or content_types[0].split(b";", 1)[0].strip().lower() != b"application/json":
        await _result_view_unavailable(send, deadline, 415)
        return
    if _content_length(scope) > 2048:
        await _result_view_unavailable(send, deadline, 413)
        return
    response_started = False
    try:
        async with asyncio.timeout_at(deadline):
            async with asyncio.timeout_at(work_deadline):
                body = bytearray()
                while True:
                    message = await receive()
                    if message["type"] == "http.disconnect":
                        return
                    if message["type"] != "http.request":
                        raise _ResultViewUnavailable
                    chunk = message.get("body", b"")
                    if len(body) + len(chunk) > 2048:
                        raise _ResultViewUnavailable(413)
                    body.extend(chunk)
                    if not message.get("more_body", False):
                        break
                try:
                    value = json.loads(body.decode("utf-8"), object_pairs_hook=_unique_object,
                                       parse_constant=_reject_constant)
                    if (
                        not isinstance(value, dict) or set(value) != {"proof"}
                        or not isinstance(value["proof"], str) or not value["proof"]
                        or not value["proof"].isascii() or len(value["proof"]) > 1536
                    ):
                        raise ValueError("invalid proof body")
                except (ValueError, UnicodeError, RecursionError):
                    raise _ResultViewUnavailable(400) from None

                delivered = False

                async def replay_receive():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": bytes(body), "more_body": False}
                    return await receive()

                messages = []
                response_bytes = 0

                async def collect(message):
                    nonlocal response_bytes
                    if message["type"] not in {"http.response.start", "http.response.body"}:
                        raise _ResultViewUnavailable
                    response_bytes += len(message.get("body", b"")) + sum(
                        len(name) + len(value) for name, value in message.get("headers", [])
                    )
                    if response_bytes > 4096 or len(messages) >= 32:
                        raise _ResultViewUnavailable
                    message = message.copy()
                    if message["type"] == "http.response.start":
                        message["headers"] = [
                            (name, value) for name, value in message.get("headers", [])
                            if name.lower() != b"cache-control"
                        ] + [(b"cache-control", b"private, no-store")]
                    messages.append(message)

                # Buffer until middleware and session cleanup finish, not merely route return.
                await _run_result_view_app(app, scope, replay_receive, collect)
                if (
                    loop.time() >= work_deadline or not messages
                    or messages[0]["type"] != "http.response.start"
                    or sum(m["type"] == "http.response.start" for m in messages) != 1
                    or messages[-1]["type"] != "http.response.body"
                    or messages[-1].get("more_body", False)
                ):
                    raise _ResultViewUnavailable
            for message in messages:
                response_started = True
                await send(message)
    except Exception as error:
        # A commit may already have happened; never retry admission or echo the input.
        if not response_started:
            await _result_view_unavailable(send, deadline, error.status if isinstance(error, _ResultViewUnavailable) else 200)
