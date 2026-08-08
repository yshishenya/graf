import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock
from uuid import uuid4

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.queries import get_account_settings_surface
from twobrain_rec_server.cabinet.view_models import (
    AccountDeviceView,
    AccountProviderView,
    account_device_view,
    account_provider_view,
    account_settings_surface,
)
from twobrain_rec_server.db.models import ExternalIdentity, RegisteredDevice


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
    assert result.label == "Яндекс"
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
    db.scalars = AsyncMock(side_effect=[(), ()])
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
