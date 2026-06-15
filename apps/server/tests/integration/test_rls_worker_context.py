from __future__ import annotations

from uuid import UUID

import pytest

from tests.fakes.auth_contexts import WORKSPACE_ID, tenant_scope
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.processing import create_finalized_meeting
from twobrain_rec_server.processing.pickup import pick_up_processing
from twobrain_rec_server.workflows.worker import tenant_scope_from_processing_payload


def test_processing_pickup_sets_worker_tenant_context(client) -> None:
    create_finalized_meeting(client, "rls-worker-context")

    async def run_pickup() -> dict[str, str]:
        async with client.app_state["sessionmaker"]() as db:
            await pick_up_processing(
                db=db,
                settings=client.app.state.settings,
                workspace_id=WORKSPACE_ID,
                tenant_scope=tenant_scope(),
                temporal_client=None,
            )
            return dict(db.info["tenant_context"])

    info = client.portal.call(run_pickup)

    assert info["app.context_kind"] == "worker"
    assert info["app.workspace_id"] == str(WORKSPACE_ID)


def test_processing_pickup_passes_tenant_context_to_temporal_payload(client) -> None:
    finalized = create_finalized_meeting(client, "rls-worker-payload")
    fake_temporal = FakeTemporalClient()

    async def run_pickup() -> dict[str, object]:
        async with client.app_state["sessionmaker"]() as db:
            await pick_up_processing(
                db=db,
                settings=client.app.state.settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=UUID(finalized["meeting"]["meeting_id"]),
                tenant_scope=tenant_scope(),
                temporal_client=fake_temporal,
            )
            return next(iter(fake_temporal.starts.values()))["payload"]

    payload = client.portal.call(run_pickup)

    assert payload["organization_id"] == str(tenant_scope().organization_id)
    assert payload["workspace_id"] == str(tenant_scope().workspace_id)
    assert payload["user_id"] == str(tenant_scope().user_id)
    assert payload["device_id"] == str(tenant_scope().device_id)


def test_worker_activity_restores_tenant_scope_from_payload() -> None:
    scope = tenant_scope()
    payload = {
        "organization_id": str(scope.organization_id),
        "workspace_id": str(scope.workspace_id),
        "user_id": str(scope.user_id),
        "device_id": str(scope.device_id),
    }
    if scope.auth_session_id is not None:
        payload["auth_session_id"] = str(scope.auth_session_id)

    restored = tenant_scope_from_processing_payload(payload)

    assert restored == scope


def test_worker_payload_rejects_missing_tenant_scope() -> None:
    with pytest.raises(ValueError, match="tenant scope"):
        tenant_scope_from_processing_payload({"workspace_id": str(WORKSPACE_ID)})


def test_worker_payload_rejects_malformed_tenant_scope_uuid() -> None:
    scope = tenant_scope()
    payload = {
        "organization_id": str(scope.organization_id),
        "workspace_id": str(scope.workspace_id),
        "user_id": "not-a-uuid",
        "device_id": str(scope.device_id),
    }

    with pytest.raises(ValueError, match="user_id"):
        tenant_scope_from_processing_payload(payload)
