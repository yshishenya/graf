import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.queries import get_account_settings_surface
from twobrain_rec_server.cabinet.view_models import (
    AccountDeviceView,
    AccountProfileView,
    AccountProviderView,
    AccountSessionView,
    account_device_view,
    account_provider_view,
    account_session_view,
    account_settings_surface,
)
from twobrain_rec_server.db.models import AuthSession, ExternalIdentity, RegisteredDevice


def test_account_provider_projection_masks_identity_subject_and_translates_status() -> None:
    identity = ExternalIdentity(
        user_id=uuid4(),
        provider="yandex",
        provider_subject="private-subject",
        is_verified=True,
        last_seen_at=datetime(2026, 7, 25, tzinfo=UTC),
    )

    result = account_provider_view(identity, primary=True)

    assert isinstance(result, AccountProviderView)
    assert result.label == "Яндекс ID"
    assert result.status_label == "Подключён"
    assert result.primary is True
    assert not hasattr(result, "provider_subject")


def test_account_device_projection_shows_current_safe_metadata() -> None:
    device_id = uuid4()
    device = RegisteredDevice(
        id=device_id,
        workspace_id=uuid4(),
        user_id=uuid4(),
        device_public_id="private-device-id",
        platform="macos",
        client_version="3.4.5",
        status="active",
        registration_state="approved",
        last_seen_at=datetime(2026, 7, 25, tzinfo=UTC),
    )

    result = account_device_view(device, current_device_id=device_id)

    assert isinstance(result, AccountDeviceView)
    assert result.platform_label == "Mac"
    assert result.version_label == "3.4.5"
    assert result.status_label == "Активно"
    assert result.current is True
    assert result.can_revoke is False
    assert not hasattr(result, "device_public_id")


def test_account_session_projection_marks_current_and_exposes_safe_metadata_only() -> None:
    session_id = uuid4()
    session = AuthSession(
        id=session_id,
        user_id=uuid4(),
        workspace_id=uuid4(),
        provider="yandex",
        session_token_hash="private-token-hash",
        status="active",
        expires_at=datetime(2026, 7, 26, tzinfo=UTC),
        last_seen_at=datetime(2026, 7, 25, tzinfo=UTC),
    )

    result = account_session_view(session, current_session_id=session_id, now=datetime(2026, 7, 25, tzinfo=UTC))

    assert isinstance(result, AccountSessionView)
    assert result.provider_label == "Яндекс ID"
    assert result.status_label == "Действует"
    assert result.current is True
    assert result.can_revoke is False
    assert not hasattr(result, "session_token_hash")


def test_account_profile_projection_defaults_to_bounded_preferences() -> None:
    profile = AccountProfileView(display_name="Тест")

    assert profile.locale == "ru-RU"
    assert profile.timezone == "Europe/Moscow"
    assert profile.theme == "system"


def test_account_surface_keeps_provider_and_device_projections_bounded() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    identity = ExternalIdentity(
        user_id=user_id,
        provider="unknown-provider",
        provider_subject="private-subject",
        is_verified=False,
    )
    device = RegisteredDevice(
        id=uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        device_public_id="private-device-id",
        platform="web",
        status="revoked",
        registration_state="revoked",
    )

    surface = account_settings_surface(
        identities=(identity,),
        devices=(device,),
        current_device_id=uuid4(),
    )

    assert len(surface.providers) == 1
    assert surface.providers[0].label == "Способ входа"
    assert len(surface.devices) == 1
    assert surface.devices[0].platform_label == "Браузер"
    assert surface.devices[0].status_label == "Отозвано"


def test_account_query_filters_current_user_and_workspace() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.scalar = AsyncMock(return_value=None)
    db.scalars = AsyncMock(side_effect=[(), (), ()])
    scope = TenantScope(
        organization_id=uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        device_id=uuid4(),
    )

    surface = asyncio.run(get_account_settings_surface(db, scope))

    assert surface.providers == ()
    identity_sql = str(db.scalars.await_args_list[0].args[0])
    device_sql = str(db.scalars.await_args_list[1].args[0])
    assert "external_identities.user_id" in identity_sql
    assert "registered_devices.workspace_id" in device_sql
    assert "registered_devices.user_id" in device_sql
    session_sql = str(db.scalars.await_args_list[2].args[0])
    assert "auth_sessions.workspace_id" in session_sql
    assert "auth_sessions.user_id" in session_sql


def test_account_query_does_not_treat_telegram_as_email_recovery() -> None:
    user_id = uuid4()
    workspace_id = uuid4()
    email = ExternalIdentity(
        id=uuid4(),
        user_id=user_id,
        provider="email",
        provider_subject="email-subject",
        is_verified=True,
    )
    telegram = ExternalIdentity(
        id=uuid4(),
        user_id=user_id,
        provider="telegram",
        provider_subject="telegram-subject",
        is_verified=True,
    )
    db = AsyncMock()
    db.get = AsyncMock(return_value=None)
    db.scalar = AsyncMock(return_value=None)
    db.scalars = AsyncMock(side_effect=[(email, telegram), (), ()])
    scope = TenantScope(
        organization_id=uuid4(),
        workspace_id=workspace_id,
        user_id=user_id,
        device_id=uuid4(),
    )

    surface = asyncio.run(get_account_settings_surface(db, scope))
    by_provider = {provider.provider: provider for provider in surface.providers}

    assert by_provider["email"].can_unlink is False
    assert by_provider["telegram"].can_unlink is True


def test_session_surface_separates_effective_access_and_uses_local_time() -> None:
    from datetime import timedelta

    from twobrain_rec_server.db.models import AuthSessionDeviceBinding

    now = datetime(2026, 9, 6, 12, tzinfo=UTC)
    user, workspace = uuid4(), uuid4()
    device = RegisteredDevice(id=uuid4(), user_id=user, workspace_id=workspace,
                              device_public_id='login:synthetic', platform='macos',
                              client_version='2026.09.06.1', status='active', registration_state='approved')
    def session(status='active', expired=False):
        return AuthSession(id=uuid4(), user_id=user, workspace_id=workspace, device_id=device.id,
                           provider='email', status=status, issued_at=now-timedelta(hours=2),
                           last_seen_at=now-timedelta(minutes=3),
                           expires_at=now+timedelta(hours=-1 if expired else 1))
    current, expired, revoked, broken = session(), session(expired=True), session('revoked'), session()
    unbound = session()
    unbound.device_id = None
    rows = (expired, unbound, revoked, broken, current)
    bindings = [AuthSessionDeviceBinding(auth_session_id=s.id, registered_device_id=device.id,
                                        device_state='trusted') for s in (current, expired, revoked)]
    surface = account_settings_surface(profile=AccountProfileView(display_name='Тест', timezone='Asia/Yekaterinburg'),
                                      devices=(device,), sessions=rows, bindings=bindings,
                                      current_session_id=current.id, now=now)
    assert [s.session_id for s in surface.active_sessions] == [current.id, unbound.id]
    assert surface.active_sessions[0].client_label == 'GRAF для macOS'
    assert surface.active_sessions[0].last_seen_label == '06.09.2026, 16:57 (Asia/Yekaterinburg)'
    assert surface.active_sessions[1].client_label == 'Устройство не подключено'
    assert {s.status_label for s in surface.session_history} == {'Срок истёк', 'Завершён', 'Доступ заблокирован'}
    assert all(not s.can_revoke for s in surface.session_history)
    assert surface.has_other_sessions


def test_old_client_metadata_is_not_invented_or_rendered_raw() -> None:
    from datetime import timedelta

    from twobrain_rec_server.db.models import AuthSessionDeviceBinding

    now = datetime.now(UTC)
    device = RegisteredDevice(id=uuid4(), workspace_id=uuid4(), user_id=uuid4(),
                              device_public_id='browser-email:synthetic', platform='web',
                              client_version='email-login', status='active', registration_state='approved')
    session = AuthSession(id=uuid4(), user_id=device.user_id, workspace_id=device.workspace_id,
                          device_id=device.id, provider='email', status='active', expires_at=now+timedelta(hours=1))
    binding = AuthSessionDeviceBinding(auth_session_id=session.id, registered_device_id=device.id, device_state='trusted')
    view = account_settings_surface(devices=(device,), sessions=(session,), bindings=(binding,), now=now).sessions[0]
    assert view.client_label == 'Неизвестный вход'
    assert view.last_seen_label == 'Нет данных'
    assert 'email-login' not in repr(view)
    assert 'browser-email' not in repr(view)


def test_session_compact_time_uses_local_calendar_without_claiming_online() -> None:
    from twobrain_rec_server.cabinet.view_models import _session_time

    now = datetime(2026, 1, 1, 20, tzinfo=UTC)  # January 2 in the profile zone.
    cases = [
        (datetime(2026, 1, 1, 19, 30, tzinfo=UTC), "Asia/Yekaterinburg", "сегодня, 00:30"),
        (datetime(2026, 1, 1, 18, 59, tzinfo=UTC), "Asia/Yekaterinburg", "вчера, 23:59"),
        (datetime(2025, 12, 31, 18, tzinfo=UTC), "Asia/Yekaterinburg", "31.12.2025, 23:00"),
        (datetime(2026, 1, 1, 20, 1, tzinfo=UTC), "UTC", "01.01.2026, 20:01"),
        (datetime(2026, 1, 1, 19, 30), "invalid/zone", "сегодня, 19:30"),
        (None, "UTC", "Нет данных"),
    ]
    for value, zone, expected in cases:
        assert _session_time(value, zone, relative_to=now) == expected
    assert _session_time(cases[0][0], "Asia/Yekaterinburg") == "02.01.2026, 00:30 (Asia/Yekaterinburg)"
