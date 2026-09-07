from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from twobrain_rec_server.auth.sessions import client_metadata, session_device_access
from twobrain_rec_server.db.models import AuthSession, AuthSessionDeviceBinding, RegisteredDevice


@pytest.mark.parametrize(('agent', 'expected'), [
    ('Mozilla/5.0 GRAFDesktop/2026.09.06.1', ('macos', '2026.09.06.1')),
    ('GRAFDesktop/<script>', ('web', 'browser:unknown:unknown')),
    ('NotGRAFDesktop/1.2', ('web', 'browser:unknown:unknown')),
    ('Mozilla/5.0 (Macintosh) Chrome/130.0 Safari/537.36', ('web', 'browser:chrome:macos')),
    ('Mozilla/5.0 (Windows NT 10.0) Chrome/130 Safari/537 Edg/130', ('web', 'browser:edge:windows')),
    (None, ('web', 'browser:unknown:unknown')),
])
def test_client_metadata_is_bounded_display_hint(agent, expected):
    assert client_metadata(agent) == expected
    assert client_metadata('GRAFDesktop/2026.09.06.1', browser_only=True)[0] == 'web'


def test_session_device_access_distinguishes_bootstrap_and_broken_bindings():
    user_id, workspace_id, session_id, device_id = (uuid4() for _ in range(4))
    session = AuthSession(id=session_id, user_id=user_id, workspace_id=workspace_id,
                          status='active', expires_at=datetime.now(UTC) + timedelta(hours=1))
    device = RegisteredDevice(id=device_id, user_id=user_id, workspace_id=workspace_id,
                              status='active', registration_state='approved')
    binding = AuthSessionDeviceBinding(auth_session_id=session_id,
                                       registered_device_id=device_id, device_state='trusted')
    assert session_device_access(session, {}, []) == (True, None)
    session.device_id = device_id
    assert session_device_access(session, {device_id: device}, []) == (False, None)
    assert session_device_access(session, {device_id: device}, [binding]) == (True, device)
    session.device_id = None
    assert session_device_access(session, {device_id: device}, [binding]) == (True, device)
    binding.device_state = 'blocked'
    assert session_device_access(session, {device_id: device}, [binding]) == (False, None)
    binding.device_state = 'trusted'
    device.status = 'revoked'
    assert session_device_access(session, {device_id: device}, [binding]) == (False, None)


@pytest.mark.parametrize(('direct', 'binding_state', 'expected'), [
    (False, None, 200), (True, None, 403), (False, 'blocked', 403),
    (True, 'blocked', 403), (False, 'trusted', 200), (True, 'trusted', 200),
])
def test_principal_checks_device_before_principal_only_api(client, direct, binding_state, expected):
    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.auth.sessions import hash_token

    token = 'synthetic-client-gate-token'
    async def seed():
        async with client.app_state['sessionmaker']() as db:
            session = AuthSession(user_id=USER_ID, workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID if direct else None, provider='email',
                session_token_hash=hash_token(token), status='active',
                expires_at=datetime.now(UTC) + timedelta(hours=1))
            db.add(session)
            await db.flush()
            if binding_state is not None:
                db.add(AuthSessionDeviceBinding(auth_session_id=session.id,
                    registered_device_id=DEVICE_ID, device_state=binding_state))
            await db.commit()
    client.portal.call(seed)
    response = client.get('/api/v1/auth/me', headers={
        'X-Auth-Session': token, 'X-Workspace-Id': str(WORKSPACE_ID)})
    assert response.status_code == expected, response.text


def test_unique_login_devices_do_not_revive_and_activity_is_bounded(client):
    from sqlalchemy import select

    from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
    from twobrain_rec_server.auth.sessions import (
        create_login_device,
        issue_auth_session,
        record_session_activity,
        revoke_registered_devices,
    )

    async def exercise():
        async with client.app_state['sessionmaker']() as db:
            now = datetime.now(UTC)
            first = await create_login_device(db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                                              user_agent='GRAFDesktop/1.2', now=now)
            await revoke_registered_devices(db, [first], actor_user_id=USER_ID)
            second = await create_login_device(db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                                               user_agent='GRAFDesktop/1.2', now=now)
            assert first.id != second.id and first.status == 'revoked'
            issued = await issue_auth_session(db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                device_id=second.id, provider='email', now=now)
            db.add(AuthSessionDeviceBinding(auth_session_id=issued.id,
                                           registered_device_id=second.id, device_state='trusted'))
            await db.flush()
            row = await db.get(AuthSession, issued.id)
            await record_session_activity(db, row, second, now=now + timedelta(seconds=300))
            await record_session_activity(db, row, second, now=now + timedelta(seconds=310))
            seen = await db.scalar(select(AuthSession.last_seen_at).where(AuthSession.id == row.id))
            assert seen == now + timedelta(seconds=300)
            expiry = row.expires_at
            await revoke_registered_devices(db, [second], actor_user_id=USER_ID)
            await record_session_activity(db, row, second, now=now + timedelta(seconds=900))
            await db.refresh(row)
            assert row.status == 'revoked' and row.last_seen_at == seen and row.expires_at == expiry
            await db.commit()
    client.portal.call(exercise)


@pytest.mark.parametrize('direct', [True, False])
def test_device_revoke_terminates_direct_and_binding_only_session(client, direct):
    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.auth.sessions import hash_token, revoke_registered_devices

    token = 'synthetic-revocation-token'
    async def revoke():
        async with client.app_state['sessionmaker']() as db:
            session = AuthSession(user_id=USER_ID, workspace_id=WORKSPACE_ID,
                device_id=DEVICE_ID if direct else None, provider='email',
                session_token_hash=hash_token(token), status='active',
                expires_at=datetime.now(UTC) + timedelta(hours=1))
            db.add(session)
            await db.flush()
            db.add(AuthSessionDeviceBinding(auth_session_id=session.id,
                registered_device_id=DEVICE_ID, device_state='trusted'))
            await db.flush()
            device = await db.get(RegisteredDevice, DEVICE_ID)
            assert await revoke_registered_devices(db, [device], actor_user_id=USER_ID) == (1, 1)
            await db.commit()
    client.portal.call(revoke)
    assert client.get('/api/v1/auth/me', headers={
        'X-Auth-Session': token, 'X-Workspace-Id': str(WORKSPACE_ID)}).status_code == 401


def test_api_registration_binds_existing_device_and_rejects_rebinding(client):
    from sqlalchemy import select

    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.auth.sessions import issue_auth_session

    async def seed():
        async with client.app_state['sessionmaker']() as db:
            issued = await issue_auth_session(db, user_id=USER_ID, workspace_id=WORKSPACE_ID,
                                              provider='email')
            device = await db.get(RegisteredDevice, DEVICE_ID)
            await db.commit()
            return issued, device.device_public_id
    issued, public_id = client.portal.call(seed)
    headers = {'X-Auth-Session': issued.token, 'X-Workspace-Id': str(WORKSPACE_ID)}
    result = client.post('/api/v1/auth/devices/register', headers=headers,
                         json={'device_public_id': public_id, 'platform': 'macos'})
    assert result.status_code == 200, result.text
    assert result.json()['device_id'] == str(DEVICE_ID)
    again = client.post('/api/v1/auth/devices/register', headers=headers,
                        json={'device_public_id': public_id, 'platform': 'macos'})
    assert again.status_code == 200
    other = client.post('/api/v1/auth/devices/register', headers=headers,
                        json={'device_public_id': 'another-client', 'platform': 'macos'})
    assert other.status_code == 409
    async def verify():
        async with client.app_state['sessionmaker']() as db:
            session = await db.get(AuthSession, issued.id)
            assert session.device_id == DEVICE_ID
            links = list(await db.scalars(select(AuthSessionDeviceBinding).where(
                AuthSessionDeviceBinding.auth_session_id == issued.id)))
            assert len(links) == 1 and links[0].device_state == 'trusted'
    client.portal.call(verify)
