import asyncio
import threading
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

from twobrain_rec_server.auth.callbacks import (
    _user_by_external_identity,
    _verify_provider_callback,
)
from twobrain_rec_server.auth.provider_links import (
    RECOVERY_CAPABLE_PROVIDERS,
    _identity_matches_session,
    expire_if_needed,
    recovery_safe_unlink_allowed,
    scrub_candidate,
    store_verified_candidate,
)
from twobrain_rec_server.auth.providers.base import ProviderCredentials, ProviderIdentity
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthSession, ExternalIdentity, WorkspaceProviderLinkState


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


def test_unlink_guard_preserves_at_least_one_recovery_path() -> None:
    assert recovery_safe_unlink_allowed(verified_identity_count=2, target_is_verified=True)
    assert recovery_safe_unlink_allowed(
        verified_identity_count=1,
        target_is_verified=True,
        has_independent_recovery_path=True,
    )
    assert not recovery_safe_unlink_allowed(verified_identity_count=1, target_is_verified=True)
    assert not recovery_safe_unlink_allowed(verified_identity_count=2, target_is_verified=False)


def test_provider_link_catalog_excludes_non_login_telegram_identity() -> None:
    assert {"email", "email_magic_link", "yandex", "vk"} <= RECOVERY_CAPABLE_PROVIDERS
    assert "telegram" not in RECOVERY_CAPABLE_PROVIDERS


def test_email_session_fingerprint_selects_exact_identity_after_merge() -> None:
    workspace_id = uuid4()
    selected_email = "selected@example.test"
    session = AuthSession(
        provider="email",
        claims_fingerprint=hash_token(f"email:{selected_email}:{workspace_id}"),
    )
    selected = ExternalIdentity(
        provider="email",
        provider_subject=selected_email,
        email=selected_email,
    )
    other = ExternalIdentity(
        provider="email",
        provider_subject="other@example.test",
        email="other@example.test",
    )

    assert _identity_matches_session(session, selected, workspace_ids={workspace_id})
    assert not _identity_matches_session(session, other, workspace_ids={workspace_id})


async def test_unlinked_external_identity_is_excluded_from_provider_login_lookup() -> None:
    db = AsyncMock()

    assert (
        await _user_by_external_identity(
            db,
            organization_id=uuid4(),
            provider="yandex",
            provider_subject="inactive-subject",
        )
        is None
    )
    query = str(db.scalar.await_args.args[0])
    assert "external_identities.is_active" in query


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


def test_sync_provider_callback_verification_does_not_block_event_loop(monkeypatch) -> None:
    release = threading.Event()

    class BlockingAdapter:
        def verify_callback(self, *args, **kwargs) -> ProviderIdentity:
            assert release.wait(timeout=0.5)
            return ProviderIdentity(provider="yandex", provider_subject="threaded-subject")

    monkeypatch.setattr(
        "twobrain_rec_server.auth.callbacks.get_provider_adapter",
        lambda provider: BlockingAdapter(),
    )

    async def exercise() -> tuple[ProviderIdentity, float]:
        loop = asyncio.get_running_loop()
        loop.call_later(0.01, release.set)
        started_at = loop.time()
        identity = await _verify_provider_callback(
            provider="yandex",
            query={"state": "synthetic-state", "code": "synthetic-code"},
            state_nonce="synthetic-state",
            provider_credentials=ProviderCredentials(
                client_id="synthetic-client",
                redirect_uri="https://example.test/callback",
            ),
            provider_http_client=object(),  # type: ignore[arg-type]
            now=datetime.now(UTC),
        )
        return identity, loop.time() - started_at

    identity, elapsed = asyncio.run(exercise())

    assert identity.provider_subject == "threaded-subject"
    assert elapsed < 0.2
