from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet

from twobrain_rec_server.cabinet.access import (
    open_invitation_delivery,
    seal_invitation_delivery,
)
from twobrain_rec_server.cabinet.rendering import render_share_invitation_accept_page


def test_invitation_delivery_payload_is_encrypted_and_round_trips() -> None:
    key = Fernet.generate_key()
    sealed = seal_invitation_delivery(
        address="recipient@example.test",
        raw_token="synthetic-one-time-token",
        key=key,
    )

    assert "recipient@example.test" not in sealed
    assert "synthetic-one-time-token" not in sealed
    assert open_invitation_delivery(sealed, key=key) == (
        "recipient@example.test",
        "synthetic-one-time-token",
    )


def test_logged_out_invitation_shows_safe_preview_without_bearer_in_login_target(client) -> None:
    response = client.get(
        "/share-invitations/synthetic-token?workspace_id="
        "20000000-0000-0000-0000-000000000001",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert "synthetic-token" not in response.text
    assert "/sign-up?" not in response.text


def test_postal_delivery_commits_at_most_once_fence_before_network_egress() -> None:
    source = Path(
        "src/twobrain_rec_server/workflows/worker.py"
    ).read_text(encoding="utf-8")
    activity = source.split(
        "async def deliver_meeting_invitation_activity", 1
    )[1].split("\ndef _processing_status_for_client_error", 1)[0]

    reserved = activity.index('invitation.status = "sending"')
    committed = activity.index("await db.commit()", reserved)
    sent = activity.index("await send_meeting_invitation(", committed)
    assert reserved < committed < sent

    recovery = activity.split('if invitation.status == "sending":', 1)[1].split(
        'if invitation.status != "pending":', 1
    )[0]
    assert 'invitation.status = "outcome_unknown"' in recovery
    assert 'invitation.failure_code = "postal_delivery_outcome_unknown"' in recovery
    assert "await send_meeting_invitation(" not in recovery


def test_account_created_delivery_uses_routed_identity_context_and_commits_before_egress() -> None:
    source = Path("src/twobrain_rec_server/workflows/worker.py").read_text(encoding="utf-8")
    activity = source.split("async def send_account_created_email_activity", 1)[1].split(
        "\ndef _processing_status_for_client_error", 1
    )[0]

    assert 'organization_id = UUID(payload["organization_id"])' in activity
    assert 'context_kind="auth_bootstrap"' in activity
    assert "await apply_tenant_context(db, tenant_context)" in activity
    reserved = activity.index('invitation.account_created_email_status = "sending"')
    committed = activity.index("await db.commit()", reserved)
    sent = activity.index("await send_account_created_email(", committed)
    assert reserved < committed < sent

    recovery = activity.split('if invitation.account_created_email_status == "sending":', 1)[1].split(
        'if invitation.account_created_email_status != "pending":', 1
    )[0]
    assert 'status="outcome_unknown"' in recovery
    assert "await send_account_created_email(" not in recovery


def test_invitation_acceptance_uses_a_separate_grant_token_and_safe_onboarding_copy() -> None:
    source = Path("src/twobrain_rec_server/cabinet/access.py").read_text(encoding="utf-8")
    acceptance = source.split("async def accept_share_invitation", 1)[1].split(
        "async def share_invitation_preview", 1
    )[0]
    assert "grant_raw_token = secrets.token_urlsafe(32)" in acceptance
    assert "grant.share_token_hash = hash_share_token(grant_raw_token)" in acceptance
    assert "invitation.grant_token_ciphertext = seal_invitation_delivery(" in acceptance
    assert 'invitation.status == "accepted"' in acceptance
    assert "grant.share_token_hash = invitation.token_hash" not in acceptance
    assert '"recipient_address_hash": invitation.normalized_address_hash' in acceptance

    rendered = render_share_invitation_accept_page(
        share_token="synthetic-token",
        workspace_id="20000000-0000-0000-0000-000000000001",
        csrf_token="synthetic-csrf",
        meeting_title="Планирование релиза",
        meeting_occurred_at=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
        meeting_duration_seconds=900,
        invitation_expires_at=datetime(2026, 7, 30, 10, 0, tzinfo=UTC),
        magic_action="/share-invitations/continue/magic?workspace_id=synthetic-workspace",
        magic_state="synthetic-continuation-state",
        magic_csrf_token="synthetic-magic-csrf-token",
        auto_accept=True,
    )
    assert "Открываем итоги" in rendered
    assert "Открыть итоги" in rendered
    assert "data-share-invitation-auto-accept-form" in rendered
    assert "Планирование релиза" not in rendered
    assert "Сведения о встрече" not in rendered
    assert "Создать аккаунт GRAF" not in rendered
    assert "транскрипт" not in rendered.lower()
    assert "audio" not in rendered.lower()


def test_magic_link_flushes_email_audit_before_switching_workspace() -> None:
    browser_source = Path(
        "src/twobrain_rec_server/cabinet/web_routes/browser.py"
    ).read_text(encoding="utf-8")
    magic_link = browser_source.split(
        "async def share_invitation_magic_link", 1
    )[1].split(
        '@router.get("/share-invitations/{share_token}"', 1
    )[0]
    audit_offset = magic_link.index("await _record_email_login_audit(")
    after_audit = magic_link[audit_offset:]
    flush_offset = after_audit.index("await session.flush()")
    context_switch_offset = after_audit.index("await apply_tenant_context(")

    assert flush_offset < context_switch_offset
    assert "no_autoflush" not in after_audit

    rls_migration = Path(
        "src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
    ).read_text(encoding="utf-8")
    assert '"auth_audit_events":' in rls_migration
    assert "workspace_id = rec_current_workspace_id()" in rls_migration


def test_invitation_notification_failure_stays_after_commit_and_bounded() -> None:
    browser_source = Path(
        "src/twobrain_rec_server/cabinet/web_routes/browser.py"
    ).read_text(encoding="utf-8")
    magic_link = browser_source.split(
        "async def share_invitation_magic_link", 1
    )[1].split(
        '@router.get("/share-invitations/{share_token}"', 1
    )[0]
    committed = magic_link.index("await session.commit()")
    notification = magic_link.index("await _dispatch_account_created_email(", committed)
    assert committed < notification

    dispatcher = browser_source.split(
        "async def _dispatch_account_created_email", 1
    )[1].split(
        '@router.post("/share-invitations/continue/magic"', 1
    )[0]
    assert "except Exception:" in dispatcher
    assert "Access is already committed" in dispatcher


def test_full_invitation_contract_exposes_recording_package_without_workspace_membership() -> None:
    browser_source = Path("src/twobrain_rec_server/cabinet/web_routes/browser.py").read_text(
        encoding="utf-8"
    )
    api_source = Path("src/twobrain_rec_server/api/cabinet.py").read_text(encoding="utf-8")
    rendered = render_share_invitation_accept_page(
        share_token="synthetic-token",
        workspace_id="20000000-0000-0000-0000-000000000001",
        csrf_token="synthetic-csrf",
        meeting_title="Планирование релиза",
        meeting_occurred_at=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
        meeting_duration_seconds=900,
        invitation_expires_at=datetime(2026, 7, 30, 10, 0, tzinfo=UTC),
        content_scope="full_meeting",
        magic_action="/share-invitations/continue/magic?workspace_id=synthetic-workspace",
        magic_state="synthetic-continuation-state",
        magic_csrf_token="synthetic-magic-csrf-token",
        auto_accept=True,
    )

    assert "Открываем запись" in rendered
    assert "Открыть запись" in rendered
    assert "data-share-invitation-auto-accept-form" in rendered
    assert "Планирование релиза" not in rendered
    assert "Сведения о встрече" not in rendered
    assert "Открыть итоги" not in rendered
    assert "/shared-meetings/" in browser_source
    assert "/cabinet/shared-meetings/{meeting_id}/playback" in api_source
    assert "/cabinet/shared-meetings/{meeting_id}/downloads/{artifact_class}" in api_source
    assert "/cabinet/shared-meetings/{meeting_id}/content-exports" in api_source
    assert "_recipient_share_access_proof" in api_source
