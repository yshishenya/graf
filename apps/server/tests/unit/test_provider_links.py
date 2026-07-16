from datetime import UTC, datetime, timedelta

from twobrain_rec_server.auth.provider_links import expire_if_needed, scrub_candidate
from twobrain_rec_server.db.models import WorkspaceProviderLinkState


def _link(*, expires_at: datetime) -> WorkspaceProviderLinkState:
    return WorkspaceProviderLinkState(
        expires_at=expires_at,
        candidate_identity_subject="verified-subject",
        candidate_email="verified@example.test",
        candidate_phone="+70000000000",
        candidate_display_name="Verified",
    )


async def test_expired_link_scrubs_verified_claims() -> None:
    now = datetime.now(UTC)
    link = _link(expires_at=now - timedelta(seconds=1))

    assert await expire_if_needed(link, now=now) is True
    assert link.status == "expired"
    assert link.resolution == "expired"
    assert link.candidate_identity_subject is None
    assert link.candidate_email is None
    assert link.candidate_phone is None
    assert link.candidate_display_name is None


def test_scrub_candidate_keeps_only_safe_terminal_state() -> None:
    link = _link(expires_at=datetime.now(UTC))

    scrub_candidate(link, status="conflict", resolution="identity_conflict")

    assert link.status == "conflict"
    assert link.resolution == "identity_conflict"
    assert link.candidate_identity_subject is None
