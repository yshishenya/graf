from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID, tenant_scope
from tests.integration.test_web_owner_session_context import (
    OWNER_REVIEW_TEST_TOKEN,
    _seed_owner_review_session,
)
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.db.models import Meeting, ServerNotification
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.notifications.inbox import record_event


def test_authenticated_inbox_http_pagination_csrf_and_read_race(client):
    async def seed():
        session = await _seed_owner_review_session(client)
        async with client.app_state['sessionmaker']() as db:
            await apply_tenant_scope(db, tenant_scope())
            for index in range(3):
                meeting = Meeting(id=uuid4(), workspace_id=WORKSPACE_ID, created_by_user_id=USER_ID,
                    device_id=DEVICE_ID, local_recording_id=str(uuid4()), title=f'Synthetic {index}',
                    duration_seconds=30, deletion_state='none')
                db.add(meeting)
                await db.flush()
                await record_event(db, meeting=meeting, kind='processing_failed', source_revision='first')
            await db.commit()
        return session.id
    session_id = client.portal.call(seed)
    anonymous = client.get('/api/v1/notifications', follow_redirects=False)
    assert anonymous.status_code in {401, 303}
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    first = client.get('/api/v1/notifications?limit=1')
    assert first.status_code == 200, first.text
    assert first.headers['cache-control'] == 'no-store'
    page = first.json()
    assert page['has_unseen_action_required'] and len(page['items']) == 1
    second = client.get('/api/v1/notifications', params={'limit':1, 'cursor':page['next_cursor']})
    assert second.status_code == 200
    item = page['items'][0]
    assert second.json()['items'][0]['id'] != item['id']
    assert client.get('/api/v1/notifications', params={'filter':'history', 'cursor':page['next_cursor']}).status_code == 422
    assert client.get('/api/v1/notifications?filter=local_upload').status_code == 422
    assert client.get('/api/v1/notifications?limit=0').status_code == 422
    path = f"/api/v1/notifications/{item['id']}/read"
    assert client.post(path, data={'revision':item['revision']}).status_code == 403
    csrf = issue_csrf_token(secret=client.app.state.settings.web_csrf_secret, session_id=session_id)
    headers = {'X-CSRF-Token':csrf, 'Accept':'application/json'}
    foreign_session_csrf = issue_csrf_token(secret=client.app.state.settings.web_csrf_secret, session_id=uuid4())
    assert client.post(path, data={'revision':item['revision']}, headers={
        **headers, 'X-CSRF-Token':foreign_session_csrf,
    }).status_code == 403
    assert client.post(path, data={'revision':999}, headers=headers).status_code == 422
    async def revise():
        async with client.app_state['sessionmaker']() as db:
            await apply_tenant_scope(db, tenant_scope())
            notice = await db.scalar(select(ServerNotification).where(ServerNotification.id == item['id']))
            meeting = await db.get(Meeting, notice.meeting_id)
            await record_event(db, meeting=meeting, kind='result_ready', source_revision='recovered')
            await record_event(db, meeting=meeting, kind='summary_failed', source_revision='new-incident')
            await db.commit()
    client.portal.call(revise)
    assert client.post(path, data={'revision':item['revision']}, headers=headers).status_code == 200
    current = client.get('/api/v1/notifications').json()
    changed = next(row for row in current['items'] if row['id'] == item['id'])
    assert changed['unseen'] and changed['revision'] > item['revision']
    fallback = client.get('/notifications')
    assert fallback.status_code == 200 and 'Просмотрено' in fallback.text
    embedded = client.get('/desktop/notifications')
    assert embedded.status_code == 200 and '/desktop/meetings/' in embedded.text
    older_id = second.json()['items'][0]['id']
    async def change_older(kind):
        async with client.app_state['sessionmaker']() as db:
            await apply_tenant_scope(db, tenant_scope())
            row = await db.get(ServerNotification, older_id)
            meeting = await db.get(Meeting, row.meeting_id)
            await record_event(db, meeting=meeting, kind=kind, source_revision='newer-change')
            await db.commit()
    client.portal.call(change_older, 'summary_failed')
    reordered = client.get('/api/v1/notifications?limit=1').json()
    assert reordered['items'][0]['id'] == older_id
    assert reordered['items'][0]['updated_at'] > reordered['items'][0]['created_at']
    unchanged = reordered['items'][0]['updated_at']
    client.portal.call(change_older, 'summary_failed')
    assert client.get('/api/v1/notifications?limit=1').json()['items'][0]['updated_at'] == unchanged
    client.portal.call(change_older, 'result_ready')
    resolved = client.get('/api/v1/notifications?filter=history&limit=1').json()['items'][0]
    assert resolved['id'] == older_id and resolved['resolved'] and not resolved['requires_action']
    assert 'Проблема решена' in client.get('/notifications?filter=history').text
    async def expire():
        async with client.app_state['sessionmaker']() as db:
            await apply_tenant_scope(db, tenant_scope())
            notice = await db.scalar(select(ServerNotification).where(ServerNotification.id == item['id']))
            notice.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
    client.portal.call(expire)
    assert client.post(path, data={'revision':item['revision']}, headers=headers).status_code == 404


def test_notification_settings_save_conflict_and_html_draft(client):
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    csrf = issue_csrf_token(secret=client.app.state.settings.web_csrf_secret, session_id=session.id)
    data = {'csrf_token':csrf,'version':'0','optional_email_enabled':'false','optional_in_app_enabled':'on'}
    saved = client.post('/settings/notifications', data=data, follow_redirects=False)
    assert saved.status_code == 303, saved.text
    current = client.get('/settings/notifications')
    assert 'name="version" value="1"' in current.text
    conflict = client.post('/settings/notifications', data=data)
    assert conflict.status_code == 409, conflict.text
    assert 'data-notification-settings' in conflict.text
    data['version'] = '1'
    assert client.post('/settings/notifications', data=data, follow_redirects=False).status_code == 303
