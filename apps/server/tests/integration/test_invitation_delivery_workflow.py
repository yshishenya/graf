from uuid import UUID

import pytest

from twobrain_rec_server.api.schemas import CreateMeetingShareInvitationRequest
from twobrain_rec_server.workflows.temporal_client import (
    cancel_invitation_delivery_workflow,
    invitation_delivery_workflow_id,
    validate_invitation_delivery_workflow_id,
)


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
