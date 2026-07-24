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
    cancel_invitation_delivery_workflow,
    invitation_delivery_workflow_id,
    validate_invitation_delivery_workflow_id,
)
from twobrain_rec_server.workflows.worker import invitation_delivery_failure_state


@pytest.mark.parametrize(
    ("content_scope", "can_download", "can_export"),
    [
        ("full_meeting", False, False),
        ("summary_only", True, False),
        ("summary_only", False, True),
    ],
)
def test_external_invitation_is_summary_only_without_egress_capabilities(
    content_scope: str,
    can_download: bool,
    can_export: bool,
) -> None:
    with pytest.raises(ValueError, match="summary-only"):
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
