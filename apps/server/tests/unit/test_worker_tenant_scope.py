from __future__ import annotations

import pytest

from tests.fakes.auth_contexts import WORKSPACE_ID, tenant_scope
from twobrain_rec_server.workflows.worker import tenant_scope_from_processing_payload


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

    assert tenant_scope_from_processing_payload(payload) == scope


def test_worker_payload_rejects_missing_tenant_scope() -> None:
    with pytest.raises(ValueError, match="tenant scope"):
        tenant_scope_from_processing_payload({"workspace_id": str(WORKSPACE_ID)})


def test_worker_payload_rejects_malformed_tenant_scope_uuid() -> None:
    scope = tenant_scope()

    with pytest.raises(ValueError, match="user_id"):
        tenant_scope_from_processing_payload(
            {
                "organization_id": str(scope.organization_id),
                "workspace_id": str(scope.workspace_id),
                "user_id": "not-a-uuid",
                "device_id": str(scope.device_id),
            }
        )
