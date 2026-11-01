"""A real PostgreSQL choice, separate from optional event storage (T106)."""
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.analytics import PUBLIC_ANALYTICS_CONSENT_VERSION

ENDPOINT = '/analytics/public-consent'
ORIGIN = 'https://rec.2brain.pro'


@pytest.fixture(autouse=True)
def synthetic_final_provider_gate(monkeypatch):
    # These causal DB tests inject a synthetic sender, with no live receiver.
    from types import SimpleNamespace

    import twobrain_rec_server.public.consent as choices
    monkeypatch.setattr(choices, 'resolve_provider_delivery_gate',
                        lambda *_, **__: SimpleNamespace(allowed=True))


def test_revoke_is_durable_when_measurement_is_disabled(postgres_seeded_database_url):
    settings = Settings(database_url=postgres_seeded_database_url, public_analytics_enabled=False)
    consent_id = str(uuid4())
    with TestClient(create_app(settings)) as client:
        def post(action):
            return client.post(ENDPOINT, json={'action': action, 'consent_id': consent_id},
                               headers={'Origin': ORIGIN})
        assert post('read').json() == {'state': 'unknown'}
        first = post('revoke')
        assert first.status_code == 200, first.text
        value = first.json()
        assert value == {'accepted': True, 'state': 'revoked', 'epoch': value['epoch'],
                         'categories': ['necessary'], 'copy_version': None}
        second = post('revoke').json()
        assert value['epoch'] != second['epoch']
    # A new application/connection sees the committed choice, not local state.
    with TestClient(create_app(settings)) as client:
        read = client.post(ENDPOINT, json={'action': 'read', 'consent_id': consent_id},
                           headers={'Origin': ORIGIN})
        assert read.json() == {'state': 'known', 'epoch': second['epoch'],
                               'categories': ['necessary'], 'copy_version': None}
        denied = client.post(ENDPOINT, headers={'Origin': ORIGIN}, json={
            'action': 'grant', 'consent_id': consent_id, 'expected_epoch': second['epoch'],
            'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION,
        })
        assert denied.status_code == 403
        assert denied.json()['accepted'] is False
        assert 'epoch' not in denied.json()


def test_choice_boundary_requires_exact_origin_and_closed_input(postgres_seeded_database_url):
    with TestClient(create_app(Settings(database_url=postgres_seeded_database_url))) as client:
        payload = {'action': 'revoke', 'consent_id': str(uuid4())}
        for origin in (None, 'null', 'http://rec.2brain.pro', 'https://rec.2brain.pro.evil.test',
                       'https://rec.2brain.pro/path'):
            response = client.post(ENDPOINT, json=payload,
                                   headers={'Origin': origin} if origin else {})
            assert response.status_code == 403, (origin, response.text)
        for bad in ({**payload, 'email': 'synthetic@example.test'},
                    {**payload, 'consent_id': 'not-a-uuid'},
                    {**payload, 'consent_id': payload['consent_id'].upper()},
                    {'action': 'read'}, []):
            response = client.post(ENDPOINT, json=bad, headers={'Origin': ORIGIN})
            assert response.status_code == 400, response.text
            assert response.headers['cache-control'] == 'no-store'


def test_new_grant_never_revives_an_old_epoch(postgres_seeded_database_url, monkeypatch):
    import twobrain_rec_server.public.consent as choices
    monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
    consent_id = str(uuid4())
    with TestClient(create_app(Settings(database_url=postgres_seeded_database_url))) as client:
        def post(action, **fields):
            return client.post(ENDPOINT, json={'action': action, 'consent_id': consent_id, **fields},
                               headers={'Origin': ORIGIN})
        fields = {'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION}
        first = post('revoke').json()['epoch']
        granted = post('grant', expected_epoch=first, **fields)
        assert granted.status_code == 200, granted.text
        assert granted.json()['epoch'] != first
        post('revoke')
        stale = post('grant', expected_epoch=first, **fields)
        assert stale.status_code == 409
        assert 'epoch' not in stale.json()
        fresh = post('revoke').json()['epoch']
        assert post('grant', expected_epoch=fresh, **fields).status_code == 200
        assert post('grant', expected_epoch=first, **fields).status_code == 409


@pytest.mark.parametrize("cancel_parent", [False, True])
def test_delivery_holds_database_order_until_transport_finishes(postgres_seeded_database_url, monkeypatch, cancel_parent):
    import asyncio

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.product_analytics.router as provider_router
    import twobrain_rec_server.public.consent as choices
    from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse

    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        settings = Settings(database_url=postgres_seeded_database_url)
        consent_id = str(uuid4())
        entered, finish = asyncio.Event(), asyncio.Event()
        sends = []
        async def transport(*_):
            sends.append(1)
            entered.set()
            await finish.wait()
            return ProviderTransportResponse(200)
        def sender(settings, event, *, transport):
            transport('https://receiver.example.test/capture', {}, b'{}', 5)
            return {'delivered': True}
        monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
        monkeypatch.setattr(provider_router, '_milestone_http_transport', transport)
        try:
            refused = await choices.control_choice(sessions, settings, {'action': 'revoke', 'consent_id': consent_id})
            grant = await choices.control_choice(sessions, settings, {
                'action': 'grant', 'consent_id': consent_id, 'expected_epoch': refused['epoch'],
                'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION,
            })
            event = {'consent_id': consent_id, 'consent_epoch': grant['epoch'], 'page_path': '/',
                     'properties': {'consent_categories': ['necessary', 'analytics']}}
            first = asyncio.create_task(choices.send_consented_event(sessions, settings, event, sender=sender))
            await asyncio.wait_for(entered.wait(), 2)
            if cancel_parent:
                first.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await first
            revoke = asyncio.create_task(choices.control_choice(sessions, settings, {'action': 'revoke', 'consent_id': consent_id}))
            # Observe the actual PostgreSQL wait, even after HTTP cancellation.
            deadline = asyncio.get_running_loop().time() + 2
            while True:
                async with sessions() as db:
                    waiting = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND NOT granted"))
                if waiting:
                    break
                assert asyncio.get_running_loop().time() < deadline
                await asyncio.sleep(.01)
            assert not revoke.done()
            finish.set()
            if not cancel_parent:
                assert (await first)['delivered'] is True
            assert (await revoke)['accepted'] is True
            assert (await choices.send_consented_event(sessions, settings, event, sender=sender))['delivered'] is False
            assert len(sends) == 1
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def _revoke_in_another_process(url, consent_id, progress, start_revoke):
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from twobrain_rec_server.public.consent import control_choice
    async def run():
        engine = create_async_engine(url, poolclass=NullPool)
        try:
            progress.put('started')
            assert await asyncio.to_thread(start_revoke.wait, 10)
            value = await control_choice(async_sessionmaker(engine), Settings(),
                                         {'action': 'revoke', 'consent_id': consent_id})
            progress.put(value['accepted'])
        finally:
            await engine.dispose()
    asyncio.run(run())


def test_another_process_waits_for_transport_then_blocks_old_epoch(postgres_seeded_database_url, monkeypatch):
    import asyncio
    import multiprocessing

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.product_analytics.router as provider_router
    import twobrain_rec_server.public.consent as choices
    from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse

    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        consent_id = str(uuid4())
        entered, finish = asyncio.Event(), asyncio.Event()
        calls = []
        async def transport(*_):
            calls.append(1)
            entered.set()
            await finish.wait()
            return ProviderTransportResponse(200)
        def sender(settings, event, *, transport):
            transport('https://receiver.example.test', {}, b'{}', 5)
            return {'delivered': True}
        monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
        monkeypatch.setattr(provider_router, '_milestone_http_transport', transport)
        context = multiprocessing.get_context('spawn')
        progress = context.Queue()
        start_revoke = context.Event()
        child = None
        try:
            refused = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            grant = await choices.control_choice(sessions, Settings(), {
                'action': 'grant', 'consent_id': consent_id, 'expected_epoch': refused['epoch'],
                'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION,
            })
            event = {'consent_id': consent_id, 'consent_epoch': grant['epoch'], 'page_path': '/',
                     'properties': {'consent_categories': ['necessary', 'analytics']}}
            # Spawn/import is test preparation, outside the product's 6s
            # delivery budget. A real IPC barrier controls the actual race.
            child = context.Process(target=_revoke_in_another_process,
                                    args=(postgres_seeded_database_url, consent_id, progress, start_revoke))
            child.start()
            assert await asyncio.to_thread(progress.get, True, 10) == 'started'
            sending = asyncio.create_task(choices.send_consented_event(sessions, Settings(), event, sender=sender))
            await asyncio.wait_for(entered.wait(), 2)
            start_revoke.set()
            deadline = asyncio.get_running_loop().time() + 2
            while True:
                async with sessions() as db:
                    waiting = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND NOT granted"))
                if waiting:
                    break
                assert asyncio.get_running_loop().time() < deadline, 'other process never waited on PostgreSQL lock'
                await asyncio.sleep(.01)
            finish.set()
            assert (await sending)['delivered'] is True
            assert await asyncio.to_thread(progress.get, True, 3) is True
            await asyncio.to_thread(child.join, 3)
            assert child.exitcode == 0
            assert (await choices.send_consented_event(sessions, Settings(), event, sender=sender))['delivered'] is False
            assert calls == [1]
        finally:
            finish.set()
            if child is not None and child.is_alive():
                child.terminate()
                child.join(2)
            progress.close()
            progress.join_thread()
            await engine.dispose()
    asyncio.run(scenario())


def test_new_row_cap_preserves_existing_refusal_and_timeout_never_claims_success(
    postgres_seeded_database_url, monkeypatch,
):
    import asyncio

    import pytest
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.public.consent as choices

    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        consent_id = str(uuid4())
        try:
            first = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            monkeypatch.setattr(choices, 'CHOICE_ADMISSION_BYTES', 0)
            with pytest.raises(choices.ChoiceRejected, match='choice_unavailable'):
                await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': str(uuid4())})
            second = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            assert first['epoch'] != second['epoch']
            async with choices.locked_choice(sessions, consent_id):
                monkeypatch.setattr(choices, 'CHOICE_BUDGET_SECONDS', .08)
                with pytest.raises(TimeoutError):
                    await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            observed = await choices.control_choice(sessions, Settings(), {'action': 'read', 'consent_id': consent_id})
            assert observed['epoch'] == second['epoch']
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_commit_failure_returns_no_accepted_choice(postgres_seeded_database_url):
    from sqlalchemy import event
    from sqlalchemy.orm import Session
    def fail_commit(session):
        if session.info.get('tenant_context', {}).get('app.context_kind') == 'public_consent':
            raise OSError('synthetic commit failure')
    with TestClient(create_app(Settings(database_url=postgres_seeded_database_url))) as client:
        event.listen(Session, 'before_commit', fail_commit)
        try:
            response = client.post(ENDPOINT, headers={'Origin': ORIGIN},
                                   json={'action': 'revoke', 'consent_id': str(uuid4())})
            assert response.status_code == 503
            assert response.json() == {'accepted': False, 'reason': 'choice_unavailable'}
        finally:
            event.remove(Session, 'before_commit', fail_commit)


def test_late_sender_failure_preserves_transport_truth_and_late_thread_cannot_send(
    postgres_seeded_database_url, monkeypatch,
):
    import asyncio
    import threading

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.product_analytics.router as provider_router
    import twobrain_rec_server.public.consent as choices
    from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse

    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        consent_id = str(uuid4())
        sends = []
        async def transport(*_):
            sends.append(1)
            return ProviderTransportResponse(200)
        monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
        monkeypatch.setattr(provider_router, '_milestone_http_transport', transport)
        release, started = threading.Event(), threading.Event()
        try:
            refused = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            grant = await choices.control_choice(sessions, Settings(), {
                'action': 'grant', 'consent_id': consent_id, 'expected_epoch': refused['epoch'],
                'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION,
            })
            event = {'consent_id': consent_id, 'consent_epoch': grant['epoch'], 'page_path': '/',
                     'properties': {'consent_categories': ['necessary', 'analytics']}}
            def late_failure(settings, event, *, transport):
                transport('https://receiver.example.test', {}, b'{}', 5)
                raise OSError('synthetic failure after HTTP200')
            result = await choices.send_consented_event(sessions, Settings(), event, sender=late_failure)
            assert result['delivered'] is True, result
            assert result['retryable'] is False
            def stalled_preparation(settings, event, *, transport):
                started.set()
                release.wait(2)
                try:
                    transport('https://receiver.example.test', {}, b'{}', 5)
                except PermissionError:
                    return {'delivered': False}
                raise AssertionError('late sender reached transport')
            monkeypatch.setattr(choices, 'CHOICE_BUDGET_SECONDS', .08)
            task = asyncio.create_task(choices.send_consented_event(sessions, Settings(), event, sender=stalled_preparation))
            assert await asyncio.to_thread(started.wait, 1)
            done, _ = await asyncio.wait([task], timeout=.3)
            assert task in done, 'preparation retained request/DB lock beyond the budget'
            assert (await task)['delivered'] is False
            # The detached preparation is still blocked, but revoke can commit.
            assert (await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id}))['accepted'] is True
            release.set()
            await asyncio.sleep(.05)
            assert sends == [1]
        finally:
            release.set()
            await engine.dispose()
    asyncio.run(scenario())


def test_actual_roles_force_one_choice_and_named_maintenance_only(postgres_isolated_cluster_database_url):
    import asyncio
    import importlib

    import pytest
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import func, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    from twobrain_rec_server.db.models import PublicAnalyticsChoice
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
    from twobrain_rec_server.public.consent import choice_digest, control_choice

    url = postgres_isolated_cluster_database_url
    password = uuid4().hex
    ids = [str(uuid4()), str(uuid4())]
    async def scenario():
        admin = create_async_engine(url, poolclass=NullPool)
        try:
            migration = importlib.import_module('twobrain_rec_server.db.migrations.versions.0108_public_consent')
            def migrate(connection, direction):
                with Operations.context(MigrationContext.configure(connection)):
                    getattr(migration, direction)()
            async with admin.begin() as connection:
                await connection.run_sync(migrate, 'downgrade')
                for role in ('twobrain_rec_app', 'twobrain_rec_maintenance'):
                    await connection.execute(text(f"CREATE ROLE {role} LOGIN PASSWORD '{password}' NOSUPERUSER NOBYPASSRLS NOINHERIT"))
                    await connection.execute(text(f'GRANT USAGE ON SCHEMA public TO {role}'))
                # Execute the actual migration after roles exist, including grants.
                await connection.run_sync(migrate, 'upgrade')
            app_url = make_url(url).set(username='twobrain_rec_app', password=password)
            app = create_async_engine(app_url, poolclass=NullPool)
            maintenance_url = make_url(url).set(username='twobrain_rec_maintenance', password=password)
            maintenance = create_async_engine(maintenance_url, poolclass=NullPool)
            try:
                sessions = async_sessionmaker(app)
                for consent_id in ids:
                    assert (await control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id}))['accepted']
                async with sessions() as db:
                    assert await db.scalar(select(func.count()).select_from(PublicAnalyticsChoice)) == 0
                from twobrain_rec_server.public.consent import locked_choice
                async with locked_choice(sessions, ids[0]) as (db, _, row):
                    assert row.consent_digest == choice_digest(ids[0])
                    assert await db.scalar(select(func.count()).select_from(PublicAnalyticsChoice)) == 1
                    assert await db.scalar(select(PublicAnalyticsChoice).where(
                        PublicAnalyticsChoice.consent_digest == choice_digest(ids[1]))) is None
                async with sessions() as db:
                    assert await db.scalar(select(func.count()).select_from(PublicAnalyticsChoice)) == 0
                    with pytest.raises(DBAPIError):
                        await db.execute(text('DELETE FROM public_analytics_choices'))
                for operation, expected in [('operator_diagnostics', 0), ('public_consent_control', 2)]:
                    async with async_sessionmaker(maintenance)() as db:
                        await apply_tenant_context(db, MaintenanceTenantContext(
                            operation_name=operation, actor_id='synthetic_operator',
                            reason_category='synthetic_test', feature_area='product_analytics'))
                        assert await db.scalar(select(func.count()).select_from(PublicAnalyticsChoice)) == expected
                async with admin.connect() as connection:
                    flags = (await connection.execute(text("SELECT relrowsecurity,relforcerowsecurity FROM pg_class WHERE oid='public_analytics_choices'::regclass"))).one()
                    assert tuple(flags) == (True, True)
            finally:
                await app.dispose()
                await maintenance.dispose()
        finally:
            await admin.dispose()
    asyncio.run(scenario())


def test_stalled_preparations_are_bounded_and_do_not_block_revoke(postgres_seeded_database_url, monkeypatch):
    import asyncio
    import threading

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.public.consent as choices

    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        release = threading.Event()
        count_lock = threading.Lock()
        started = []
        finished = []
        monkeypatch.setattr(choices, 'CHOICE_BUDGET_SECONDS', .08)
        if hasattr(choices, 'PUBLIC_PREPARATIONS'):
            monkeypatch.setattr(choices, 'PUBLIC_PREPARATIONS', threading.BoundedSemaphore(2))
        event = {'consent_id': str(uuid4()), 'consent_epoch': str(uuid4())}
        def stalled(settings, event, *, transport):
            with count_lock:
                started.append(1)
            release.wait(2)
            try:
                transport('https://receiver.example.test', {}, b'{}', 5)
                raise AssertionError('late preparation sent a request')
            except PermissionError:
                return {'delivered': False}
            finally:
                with count_lock:
                    finished.append(1)
        try:
            results = await asyncio.wait_for(asyncio.gather(*[
                choices.send_consented_event(sessions, Settings(), event, sender=stalled) for _ in range(10)
            ]), .5)
            assert all(result['delivered'] is False for result in results)
            assert len(started) == 2, 'unbounded sender preparations were queued/started'
            refused = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': event['consent_id']})
            assert refused['accepted'] is True
            release.set()
            deadline = asyncio.get_running_loop().time() + 1
            while len(finished) < 2:
                assert asyncio.get_running_loop().time() < deadline
                await asyncio.sleep(.01)
            calls = []
            def resumed(settings, event, *, transport):
                calls.append(1)
                return {'delivered': False}
            await choices.send_consented_event(sessions, Settings(), event, sender=resumed)
            assert calls == [1], 'capacity did not recover after actual sender exit'
        finally:
            release.set()
            await engine.dispose()
    asyncio.run(scenario())


def test_real_wrapper_keeps_view_identity_and_final_provider_gate(postgres_seeded_database_url, monkeypatch, tmp_path):
    import asyncio
    import json
    from types import SimpleNamespace

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.product_analytics.posthog_client as posthog
    import twobrain_rec_server.product_analytics.router as provider_router
    import twobrain_rec_server.public.analytics as analytics
    import twobrain_rec_server.public.consent as choices
    key = tmp_path / 'synthetic-provider-key'
    key.write_text('synthetic-key')
    key.chmod(0o600)
    permitted = [True]
    monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
    monkeypatch.setattr(analytics, 'public_analytics_blocker', lambda *_: None)
    monkeypatch.setattr(posthog, 'resolve_provider_delivery_gate', lambda *_, **__: SimpleNamespace(allowed=permitted[0], blockers=()))
    monkeypatch.setattr(choices, 'resolve_provider_delivery_gate', lambda *_, **__: SimpleNamespace(allowed=permitted[0]))
    monkeypatch.setattr(posthog.PostHogClientWrapper, 'from_settings', lambda settings: posthog.PostHogClientWrapper(
        enabled=True, host='https://receiver.example.test', project_key_file=key, project_key_present=True,
        validation_mode='live_safe', live_delivery_allowed=True, settings=settings))
    bodies = []
    async def transport(url, headers, body, timeout):
        assert 0 < timeout <= 5
        bodies.append(json.loads(body))
        return posthog.ProviderTransportResponse(200)
    monkeypatch.setattr(provider_router, '_milestone_http_transport', transport)
    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        consent_id = str(uuid4())
        try:
            refused = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            granted = await choices.control_choice(sessions, Settings(), {
                'action': 'grant', 'consent_id': consent_id, 'expected_epoch': refused['epoch'],
                'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION})
            event = analytics.normalize_public_analytics_event({
                'event_name': 'public_download_viewed', 'page_path': '/download', 'surface': 'public_download',
                'view_id': 'graf_public_view_0123456789abcdef', 'consent_state': 'customized',
                'consent_copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION,
                'consent_categories': ['necessary', 'analytics'], 'consent_id': consent_id,
                'consent_epoch': granted['epoch']})
            assert (await choices.send_consented_event(sessions, Settings(), event))['delivered'] is True
            assert len(bodies) == 1
            assert bodies[0]['distinct_id'] == event['view_id']
            exported = json.dumps(bodies)
            for control_value in (consent_id, choices.choice_digest(consent_id), granted['epoch']):
                assert control_value not in exported
            # Approval closes while the real wrapper's already-approved request
            # waits on the PostgreSQL choice lock. No transport may start later.
            async with choices.locked_choice(sessions, consent_id):
                queued = asyncio.create_task(choices.send_consented_event(sessions, Settings(), event))
                deadline = asyncio.get_running_loop().time() + 2
                while True:
                    async with sessions() as db:
                        waiting = await db.scalar(text("SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND NOT granted"))
                    if waiting:
                        break
                    assert asyncio.get_running_loop().time() < deadline, 'delivery never waited on the choice lock'
                    await asyncio.sleep(.01)
                permitted[0] = False
            assert (await queued)['delivered'] is False, 'provider approval closed during lock wait'
            assert len(bodies) == 1, 'queued delivery bypassed the final provider gate'
            assert (await choices.send_consented_event(sessions, Settings(), event))['delivered'] is False
            assert len(bodies) == 1, 'final provider gate was bypassed'
            permitted[0] = True
            await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
            assert (await choices.send_consented_event(sessions, Settings(), event))['delivered'] is False
            assert len(bodies) == 1
        finally:
            await engine.dispose()
    asyncio.run(scenario())


def test_stalled_final_gate_reads_are_bounded_and_never_send_late(postgres_seeded_database_url, monkeypatch):
    import asyncio
    import threading
    from types import SimpleNamespace

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    from sqlalchemy.pool import NullPool

    import twobrain_rec_server.product_analytics.router as provider_router
    import twobrain_rec_server.public.consent as choices
    from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse

    release = threading.Event()
    count_lock = threading.Lock()
    started, finished, sends = [], [], []
    def read_gate(*_, **__):
        with count_lock:
            started.append(1)
        try:
            assert release.wait(3)
            return SimpleNamespace(allowed=True)
        finally:
            with count_lock:
                finished.append(1)
    def sender(settings, event, *, transport):
        transport('https://receiver.example.test', {}, b'{}', 5)
        return {'delivered': True}
    async def transport(*_):
        sends.append(1)
        return ProviderTransportResponse(200)
    monkeypatch.setattr(choices, 'public_analytics_blocker', lambda *_: None)
    monkeypatch.setattr(choices, 'resolve_provider_delivery_gate', read_gate)
    monkeypatch.setattr(provider_router, '_milestone_http_transport', transport)
    monkeypatch.setattr(choices, 'PUBLIC_GATE_READS', threading.BoundedSemaphore(2))
    async def scenario():
        engine = create_async_engine(postgres_seeded_database_url, poolclass=NullPool)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        events = []
        try:
            for _ in range(2):
                consent_id = str(uuid4())
                refused = await choices.control_choice(sessions, Settings(), {'action': 'revoke', 'consent_id': consent_id})
                grant = await choices.control_choice(sessions, Settings(), {
                    'action': 'grant', 'consent_id': consent_id, 'expected_epoch': refused['epoch'],
                    'categories': ['necessary', 'analytics'], 'copy_version': PUBLIC_ANALYTICS_CONSENT_VERSION})
                events.append({'consent_id': consent_id, 'consent_epoch': grant['epoch'], 'page_path': '/',
                               'properties': {'consent_categories': ['necessary', 'analytics']}})
            monkeypatch.setattr(choices, 'CHOICE_BUDGET_SECONDS', .2)
            results = await asyncio.wait_for(asyncio.gather(*[
                choices.send_consented_event(sessions, Settings(), event, sender=sender) for event in events]), 1)
            assert all(result['delivered'] is False for result in results)
            assert len(started) == 2 and not finished
            for _ in range(3):
                assert (await choices.send_consented_event(sessions, Settings(), events[0], sender=sender))['delivered'] is False
            assert len(started) == 2, 'timed-out readers lost their concurrency slots'
            assert (await choices.control_choice(sessions, Settings(), {
                'action': 'revoke', 'consent_id': events[0]['consent_id']}))['accepted'] is True
            release.set()
            deadline = asyncio.get_running_loop().time() + 1
            while len(finished) < 2:
                assert asyncio.get_running_loop().time() < deadline
                await asyncio.sleep(.01)
            assert sends == [], 'a timed-out reader started late HTTP'
            assert (await choices.send_consented_event(sessions, Settings(), events[1], sender=sender))['delivered'] is True
            assert sends == [1], 'reader capacity did not recover'
        finally:
            release.set()
            await engine.dispose()
    asyncio.run(scenario())
