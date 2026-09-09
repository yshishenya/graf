import json
from uuid import UUID

import httpx
import pytest

from twobrain_rec_server.api.schemas import CreateMeetingShareInvitationRequest
from twobrain_rec_server.auth.email_delivery import (
    EmailLoginDeliveryError,
    PostalEmailLoginClient,
)
from twobrain_rec_server.workflows.temporal_client import (
    account_created_email_workflow_id,
    cancel_invitation_delivery_workflow,
    invitation_delivery_workflow_id,
    validate_account_created_email_workflow_id,
    validate_invitation_delivery_workflow_id,
)
from twobrain_rec_server.workflows.worker import invitation_delivery_failure_state


@pytest.mark.parametrize("status", ["pending", "sent"])
async def test_invitation_response_uses_saved_scope_and_roles(monkeypatch, tmp_path, status):
    from datetime import UTC, datetime
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from twobrain_rec_server.api import cabinet

    identity = UUID("10000000-0000-0000-0000-000000000121")
    invitation = SimpleNamespace(
        id=identity, status=status, expires_at=datetime.now(UTC),
        content_scope="full_meeting", can_comment=True, can_edit=True,
    )
    key = tmp_path / "synthetic-key"
    key.write_bytes(b"synthetic-test-key")
    settings = SimpleNamespace(
        share_external_invitations_enabled=True,
        credential_encryption_key_file=key, share_invitation_ttl_seconds=60,
    )
    monkeypatch.setattr(cabinet, "_authorized_meeting", AsyncMock(return_value=(object(), None)))
    monkeypatch.setattr(cabinet, "create_share_invitation", AsyncMock(return_value=invitation))
    delivery = AsyncMock()
    monkeypatch.setattr(cabinet, "start_invitation_delivery_workflow", delivery)
    response = await cabinet.create_meeting_share_invitation_route(
        request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            settings=settings, temporal_client=object(),
        ))),
        meeting_id=identity,
        payload=CreateMeetingShareInvitationRequest(address="synthetic@example.test"),
        tenant_scope=SimpleNamespace(workspace_id=identity),
        principal=SimpleNamespace(user_id=identity),
        device=SimpleNamespace(device_id=identity),
        db=SimpleNamespace(info={}, commit=AsyncMock()),
    )
    data = response.model_dump(mode="json")
    assert data["content_scope"] == "full_meeting"
    assert data["can_comment"] is True
    assert data["can_edit"] is True
    assert delivery.await_count == (1 if status == "pending" else 0)


@pytest.mark.parametrize(
    ("content_scope", "can_download", "can_export", "error_text"),
    [
        ("full_meeting", False, False, "recording invitations"),
        ("full_meeting", True, False, "recording invitations"),
        ("full_meeting", False, True, "recording invitations"),
        ("summary_only", True, False, "summary invitations"),
        ("summary_only", False, True, "summary invitations"),
    ],
)
def test_external_invitation_requires_a_complete_scope_preset(
    content_scope: str,
    can_download: bool,
    can_export: bool,
    error_text: str,
) -> None:
    with pytest.raises(ValueError, match=error_text):
        CreateMeetingShareInvitationRequest(
            address="external@example.com",
            content_scope=content_scope,
            can_download=can_download,
            can_export=can_export,
        )


def test_invitation_delivery_workflow_id_is_deterministic_and_bounded() -> None:
    invitation_id = UUID("10000000-0000-0000-0000-000000000121")
    workflow_id = invitation_delivery_workflow_id(invitation_id)

    assert workflow_id == "share-invitation/10000000-0000-0000-0000-000000000121"
    validate_invitation_delivery_workflow_id(workflow_id)


def test_account_created_email_workflow_id_is_deterministic_and_bounded() -> None:
    invitation_id = UUID("10000000-0000-0000-0000-000000000121")
    workflow_id = account_created_email_workflow_id(invitation_id)

    assert workflow_id == "share-account-created/10000000-0000-0000-0000-000000000121"
    validate_account_created_email_workflow_id(workflow_id)


async def test_invitation_cancellation_uses_the_same_deterministic_id() -> None:
    invitation_id = UUID("10000000-0000-0000-0000-000000000121")
    cancelled: list[str] = []

    class _Handle:
        async def cancel(self) -> None:
            cancelled.append("cancelled")

    class _Client:
        def get_workflow_handle(self, workflow_id: str) -> _Handle:
            assert workflow_id == invitation_delivery_workflow_id(invitation_id)
            return _Handle()

    assert await cancel_invitation_delivery_workflow(
        temporal_client=_Client(), invitation_id=invitation_id
    )
    assert cancelled == ["cancelled"]


def test_invitation_delivery_keeps_pre_egress_failure_distinct() -> None:
    assert invitation_delivery_failure_state(
        EmailLoginDeliveryError("postal_config_missing", retryable=False)
    ) == ("failed", "postal_config_missing")


@pytest.mark.anyio
async def test_invitation_delivery_records_provider_acceptance_without_content() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success"})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="synthetic-postal-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )
    await client.send_meeting_invitation(
        recipient_email="recipient@example.test",
        acceptance_url="https://graf.example.test/share-invitations/synthetic-token",
        delivery_key="synthetic-invitation-id",
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["tag"] == "meeting-share-invitation"
    assert payload["headers"]["X-2brain-Delivery-Key"] == "synthetic-invitation-id"
    assert "synthetic-token" in payload["plain_body"]
    assert "recipient@example.test" not in payload["plain_body"]


def test_invitation_delivery_keeps_post_egress_outcome_unknown() -> None:
    assert invitation_delivery_failure_state(
        EmailLoginDeliveryError(
            "postal_timeout",
            retryable=False,
            outcome_unknown=True,
        )
    ) == ("outcome_unknown", "postal_timeout")
