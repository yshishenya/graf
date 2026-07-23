from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import (
    CreateMeetingShareInvitationRequest,
    SharePanelState,
    ShareRecipientView,
)
from twobrain_rec_server.cabinet.access import (
    MAX_SHARE_INVITATION_TTL_SECONDS,
    bounded_share_invitation_expiry,
    effective_grant_capabilities,
    escape_share_search_query,
)


def test_share_search_escapes_like_wildcards_and_bounds_input() -> None:
    assert escape_share_search_query(r"a%_\b") == r"a\%\_\\b"
    assert len(escape_share_search_query("x" * 120)) == 80


def test_invitation_expiry_is_positive_and_bounded() -> None:
    now = datetime(2026, 7, 23, 12, tzinfo=UTC)

    expiry = bounded_share_invitation_expiry(
        now=now,
        ttl_seconds=MAX_SHARE_INVITATION_TTL_SECONDS * 4,
    )

    assert expiry == now + timedelta(seconds=MAX_SHARE_INVITATION_TTL_SECONDS)
    with pytest.raises(ProblemDetail) as error:
        bounded_share_invitation_expiry(now=now, ttl_seconds=0)
    assert error.value.code == "invalid_invitation_ttl"


def test_external_invitation_request_is_summary_only() -> None:
    with pytest.raises(ValidationError):
        CreateMeetingShareInvitationRequest(
            address="recipient@example.test",
            content_scope="full_meeting",
        )
    with pytest.raises(ValidationError):
        CreateMeetingShareInvitationRequest(
            address="recipient@example.test",
            can_download=True,
        )


def test_share_projection_exposes_source_and_capability_without_content() -> None:
    recipient = ShareRecipientView(
        user_id="30000000-0000-0000-0000-000000000017",
        display_label="Synthetic teammate",
        source="workspace_calendar",
        freshness="current",
    )
    panel = SharePanelState(
        team_visibility="disabled",
        copy_link_state="available",
        public_link_state="disabled_by_default",
        capability_state="available",
        external_invitation_state="disabled",
        recipient_sources=["workspace", "calendar"],
    )

    assert recipient.recipient_type == "workspace_member"
    assert panel.external_invitation_state == "disabled"
    assert not hasattr(panel, "transcript")
    assert not hasattr(panel, "audio")


def test_expired_summary_grant_has_no_effective_capability() -> None:
    now = datetime.now(UTC)
    capabilities = effective_grant_capabilities(
        content_scope="summary_only",
        can_download=False,
        can_export=False,
        expires_at=now - timedelta(seconds=1),
        now=now,
    )

    assert capabilities.can_view_summary is False
    assert capabilities.can_view_full_meeting is False
