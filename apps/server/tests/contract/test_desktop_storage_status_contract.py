from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.billing import storage_status as module
from twobrain_rec_server.billing.storage import StorageProjection
from twobrain_rec_server.config import Settings


class _FakeDb:
    def __init__(self, subscription=None) -> None:
        self.subscription = subscription

    async def scalar(self, statement):
        return self.subscription

    async def get(self, model, key):
        return None


def _settings(**overrides) -> Settings:
    values = {
        "retention_meeting_delete_after_days": 365,
        "retention_backup_expiry_days": 30,
        "retention_local_buffer_expiry_days": 7,
    }
    values.update(overrides)
    return Settings(**values)


def _scope(user_id=None, workspace_id=None) -> TenantScope:
    return TenantScope(
        organization_id=uuid4(),
        workspace_id=workspace_id or uuid4(),
        user_id=user_id or uuid4(),
        device_id=uuid4(),
    )


def _patch_role(monkeypatch, role: str) -> None:
    async def fake_role(db, *, tenant_scope):
        return role, None

    monkeypatch.setattr(module, "_resolve_billing_role", fake_role)


def _patch_projection(monkeypatch, projection: StorageProjection | Exception) -> None:
    async def fake_reserved(db, *, workspace_id, now):
        return projection.reserved_bytes if isinstance(projection, StorageProjection) else 0

    async def fake_project(db, *, workspace_id, capacity_bytes, reserved_bytes):
        if isinstance(projection, Exception):
            raise projection
        return projection

    monkeypatch.setattr(module, "_active_reserved_bytes", fake_reserved)
    monkeypatch.setattr(module, "project_active_playback_storage", fake_project)


@pytest.mark.asyncio
async def test_missing_database_session_is_503() -> None:
    with pytest.raises(ProblemDetail) as error:
        await module.desktop_storage_status(None, tenant_scope=_scope(), settings=_settings())

    assert error.value.status == 503
    assert error.value.code == "cabinet_store_unavailable"
    assert error.value.headers == {"Cache-Control": "no-store"}


@pytest.mark.asyncio
async def test_personal_owner_with_payer_rights_can_manage(monkeypatch) -> None:
    _patch_role(monkeypatch, "owner")
    _patch_projection(monkeypatch, StorageProjection(used_bytes=10, reserved_bytes=0, capacity_bytes=100))
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=scope.user_id))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.billing_role == "owner"
    assert response.access_mode == "manage"
    assert response.used_bytes == 10
    assert response.available_bytes == 90
    assert response.threshold == "normal"
    assert response.action == "none"
    assert response.action_path is None
    assert response.retention_policy_state == "active"


@pytest.mark.asyncio
async def test_personal_owner_over_threshold_gets_manage_action(monkeypatch) -> None:
    _patch_role(monkeypatch, "owner")
    _patch_projection(monkeypatch, StorageProjection(used_bytes=96, reserved_bytes=0, capacity_bytes=100))
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=None))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.access_mode == "manage"
    assert response.threshold == "95%"
    assert response.action == "open_billing_storage"
    assert response.action_path == "/billing/storage"


@pytest.mark.asyncio
async def test_corporate_admin_is_read_only_with_visible_amounts(monkeypatch) -> None:
    _patch_role(monkeypatch, "admin")
    _patch_projection(monkeypatch, StorageProjection(used_bytes=96, reserved_bytes=0, capacity_bytes=100))
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=uuid4()))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.billing_role == "admin"
    assert response.access_mode == "read_only"
    assert response.used_bytes == 96
    assert response.threshold == "95%"
    assert response.action == "contact_owner"
    assert response.action_path is None


@pytest.mark.asyncio
async def test_member_gets_no_amounts_and_no_action(monkeypatch) -> None:
    _patch_role(monkeypatch, "member")
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=None))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.billing_role == "member"
    assert response.access_mode == "read_only"
    assert response.used_bytes is None
    assert response.reserved_bytes is None
    assert response.capacity_bytes is None
    assert response.available_bytes is None
    assert response.threshold == "unknown"
    assert response.action == "none"
    assert response.action_path is None
    assert response.meeting_retention_days == 365
    assert response.retention_policy_state == "active"


@pytest.mark.asyncio
async def test_unknown_role_gets_safe_member_profile(monkeypatch) -> None:
    _patch_role(monkeypatch, "mystery")
    scope = _scope()
    db = _FakeDb(None)

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.billing_role == "member"
    assert response.access_mode == "read_only"
    assert response.threshold == "unknown"
    assert response.action == "none"


@pytest.mark.asyncio
async def test_unknown_plan_fails_closed(monkeypatch) -> None:
    _patch_role(monkeypatch, "admin")
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="mystery", state="mystery", paid_through=None, trial_ends_at=None, billing_owner_id=None))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.access_mode == "read_only"
    assert response.threshold == "unknown"
    assert response.action == "none"
    assert response.used_bytes is None


@pytest.mark.asyncio
async def test_projection_failure_stays_successful_unknown(monkeypatch) -> None:
    _patch_role(monkeypatch, "owner")
    _patch_projection(monkeypatch, RuntimeError("projection unavailable"))
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=scope.user_id))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.access_mode == "manage"
    assert response.used_bytes is None
    assert response.threshold == "unknown"
    assert response.action == "none"
    assert response.retention_policy_state == "active"


@pytest.mark.asyncio
async def test_payer_mismatch_is_read_only_but_amounts_remain_visible(monkeypatch) -> None:
    _patch_role(monkeypatch, "owner")
    _patch_projection(monkeypatch, StorageProjection(used_bytes=96, reserved_bytes=0, capacity_bytes=100))
    scope = _scope()
    db = _FakeDb(SimpleNamespace(plan_code="free", state="free", paid_through=None, trial_ends_at=None, billing_owner_id=uuid4()))

    response = await module.desktop_storage_status(db, tenant_scope=scope, settings=_settings())

    assert response.billing_role == "owner"
    assert response.access_mode == "read_only"
    assert response.used_bytes == 96
    assert response.action == "contact_owner"
    assert response.action_path is None


def test_storage_status_route_is_no_store(client: TestClient) -> None:
    response = client.get("/api/v1/desktop/storage/status", headers=auth_headers())

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    body = response.json()
    assert body["billing_role"] in {"owner", "admin", "member"}
    assert body["access_mode"] in {"manage", "read_only"}
    assert body["threshold"] in {"normal", "80%", "95%", "full", "unknown"}
    assert body["action"] in {"none", "open_billing_storage", "contact_owner"}
