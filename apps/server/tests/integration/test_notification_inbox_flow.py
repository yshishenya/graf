import asyncio
from uuid import uuid4

from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID, principal, tenant_scope
from twobrain_rec_server.cabinet.web_routes.notifications import inbox_page
from twobrain_rec_server.db.models import Meeting, ServerNotification
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.notifications.inbox import acknowledge_revision, record_event


def test_committed_lifecycle_scope_revision_and_deletion(client):
    async def exercise():
        factory = client.app_state['sessionmaker']
        scope = tenant_scope()
        meeting_id = uuid4()
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            meeting = Meeting(id=meeting_id, workspace_id=WORKSPACE_ID, created_by_user_id=USER_ID,
                              device_id=DEVICE_ID, local_recording_id=str(uuid4()), title='Synthetic meeting',
                              duration_seconds=30, deletion_state='none')
            db.add(meeting)
            await db.flush()
            await record_event(db, meeting=meeting, kind='processing_failed', source_revision='1')
            await db.commit()
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            meeting = await db.get(Meeting, meeting_id)
            await record_event(db, meeting=meeting, kind='result_ready', source_revision='2')
            await db.rollback()
        from types import SimpleNamespace
        request = SimpleNamespace(app=client.app)
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            page = await inbox_page(request, db, scope, principal(), 'important', None, 1)
            assert len(page['items']) == 1 and page['has_unseen_action_required']
            row = await db.scalar(select(ServerNotification).where(ServerNotification.meeting_id == meeting_id).with_for_update())
            acknowledge_revision(row, row.revision)
            shown = row.revision
            meeting = await db.get(Meeting, meeting_id)
            await record_event(db, meeting=meeting, kind='processing_failed', source_revision='retry')
            assert row.revision == shown
            await db.commit()
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            page = await inbox_page(request, db, scope, principal(), 'important', None, 1)
            assert len(page['items']) == 1 and not page['has_unseen_action_required']
            meeting = await db.get(Meeting, meeting_id)
            await record_event(db, meeting=meeting, kind='result_ready', source_revision='success')
            await db.commit()
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            page = await inbox_page(request, db, scope, principal(), 'important', None, 1)
            assert page['items'] == [] and not page['has_unseen_action_required']
            history = await inbox_page(request, db, scope, principal(), 'history', None, 1)
            assert history['items'][0]['title'] == 'Итоги готовы'
            meeting = await db.get(Meeting, meeting_id)
            meeting.deletion_state = 'requested'
            await db.commit()
        async with factory() as db:
            await apply_tenant_scope(db, scope)
            page = await inbox_page(request, db, scope, principal(), 'history', None, 30)
            assert page['items'] == [] and not page['has_unseen_action_required']
    asyncio.run(exercise())


def test_real_share_producer_revocation_and_embedded_route(client):
    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fixtures.cabinet import seed_cabinet_meetings
    from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user, auth_headers_for
    from twobrain_rec_server.db.models import MeetingShareGrant

    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)
    created = client.post(f'/api/v1/cabinet/meetings/{seeds.ready_id}/shares', headers=auth_headers(),
        json={'audience_type':'user', 'audience_id':str(SHARED_USER_ID),
              'content_scope':'full_meeting', 'can_download':False})
    assert created.status_code == 201, created.text
    response = client.get('/api/v1/notifications?filter=history', headers=auth_headers_for())
    assert response.status_code == 200, response.text
    page = response.json()
    assert len(page['items']) == 1 and not page['has_unseen_action_required']
    item = page['items'][0]
    assert item['personal'] and item['href'].startswith('/shared-meetings/')
    assert client.get(item['href'], headers={**auth_headers_for(), 'X-GRAF-Client':'desktop'}).status_code == 200
    html = client.get('/desktop/notifications?filter=history', headers=auth_headers_for())
    assert html.status_code == 200 and '/desktop/shared-meetings/' not in html.text
    async def revoke():
        async with client.app_state['sessionmaker']() as db:
            grant = await db.scalar(select(MeetingShareGrant).where(MeetingShareGrant.meeting_id == seeds.ready_id))
            grant.status = 'revoked'
            await db.commit()
    client.portal.call(revoke)
    assert client.get('/api/v1/notifications?filter=history', headers=auth_headers_for()).json()['items'] == []


def test_notification_rls_rejects_unrelated_member_and_recipient_forgery(client):
    from dataclasses import replace

    import pytest
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user
    from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role

    add_workspace_user(client)
    async def exercise():
        factory = client.app_state['sessionmaker']
        url = client.app.state.settings.database_url
        async with factory() as db:
            meeting = Meeting(id=uuid4(), workspace_id=WORKSPACE_ID, created_by_user_id=USER_ID,
                device_id=DEVICE_ID, local_recording_id=str(uuid4()), title='Synthetic RLS',
                duration_seconds=30, deletion_state='none')
            db.add(meeting)
            await db.flush()
            await record_event(db, meeting=meeting, kind='processing_failed', source_revision='rls')
            meeting_id = meeting.id
            await db.commit()
        role, password = await _create_probe_role(url, role_name='graf_notification_' + uuid4().hex[:12])
        engine = create_async_engine(make_url(url).set(username=role, password=password))
        try:
            scoped = async_sessionmaker(engine, expire_on_commit=False)
            async with scoped() as db:
                assert not await db.scalar(text('select rolbypassrls or rolsuper from pg_roles where rolname=current_user'))
                await apply_tenant_scope(db, replace(tenant_scope(), user_id=SHARED_USER_ID))
                assert list(await db.scalars(select(ServerNotification))) == []
                db.add(ServerNotification(recipient_id=SHARED_USER_ID, workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id, family='result', source_id=uuid4(), source_revision='forged',
                    kind='processing_failed', revision=1, read_revision=0, requires_action=True))
                with pytest.raises(DBAPIError):
                    await db.flush()
                await db.rollback()
                await apply_tenant_scope(db, tenant_scope())
                assert len(list(await db.scalars(select(ServerNotification)))) == 1
        finally:
            await engine.dispose()
            await _drop_probe_role(url, role)
    client.portal.call(exercise)


def test_summary_success_keeps_other_format_failure_until_recovered(client):
    from datetime import UTC, datetime, timedelta

    from tests.fixtures.cabinet import create_outcome_ready_meeting
    from twobrain_rec_server.db.models import (
        MeetingOutcomeGenerationAttempt,
        MeetingOutcomeSet,
        MeetingSummarySlot,
        ProcessingResult,
    )
    from twobrain_rec_server.outcomes.ai_service import _record_summary_notice

    meeting_id = create_outcome_ready_meeting(client, 'notification-multiple-formats')
    async def exercise():
        async with client.app_state['sessionmaker']() as db:
            meeting = await db.get(Meeting, meeting_id)
            result = await db.scalar(select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id))
            failed = MeetingOutcomeGenerationAttempt(workspace_id=meeting.workspace_id,
                meeting_id=meeting.id, processing_result_id=result.id, template_key='meeting_minutes',
                generator_version='synthetic', status='failed', created_at=datetime.now(UTC)-timedelta(minutes=1))
            db.add(failed)
            await db.flush()
            await _record_summary_notice(db, meeting, source_result_id=result.id, completed=True)
            row = await db.scalar(select(ServerNotification).where(ServerNotification.meeting_id == meeting_id))
            assert row.kind == 'summary_failed' and row.requires_action
            shown = row.revision
            retry = MeetingOutcomeGenerationAttempt(workspace_id=meeting.workspace_id,
                meeting_id=meeting.id, processing_result_id=result.id, template_key='meeting_minutes',
                generator_version='synthetic', status='generating', created_at=datetime.now(UTC))
            db.add(retry)
            await db.flush()
            await _record_summary_notice(db, meeting, source_result_id=result.id, completed=True)
            assert row.kind == 'summary_failed' and row.revision == shown
            for status in ('candidate', 'expired', 'cancelled', 'accepted'):
                retry.status = status
                await db.flush()
                await _record_summary_notice(db, meeting, source_result_id=result.id, completed=True)
                assert row.kind == 'summary_failed' and row.revision == shown, status
            replacement = MeetingOutcomeSet(workspace_id=meeting.workspace_id,
                meeting_id=meeting.id, processing_result_id=result.id, template_key='meeting_minutes',
                generator_version='synthetic-replacement', accepted_at=datetime.now(UTC))
            db.add(replacement)
            await db.flush()
            db.add(MeetingSummarySlot(workspace_id=meeting.workspace_id, meeting_id=meeting.id,
                template_key='meeting_minutes', current_outcome_set_id=replacement.id,
                current_binding_class='verified_complete'))
            await db.flush()
            await _record_summary_notice(db, meeting, source_result_id=result.id, completed=True)
            assert row.kind == 'result_ready' and not row.requires_action
            await db.rollback()
    client.portal.call(exercise)


def test_additive_migration_roundtrip_preserves_existing_opt_out(client):
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    migration_path = Path(__file__).resolve().parents[2] / 'src/twobrain_rec_server/db/migrations/versions/0086_notification_inbox.py'
    module_spec = importlib.util.spec_from_file_location('notification_migration', migration_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    async def exercise():
        async with client.app_state['engine'].begin() as connection:
            await connection.execute(text('INSERT INTO billing_notification_preferences (user_id,optional_email_enabled,optional_in_app_enabled,version) VALUES (:user,false,false,4)'), {'user':USER_ID})
            def roundtrip(sync_connection):
                with Operations.context(MigrationContext.configure(sync_connection)):
                    module.downgrade()
                    module.upgrade()
            await connection.run_sync(roundtrip)
            row = (await connection.execute(text('SELECT optional_email_enabled,optional_in_app_enabled,version FROM billing_notification_preferences WHERE user_id=:user'), {'user':USER_ID})).one()
            assert tuple(row) == (False, False, 0)
            # Roll back this historical DDL probe so later tests retain the current schema.
            await connection.rollback()
    client.portal.call(exercise)
