"""Durable per-choice ordering. This module never emits a visitor identifier."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from hashlib import sha256
from threading import BoundedSemaphore
from uuid import UUID, uuid4

from sqlalchemy import func, select, text

from twobrain_rec_server.db.models import PublicAnalyticsChoice
from twobrain_rec_server.db.tenant_context import PublicConsentContext, apply_tenant_context
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_CONSENT_VERSION,
    normalize_public_analytics_consent,
    public_analytics_blocker,
)

CHOICE_BUDGET_SECONDS = 6.0
CHOICE_ADMISSION_BYTES = 16 * 1024 * 1024
CHOICE_ENDPOINT = '/analytics/public-consent'
# ponytail: four unfinished preparations per API process; use a dedicated pool
# only if measured provider preparation throughput needs more capacity.
PUBLIC_PREPARATIONS = BoundedSemaphore(4)


class ChoiceRejected(ValueError):
    def __init__(self, reason, status=400):
        super().__init__(reason)
        self.status = status


def canonical_uuid(value):
    try:
        parsed = UUID(value) if isinstance(value, str) else None
    except ValueError:
        parsed = None
    if parsed is None or parsed.version != 4 or str(parsed) != value:
        raise ChoiceRejected('invalid_choice_reference')
    return value


def choice_digest(consent_id):
    return sha256(canonical_uuid(consent_id).encode('ascii')).hexdigest()


@asynccontextmanager
async def locked_choice(sessions, consent_id):
    digest = choice_digest(consent_id)
    # One transaction/lock spans the final read, transport and commit. A missing
    # row takes the very same lock, so an initial refusal cannot race delivery.
    async with asyncio.timeout(CHOICE_BUDGET_SECONDS):
        async with sessions() as db:
            async with db.begin():
                await apply_tenant_context(db, PublicConsentContext(digest))
                await db.execute(text("SET LOCAL statement_timeout='6000ms'"))
                await db.execute(text("SET LOCAL lock_timeout='6000ms'"))
                await db.execute(text('SELECT pg_advisory_xact_lock(hashtextextended(:key,0))'),
                                 {'key': 'public-consent:' + digest})
                row = await db.scalar(select(PublicAnalyticsChoice).where(
                    PublicAnalyticsChoice.consent_digest == digest).execution_options(populate_existing=True))
                yield db, digest, row


def normalize_choice(payload):
    if not isinstance(payload, dict):
        raise ChoiceRejected('invalid_choice')
    action = payload.get('action')
    fields = {'action', 'consent_id'}
    if not isinstance(action, str):
        raise ChoiceRejected('invalid_choice')
    if action == 'grant':
        fields |= {'expected_epoch', 'categories', 'copy_version'}
    elif action not in {'read', 'revoke'}:
        raise ChoiceRejected('invalid_choice')
    if set(payload) != fields:
        raise ChoiceRejected('invalid_choice')
    choice_digest(payload['consent_id'])
    if action == 'grant':
        canonical_uuid(payload['expected_epoch'])
        choice = normalize_public_analytics_consent(payload)
        if choice['state'] == 'unknown' or len(choice['categories']) <= 1:
            raise ChoiceRejected('invalid_choice')
        payload = {**payload, 'categories': choice['categories']}
    return payload


async def control_choice(sessions, settings, payload):
    payload = normalize_choice(payload)
    action = payload['action']
    if action == 'grant' and public_analytics_blocker(settings, '/'):
        raise ChoiceRejected('choice_not_allowed', 403)
    async with locked_choice(sessions, payload['consent_id']) as (db, digest, row):
        if action == 'read':
            response = ({'state': 'unknown'} if row is None else {
                'state': 'known', 'epoch': str(row.epoch), 'categories': row.categories,
                'copy_version': row.copy_version,
            })
        else:
            if action == 'grant':
                # Repeat the global guard after waiting for the shared lock.
                if public_analytics_blocker(settings, '/'):
                    raise ChoiceRejected('choice_not_allowed', 403)
                if row is None or str(row.epoch) != payload['expected_epoch']:
                    raise ChoiceRejected('stale_choice', 409)
            if row is None:
                await db.execute(text("SELECT pg_advisory_xact_lock(hashtextextended('public-consent-admission',0))"))
                size = await db.scalar(text("SELECT pg_total_relation_size('public_analytics_choices')"))
                if size >= CHOICE_ADMISSION_BYTES:
                    raise ChoiceRejected('choice_unavailable', 503)
                row = PublicAnalyticsChoice(consent_digest=digest)
                db.add(row)
            row.epoch = uuid4()
            row.categories = payload['categories'] if action == 'grant' else ['necessary']
            row.copy_version = PUBLIC_ANALYTICS_CONSENT_VERSION if action == 'grant' else None
            row.updated_at = func.now()
            response = {'accepted': True, 'state': 'granted' if action == 'grant' else 'revoked',
                        'epoch': str(row.epoch), 'categories': row.categories, 'copy_version': row.copy_version}
    # __aexit__ above has successfully committed; an uncertain commit cannot
    # expose an epoch or claim that a refusal has been saved.
    return response


def _allows_event(row, event):
    return bool(
        row is not None and str(row.epoch) == event.get('consent_epoch')
        and row.copy_version == PUBLIC_ANALYTICS_CONSENT_VERSION
        and 'analytics' in row.categories
        and row.categories == event.get('properties', {}).get('consent_categories')
    )


async def send_consented_event(sessions, settings, event, *, sender=None):
    """Only the bounded native async transport owns the database lock.

    Synchronous provider preparation may finish late. Its attempt is then
    irrevocably closed: neither that thread nor an already queued callback can
    start a transport. It never owns a DB connection while preparing a request.
    """
    from threading import Event

    from twobrain_rec_server.product_analytics.router import _milestone_http_transport
    from twobrain_rec_server.public.analytics import deliver_public_analytics_event

    loop = asyncio.get_running_loop()
    deadline = loop.time() + CHOICE_BUDGET_SECONDS
    closed = Event()
    entered = False
    response_status = None
    sender = sender or deliver_public_analytics_event

    def outcome(fallback=None):
        if response_status is not None:
            return {"provider": "posthog", "status": "live_safe_sent" if 200 <= response_status < 300 else "provider_error",
                    "delivered": 200 <= response_status < 300, "retryable": False}
        if entered:
            return {"provider": "posthog", "status": "transport_ambiguous", "delivered": None, "retryable": False}
        return {**(fallback or {"provider": "posthog", "status": "choice_blocked", "delivered": False}),
                "retryable": False}

    async def guarded_transport(url, headers, body, timeout):
        nonlocal entered, response_status
        if closed.is_set() or loop.time() >= deadline:
            raise PermissionError("choice_attempt_closed")
        async with asyncio.timeout_at(deadline):
            async with locked_choice(sessions, event.get("consent_id")) as (db, digest, row):
                if (closed.is_set() or loop.time() >= deadline or not _allows_event(row, event)
                        or public_analytics_blocker(settings, event["page_path"])):
                    raise PermissionError("choice_blocked")
                entered = True
                response = await _milestone_http_transport(
                    url, headers, body, min(timeout, 5.0, max(0, deadline - loop.time())))
                # Keep the observed HTTP result even if subsequent commit or
                # synchronous sender cleanup fails. A lost reply stays unknown.
                response_status = response.status_code
            return response

    def transport(url, headers, body, timeout):
        if closed.is_set():
            raise PermissionError("choice_attempt_closed")
        return asyncio.run_coroutine_threadsafe(
            guarded_transport(url, headers, body, timeout), loop).result()

    task = None
    try:
        canonical_uuid(event.get("consent_epoch"))
        choice_digest(event.get("consent_id"))
        if not PUBLIC_PREPARATIONS.acquire(blocking=False):
            return outcome()
        # A slot belongs to the actual preparation, not to its timed-out HTTP
        # waiter. At most four futures can occupy/queue in the shared executor.
        slots = PUBLIC_PREPARATIONS
        def prepare():
            try:
                if closed.is_set():
                    raise PermissionError("choice_attempt_closed")
                return sender(settings, event, transport=transport)
            finally:
                slots.release()
        task = asyncio.create_task(asyncio.to_thread(prepare))
        # Retrieve a late exception without leaving a background retry/transport.
        task.add_done_callback(lambda done: None if done.cancelled() else done.exception())
        async with asyncio.timeout_at(deadline):
            result = await asyncio.shield(task)
        return outcome(result)
    except Exception:
        return outcome()
    finally:
        # A canceled request does not release a transport's lock: the native
        # coroutine owns it until bounded I/O/transaction exit. Late preparation
        # owns no lock and its capability to enter that coroutine is revoked.
        closed.set()
