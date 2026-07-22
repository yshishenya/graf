from datetime import UTC, datetime, timedelta

import pytest

from twobrain_rec_server.cabinet.access import effective_grant_capabilities
from twobrain_rec_server.config import Settings


def test_summary_only_view_never_implies_full_meeting_or_egress() -> None:
    capabilities = effective_grant_capabilities(
        content_scope="summary_only",
        can_download=False,
        can_export=False,
        expires_at=None,
        now=datetime.now(UTC),
    )

    assert capabilities.can_view_summary is True
    assert capabilities.can_view_full_meeting is False
    assert capabilities.can_download is False
    assert capabilities.can_export is False


def test_expired_grant_has_no_effective_capability() -> None:
    now = datetime.now(UTC)
    capabilities = effective_grant_capabilities(
        content_scope="full_meeting",
        can_download=True,
        can_export=True,
        expires_at=now - timedelta(seconds=1),
        now=now,
    )

    assert not any(
        (
            capabilities.can_view_summary,
            capabilities.can_view_full_meeting,
            capabilities.can_download,
            capabilities.can_export,
        )
    )


def test_broader_sharing_modes_are_disabled_by_default() -> None:
    settings = Settings()

    assert settings.share_workspace_audience_enabled is False
    assert settings.share_team_audience_enabled is False
    assert settings.share_public_links_enabled is False
    assert settings.share_external_invitations_enabled is False


def test_public_links_require_an_explicit_public_base_url() -> None:
    with pytest.raises(ValueError, match="public meeting links require public_base_url"):
        Settings(share_public_links_enabled=True)


def test_public_links_require_shared_ingress_abuse_gate() -> None:
    with pytest.raises(ValueError, match="shared ingress abuse gate"):
        Settings(
            share_public_links_enabled=True,
            public_base_url="https://graf.example.test",
        )


def test_team_sharing_cannot_enable_without_canonical_team_directory() -> None:
    with pytest.raises(ValueError, match="canonical workspace team directory"):
        Settings(share_team_audience_enabled=True)
