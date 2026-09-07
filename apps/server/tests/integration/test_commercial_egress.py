"""Commercial restrictions at real HTTP egress boundaries under the actual app role."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import SAFE_TRANSCRIPT_TEXT, seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_retained_playback_m4a,
    add_workspace_user,
    audit_events,
    auth_headers_for,
    grant_meeting_to_user,
    set_artifact_policy,
)
from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
from tests.integration.test_system_admin_billing import _managed_payment
from twobrain_rec_server.billing.admin_grants import create_adjustment, revoke_adjustment
from twobrain_rec_server.cabinet import egress

pytestmark = pytest.mark.strict_rls


@pytest.fixture
def commercial(client, monkeypatch):
    seeds = seed_cabinet_meetings(client)
    add_retained_playback_m4a(client, seeds.ready_id)
    add_workspace_user(client)
    grant_meeting_to_user(client, seeds.ready_id)
    set_artifact_policy(client, seeds.ready_id, audio_download="allowed",
                        transcript_download="allowed", package_export="allowed")
    role = _exact_app_role_engine(str(client.app.state.settings.database_url))
    engine = client.portal.call(role.__aenter__)

    async def check_role():
        async with engine.connect() as connection:
            assert await connection.scalar(text("select session_user")) == "twobrain_rec_app"
            assert not await connection.scalar(text(
                "select rolsuper or rolbypassrls or rolinherit from pg_roles where rolname=session_user"))
    client.portal.call(check_role)
    monkeypatch.setattr(client.app.state, "db_sessionmaker", async_sessionmaker(engine, expire_on_commit=False))
    try:
        yield client, seeds.ready_id
    finally:
        client.portal.call(role.__aexit__, None, None, None)


async def _deny(client, feature, *, subject=None):
    now = datetime.now(UTC)
    async with client.app_state["sessionmaker"]() as db:
        await db.execute(text("set local lock_timeout='3s'"))
        row = await create_adjustment(db, workspace_id=WORKSPACE_ID, subject_user_id=subject,
            kind="deny", feature_key=feature, value=False, unit="boolean",
            starts_at=now-timedelta(seconds=1), ends_at=now+timedelta(days=1),
            source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic egress restriction")
        await db.commit()
        return row.id


@pytest.mark.parametrize("subject", [None, USER_ID])
def test_download_deny_revoke_and_playback_independence(commercial, subject):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"
    assert client.get(path+"/downloads/audio", headers=auth_headers()).status_code == 200
    adjustment = client.portal.call(lambda: _deny(client, "audio_download", subject=subject))
    denied = client.get(path+"/downloads/audio", headers=auth_headers())
    assert denied.status_code == 409 and "content-disposition" not in denied.headers
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_audio_download_denied"
    assert client.get(path+"/playback", headers=auth_headers()).status_code == 200
    assert client.get(path+"/downloads/transcript", headers=auth_headers()).status_code == 200

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            await revoke_adjustment(db, workspace_id=WORKSPACE_ID, adjustment_id=adjustment,
                source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic egress restore")
            await db.commit()
    client.portal.call(revoke)
    assert client.get(path+"/downloads/audio", headers=auth_headers()).status_code == 200


def test_recipient_personal_deny_is_visible_in_authenticated_shared_context(commercial):
    client, meeting = commercial
    path = f"/api/v1/cabinet/shared-meetings/{meeting}"
    params = {"workspace_id":str(WORKSPACE_ID)}
    client.portal.call(lambda: _deny(client, "content_export", subject=SHARED_USER_ID))
    capability = client.get(path+"/content-exports", headers=auth_headers_for(), params=params)
    assert capability.status_code == 200, capability.text
    assert capability.json()["transcript"]["state"] == "denied"
    assert capability.json()["formats"]["transcript"] == []
    denied = client.get(path+"/downloads/transcript", headers=auth_headers_for(), params=params)
    assert denied.status_code == 409 and SAFE_TRANSCRIPT_TEXT not in denied.text
    # Another member's restriction must not leak onto the owner.
    own = client.get(f"/api/v1/cabinet/meetings/{meeting}/downloads/transcript", headers=auth_headers())
    assert own.status_code == 200


def test_content_deny_blocks_prepared_package_and_direct_post(commercial):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}"
    capability = client.get(path+"/content-exports", headers=auth_headers()).json()
    created = client.post(path+"/exports", headers=auth_headers(), json={"artifact_classes":["transcript"]})
    assert created.status_code == 202, created.text
    export_path = path+f"/exports/{created.json()['export_id']}/download"
    assert client.get(export_path, headers=auth_headers()).status_code == 200
    client.portal.call(lambda: _deny(client, "content_export"))
    for response in (
        client.get(export_path, headers=auth_headers()),
        client.post(path+"/content-exports", headers=auth_headers(), json={"content_scope":"transcript",
            "format":"txt", "processing_result_id":capability["processing_result_id"]}),
    ):
        assert response.status_code in {403,409}, response.text
        assert "content-disposition" not in response.headers and SAFE_TRANSCRIPT_TEXT not in response.text


def test_deny_during_render_wins_final_egress_check(commercial, monkeypatch):
    client, meeting = commercial
    path = f"/api/v1/cabinet/meetings/{meeting}/content-exports"
    capability = client.get(path, headers=auth_headers()).json()
    original = egress.build_export_snapshot

    async def build_and_deny(*args, **kwargs):
        snapshot = await original(*args, **kwargs)
        await _deny(client, "content_export")
        return snapshot
    monkeypatch.setattr(egress, "build_export_snapshot", build_and_deny)
    denied = client.post(path, headers=auth_headers(), json={"content_scope":"transcript",
        "format":"txt", "processing_result_id":capability["processing_result_id"]})
    assert denied.status_code == 403, denied.text
    assert "content-disposition" not in denied.headers and SAFE_TRANSCRIPT_TEXT not in denied.text
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_export_denied"


def test_managed_formats_apply_to_discovery_direct_post_and_legacy_download(commercial):
    client, meeting = commercial
    now = datetime.now(UTC)

    async def gift():
        async with client.app_state["sessionmaker"]() as db:
            version, _, _, _ = await _managed_payment(db)
            await create_adjustment(db, workspace_id=WORKSPACE_ID, kind="plan_interval",
                plan_version_id=version.id, plan_mode="overlay", starts_at=now-timedelta(seconds=1),
                ends_at=now+timedelta(days=1), source_kind="migration",
                source_ref=f"synthetic:{uuid4()}", reason="Synthetic export plan")
            await db.commit()
    client.portal.call(gift)
    path = f"/api/v1/cabinet/meetings/{meeting}"
    capability = client.get(path+"/content-exports", headers=auth_headers()).json()
    assert capability["formats"]["transcript"] == ["txt","md"]
    for format, status in (("txt",200),("csv",409),("json",409)):
        exported = client.post(path+"/content-exports", headers=auth_headers(), json={
            "content_scope":"transcript", "format":format,
            "processing_result_id":capability["processing_result_id"]})
        assert exported.status_code == status, exported.text
    legacy = client.post(path+"/exports", headers=auth_headers(), json={"artifact_classes":["transcript"]})
    assert legacy.status_code == 409  # Its manifest is JSON, outside the exact plan formats.


def test_shared_outsider_sees_owner_workspace_restrictions(commercial):
    from tests.fixtures.cabinet import (
        FOREIGN_DEVICE_ID,
        FOREIGN_ORG_ID,
        FOREIGN_USER_ID,
        FOREIGN_WORKSPACE_ID,
    )

    client, meeting = commercial
    from sqlalchemy import select

    from twobrain_rec_server.cabinet.access import hash_invitation_address
    from twobrain_rec_server.db.models import ExternalIdentity, MeetingShareGrant

    grant_meeting_to_user(client, meeting, user_id=FOREIGN_USER_ID)

    async def accepted_invitation():
        async with client.app_state["sessionmaker"]() as db:
            email = "synthetic-recipient@example.invalid"
            db.add(ExternalIdentity(user_id=FOREIGN_USER_ID, provider="email",
                provider_subject=email, email=email, is_verified=True, is_active=True))
            grant = await db.scalar(select(MeetingShareGrant).where(
                MeetingShareGrant.meeting_id == meeting, MeetingShareGrant.audience_id == FOREIGN_USER_ID))
            grant.metadata_json = {"source":"accepted_external_invitation",
                "recipient_address_hash":hash_invitation_address(email)}
            await db.commit()
    client.portal.call(accepted_invitation)
    headers = auth_headers_for(user_id=FOREIGN_USER_ID, device_id=FOREIGN_DEVICE_ID,
        workspace_id=FOREIGN_WORKSPACE_ID, organization_id=FOREIGN_ORG_ID)
    path = f"/api/v1/cabinet/shared-meetings/{meeting}/downloads/transcript"
    params = {"workspace_id":str(WORKSPACE_ID)}
    assert client.get(path, headers=headers, params=params).status_code == 200
    client.portal.call(lambda: _deny(client, "content_export"))
    denied = client.get(path, headers=headers, params=params)
    assert denied.status_code == 409 and SAFE_TRANSCRIPT_TEXT not in denied.text


def test_egress_workspace_fence_serializes_assignment_before_bytes(commercial):
    import asyncio

    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    client, _ = commercial

    async def check():
        async with client.app.state.db_sessionmaker() as db:
            await apply_tenant_context(db, TenantDatabaseContext(
                organization_id=uuid4(), workspace_id=WORKSPACE_ID, user_id=USER_ID))
            await egress._lock_commercial_workspace(db, WORKSPACE_ID)
            task = asyncio.create_task(_deny(client, "audio_download"))
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.2)
                await db.commit()
                assert await asyncio.wait_for(task, timeout=5)
            finally:
                await db.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    client.portal.call(check)


def test_scheduled_restriction_starting_during_audio_materialization_blocks_bytes(commercial, monkeypatch):
    client, meeting = commercial
    now = datetime.now(UTC)

    async def schedule():
        async with client.app_state["sessionmaker"]() as db:
            await create_adjustment(db, workspace_id=WORKSPACE_ID,
                kind="deny", feature_key="audio_download", value=False, unit="boolean",
                starts_at=now+timedelta(minutes=1), ends_at=now+timedelta(days=1),
                source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic scheduled restriction")
            await db.commit()
    client.portal.call(schedule)
    original = egress._materialize_storage_stream

    class AfterRestrictionStart(datetime):
        @classmethod
        def now(cls, tz=None):
            return (now+timedelta(minutes=2)).astimezone(tz)

    async def materialize(*args, **kwargs):
        body = await original(*args, **kwargs)
        monkeypatch.setattr(egress, "datetime", AfterRestrictionStart)
        return body
    monkeypatch.setattr(egress, "_materialize_storage_stream", materialize)
    denied = client.get(f"/api/v1/cabinet/meetings/{meeting}/downloads/audio", headers=auth_headers())
    assert denied.status_code == 409 and "content-disposition" not in denied.headers
    assert audit_events(client, meeting)[-1].policy_reason == "commercial_audio_download_denied"
