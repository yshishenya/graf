from __future__ import annotations

from datetime import UTC, datetime, timedelta

from twobrain_rec_server.admin.invitations import (
    invitation_runtime_status,
    matching_invitation_contacts,
    normalize_invitation_target,
)
from twobrain_rec_server.auth.audit import ONBOARDING_AUDIT_METADATA_KEYS
from twobrain_rec_server.db.models import WorkspaceInvitation


def test_normalize_invitation_target_is_case_and_space_stable() -> None:
    assert normalize_invitation_target("  USER@Example.TEST ") == "user@example.test"
    assert normalize_invitation_target("@TelegramUser") == "@telegramuser"


def test_matching_invitation_contacts_include_provider_subject_and_safe_contacts() -> None:
    contacts = matching_invitation_contacts(
        provider_subject="Subject-123",
        provider_username="UserName",
        email="USER@example.test",
        phone="+7 999 100 20 30",
    )

    assert "subject-123" in contacts
    assert "username" in contacts
    assert "user@example.test" in contacts
    assert "+7 999 100 20 30" in contacts


def test_join_offer_audit_contract_allows_only_opaque_metadata() -> None:
    expected_metadata_keys = {
        "action",
        "invitation_id",
        "offer_id",
        "status",
        "workspace_kind",
    }
    assert expected_metadata_keys == ONBOARDING_AUDIT_METADATA_KEYS
    assert "target_contact" not in ONBOARDING_AUDIT_METADATA_KEYS


def test_invitation_runtime_status_marks_pending_expired_without_mutating_terminal_states() -> None:
    now = datetime(2026, 6, 27, tzinfo=UTC)
    pending = WorkspaceInvitation(
        target_contact="user@example.test",
        invited_role="member",
        status="pending",
        expires_at=now + timedelta(hours=1),
    )
    expired = WorkspaceInvitation(
        target_contact="old@example.test",
        invited_role="member",
        status="pending",
        expires_at=now - timedelta(seconds=1),
    )
    revoked = WorkspaceInvitation(
        target_contact="revoked@example.test",
        invited_role="member",
        status="revoked",
        expires_at=now - timedelta(days=1),
    )

    assert invitation_runtime_status(pending, now=now) == "pending"
    assert invitation_runtime_status(expired, now=now) == "expired"
    assert invitation_runtime_status(revoked, now=now) == "revoked"
