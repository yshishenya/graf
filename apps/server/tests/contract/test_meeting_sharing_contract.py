import asyncio
import subprocess
import urllib.request
from pathlib import Path

import httpx
import pytest
import urllib3
from jinja2 import Template
from sqlalchemy import select
from temporalio.client import Client

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.cabinet import (
    FOREIGN_DEVICE_ID,
    FOREIGN_ORG_ID,
    FOREIGN_USER_ID,
    FOREIGN_WORKSPACE_ID,
    _create_foreign_meeting,
    create_ready_meeting,
)
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    auth_headers_for,
    set_meeting_deletion_state,
)
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

    assert 'data-meeting-id="{{ meeting_id }}"' in source
    assert "data-summary-share-dialog" in source
    assert "data-summary-share-email-form" in source
    assert "data-summary-share-recipients" in source
    assert 'data-summary-link-action="rotate"' in source
    assert "data-share-existing-role" not in source
    assert "data-share-comment-role" not in source
    assert "data-share-dialog open" not in source
    assert "расшифровка" in source.lower()
    assert "Запись и расшифровка останутся закрыты" in source


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


@pytest.mark.parametrize("route,key", [
    ("summary-sharing/recipients", "recipients"),
    ("share-recipients", "items"),
])
def test_recipient_lookup_never_imports_contacts_or_grants_access(client, monkeypatch, route, key):
    meeting_id = create_ready_meeting(client)
    foreign_meeting_id = _create_foreign_meeting(client)
    add_workspace_user(client, display_name="Synthetic Teammate")

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            for user_id, email in [
                (SHARED_USER_ID, "teammate@example.test"),
                (FOREIGN_USER_ID, "teammate-foreign@example.test"),
            ]:
                db.add(models.ExternalIdentity(
                    user_id=user_id, provider="synthetic", provider_subject=str(user_id),
                    email=email, is_verified=True,
                ))
            await db.commit()

    asyncio.run(seed())
    # Compare rows, not only counts: a hidden refresh or consent update is also a defect.
    # The intentional recipient-search rate-limit bucket is outside this snapshot.
    table_names = {
        "meetings", "user_identities", "external_identities", "workspace_memberships",
        "workspace_provider_link_states", "workspace_consent_copy", "workspace_auth_policies",
        "meeting_share_grants", "meeting_share_invitations", "meeting_egress_audit_events",
        "published_meeting_summaries", "summary_delivery_batches", "summary_recipient_deliveries",
        "external_calendars", "recording_calendar_context_links", "server_notifications",
    } | {name for name in Base.metadata.tables if name.startswith("calendar_")}

    async def snapshot():
        async with client.app_state["sessionmaker"]() as db:
            return {
                name: (await db.execute(select(Base.metadata.tables[name]).order_by(
                    *Base.metadata.tables[name].primary_key.columns
                ))).all()
                for name in sorted(table_names)
            }

    calls = []

    def unexpected(*args, **kwargs):
        calls.append("provider_or_delivery")
        raise AssertionError("Recipient lookup must not call providers or start delivery")

    async def unexpected_async(*args, **kwargs):
        unexpected()

    monkeypatch.setattr(httpx.AsyncClient, "send", unexpected_async)
    monkeypatch.setattr(httpx.HTTPTransport, "handle_request", unexpected)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", unexpected)
    monkeypatch.setattr(urllib3.connectionpool.HTTPConnectionPool, "urlopen", unexpected)
    monkeypatch.setattr(Client, "connect", unexpected_async)
    monkeypatch.setattr(Client, "start_workflow", unexpected_async)

    before = asyncio.run(snapshot())
    assert before["calendar_sources"] == []  # No permission or provider connection.
    url = f"/api/v1/cabinet/meetings/{meeting_id}/{route}"
    found = client.get(url, headers=auth_headers(), params={"query": "teammate"})
    assert found.status_code == 200, found.text
    assert [row["user_id"] for row in found.json()[key]] == [str(SHARED_USER_ID)]
    assert found.json()[key][0]["source"] == "workspace"
    unknown = client.get(url, headers=auth_headers(), params={"query": "unknown@example.test"})
    assert unknown.status_code == 200
    assert unknown.json()[key] == []
    foreign_headers = auth_headers_for(
        user_id=FOREIGN_USER_ID, device_id=FOREIGN_DEVICE_ID,
        workspace_id=FOREIGN_WORKSPACE_ID, organization_id=FOREIGN_ORG_ID,
    )
    for denied_url, headers in [
        (url, auth_headers_for()),
        (url, foreign_headers),
        (f"/api/v1/cabinet/meetings/{foreign_meeting_id}/{route}", auth_headers()),
    ]:
        denied = client.get(denied_url, headers=headers, params={"query": "teammate"})
        assert denied.status_code == 404, denied.text
        assert denied.json()["code"] == "meeting_not_found"
    assert asyncio.run(snapshot()) == before

    set_meeting_deletion_state(client, meeting_id, "deleting")
    before_deleting = asyncio.run(snapshot())
    deleted = client.get(url, headers=auth_headers(), params={"query": "teammate"})
    assert deleted.status_code == 404
    assert deleted.json()["code"] == "meeting_not_found"
    assert asyncio.run(snapshot()) == before_deleting
    assert calls == []


@pytest.mark.browser
def test_browser_recipient_selection_never_requests_contacts_or_sends(tmp_path):
    page = tmp_path / "share.html"
    page.write_text(Template(FRAGMENT.read_text(encoding="utf-8")).render(
        meeting_id="synthetic-meeting", share_workspace_id="synthetic-workspace",
    ), encoding="utf-8")
    script = Path(__file__).parents[1] / "browser/share-recipient-privacy.test.cjs"
    result = subprocess.run(
        ["node", str(script), str(page)], capture_output=True, text=True, timeout=90,
    )
    assert result.returncode == 0, result.stdout + result.stderr
