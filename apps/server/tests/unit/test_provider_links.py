from datetime import UTC, datetime, timedelta
from uuid import uuid4

from twobrain_rec_server.auth.provider_links import (
    expire_if_needed,
    scrub_candidate,
    store_verified_candidate,
)
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


async def test_verified_candidate_is_stored_only_after_provider_callback() -> None:
    class Session:
        def __init__(self) -> None:
            self.added: list[object] = []

        def add(self, value: object) -> None:
            self.added.append(value)

    now = datetime.now(UTC)
    link = WorkspaceProviderLinkState(
        id=uuid4(),
        workspace_id=uuid4(),
        initiating_user_id=uuid4(),
        source_provider_identity_id=uuid4(),
        candidate_provider="vk",
        status="initiated",
        expires_at=now + timedelta(minutes=15),
    )
    session = Session()

    await store_verified_candidate(
        session,  # type: ignore[arg-type]
        link=link,
        provider="vk",
        provider_subject="verified-subject",
        email="verified@example.test",
        phone=None,
        display_name="Verified",
        now=now,
    )

    assert link.status == "callback_verified"
    assert link.candidate_identity_subject == "verified-subject"
    assert link.candidate_email == "verified@example.test"
    assert len(session.added) == 1
