from pathlib import Path

from twobrain_rec_server.db import models
from twobrain_rec_server.db.base import Base
from twobrain_rec_server.observability.logging import template_path

REPO_ROOT = Path(__file__).resolve().parents[4]
FRAGMENT = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_share.html"
JS = REPO_ROOT / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
LOGGING = REPO_ROOT / "apps/server/src/twobrain_rec_server/observability/logging.py"
SECURITY_MIGRATION = REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions/0035_meeting_share_security_hardening.py"


def test_share_fragment_is_meeting_bound_and_has_truthful_capability_copy() -> None:
    source = FRAGMENT.read_text(encoding="utf-8")

    assert "/api/v1/cabinet/meetings/{{ meeting_id }}/share-recipients" in source
    assert "data-share-capability-state" in source
    assert "data-share-external-disabled" in source
    assert "data-share-rotate-url" in source
    assert "data-share-dialog open" not in source
    assert "расшифровка" in source.lower()
    assert "аудио" in source.lower()


def test_share_client_keeps_external_disabled_flow_inert_and_handles_returned_url() -> None:
    source = JS.read_text(encoding="utf-8")

    assert "externalInvitationsEnabled" in source
    assert "share_invitations_disabled" in source
    assert "payload?.share_url" in source
    assert "data-share-copy-button" in source
    assert "cache: \"no-store\"" in source


def test_internal_share_notification_is_token_free_and_reports_outcome() -> None:
    source = (REPO_ROOT / "apps/server/src/twobrain_rec_server/api/cabinet.py").read_text(
        encoding="utf-8"
    )
    helper = source.split("async def _send_internal_share_notification", 1)[1].split(
        "async def get_public_share_db_session", 1
    )[0]

    assert "send_meeting_invitation" in helper
    assert "/meetings/{meeting.id}" in helper
    assert "raw_token" not in helper
    assert 'notification_status="not_attempted"' in source


def test_share_token_paths_are_redacted_and_non_indexable() -> None:
    source = LOGGING.read_text(encoding="utf-8")

    assert "SHARE_TOKEN_PATH_RE" in source
    assert "{share_token}" in source
    assert "Referrer-Policy" in source
    assert "X-Robots-Tag" in source


def test_invitation_acceptance_token_is_redacted_in_request_path() -> None:
    assert (
        template_path("/api/v1/cabinet/share-invitations/synthetic-token/accept")
        == "/api/v1/cabinet/share-invitations/{share_token}/accept"
    )


def test_share_security_persistence_is_tenant_bound_and_migration_backed() -> None:
    assert models.MeetingShareRateLimitBucket.__tablename__ == "meeting_share_rate_limit_buckets"
    table = Base.metadata.tables["meeting_share_rate_limit_buckets"]
    assert {"workspace_id", "user_id", "device_id", "action_key", "blocked_until"}.issubset(
        table.c.keys()
    )
    source = SECURITY_MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "0035_meeting_share_security"' in source
    assert "meeting_share_rate_limit_buckets_isolation" in source
    assert "continuation_nonce" in source
