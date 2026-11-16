"""Fresh session/access fences inside isolated account admission, not HTTP/T113."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic

import pytest
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError

from tests.contract.test_result_view_admission import (
    SESSION_ID,
    _accept,
    _prepare,
    _result_principal,
    isolated_admission,  # noqa: F401
    result_period,  # noqa: F401
)
from tests.contract.test_result_visibility import _run
from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID, DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    DiarizationSegment,
    MediaRevision,
    Meeting,
    ProcessingResult,
    ProductActivationMilestone,
    RegisteredDevice,
    TranscriptSegment,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)
from twobrain_rec_server.processing.fences import lock_meeting_fence
from twobrain_rec_server.product_analytics import ingest, milestones

pytestmark = pytest.mark.usefixtures("isolated_admission", "result_period")


@pytest.mark.parametrize("broken", [
    "session_revoked", "session_replaced", "session_expired", "membership",
    "membership_missing", "binding", "binding_missing", "binding_extra",
    "device", "device_unapproved", "device_quarantined", "personal_owner", "account",
])
def test_persisted_access_revoke_after_render_refuses_before_verifier(
    postgres_seeded_database_url, broken,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        async with sessions() as db:
            if broken.startswith("session_"):
                session = await db.get(AuthSession, SESSION_ID)
                if broken != "session_expired":
                    session.status = "revoked" if broken == "session_revoked" else "replaced"
                else:
                    session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            elif broken.startswith("membership"):
                member = await db.get(WorkspaceMembership, (WORKSPACE_ID, USER_ID))
                if broken == "membership_missing":
                    await db.delete(member)
                else:
                    member.status = "revoked"
            elif broken.startswith("binding"):
                link = await db.scalar(select(AuthSessionDeviceBinding).where(
                    AuthSessionDeviceBinding.auth_session_id == SESSION_ID,
                ))
                if broken == "binding_missing":
                    await db.delete(link)
                elif broken == "binding_extra":
                    db.add(AuthSessionDeviceBinding(
                        auth_session_id=SESSION_ID, registered_device_id=DEVICE_ID, device_state="blocked",
                    ))
                else:
                    link.device_state = "blocked"
            elif broken == "personal_owner":
                workspace = await db.get(Workspace, WORKSPACE_ID)
                workspace.kind, workspace.owner_user_id = "personal", None
            elif broken == "account":
                user = await db.get(UserIdentity, USER_ID)
                user.status = "closed"
            else:
                device = await db.get(RegisteredDevice, DEVICE_ID)
                if broken == "device_unapproved":
                    device.registration_state = "pending"
                else:
                    device.status = "quarantined" if broken == "device_quarantined" else "revoked"
            await db.commit()
        called = False

        async def forbidden(db, started_at):
            nonlocal called
            called = True
            return await verify(db, started_at)

        assert not await _accept(sessions, forbidden)
        assert not called
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []

    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["deleted", "epoch", "source", "version", "text"])
def test_fresh_locked_projection_rejects_changed_source_or_body(
    postgres_seeded_database_url, broken,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        async with sessions() as db:
            meeting_id = await db.scalar(select(Meeting.id).where(Meeting.created_by_user_id == USER_ID))
            meeting = await lock_meeting_fence(db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id)
            if broken == "deleted":
                meeting.deleted_at = datetime.now(UTC)
            elif broken == "epoch":
                meeting.deletion_epoch += 1
            elif broken == "source":
                revision = await db.scalar(select(MediaRevision).where(MediaRevision.meeting_id == meeting_id))
                revision.status = "blocked"
            elif broken == "version":
                result = await db.scalar(select(ProcessingResult).where(
                    ProcessingResult.meeting_id == meeting_id,
                ).order_by(ProcessingResult.result_version.desc()))
                result.result_version += 1
            else:
                await db.execute(update(TranscriptSegment).where(
                    TranscriptSegment.meeting_id == meeting_id,
                ).values(text="Изменённое учебное содержимое"))
                await db.execute(update(DiarizationSegment).where(
                    DiarizationSegment.meeting_id == meeting_id,
                ).values(text="Изменённое учебное содержимое"))
            await db.commit()
        assert not await _accept(sessions, verify)
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("point", ["second_insert", "commit"])
def test_session_expiry_during_pair_rolls_back_all_new_rows(
    postgres_seeded_database_url, monkeypatch, point,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        original = ingest.admit_account_milestone
        validate_session = ingest.is_session_token_valid
        calls = 0
        expired = False
        checks = []

        def check_at_phase_time(session, at):
            # Move only the session clock; real work/cleanup deadlines do not move.
            phase_time = session.expires_at + timedelta(microseconds=1) if expired else at
            valid = validate_session(session, phase_time)
            checks.append((expired, valid))
            return valid

        async def admit(db, event, **kwargs):
            nonlocal calls, expired
            calls += 1
            row = await original(db, event, **kwargs)
            if calls == (1 if point == "second_insert" else 2):
                assert await db.get(AuthSession, SESSION_ID) is not None
                expired = True
            return row

        monkeypatch.setattr(ingest, "is_session_token_valid", check_at_phase_time)
        monkeypatch.setattr(milestones, "admit_account_milestone", admit)
        began = monotonic()
        assert not await _accept(sessions, verify)
        assert monotonic() - began < 2.1
        assert calls == 2 and expired
        assert (False, True) in checks and checks[-1] == (True, False)
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


def test_device_bootstrap_keeps_empty_binding_set_fenced(
    postgres_seeded_database_url,
):
    async def scenario(sessions):
        await _prepare(sessions)
        async with sessions() as db:
            await db.execute(delete(AuthSessionDeviceBinding).where(
                AuthSessionDeviceBinding.auth_session_id == SESSION_ID,
            ))
            await db.execute(update(AuthSession).where(AuthSession.id == SESSION_ID).values(device_id=None))
            await db.commit()
        service = ingest.ProductAnalyticsIngestService(Settings(
            product_analytics_enabled=True, web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
        ))
        actor = replace(_result_principal(), session_device_id=None)
        blocked = []
        async def verify(db, started_at):
            async with sessions() as writer_db:
                await writer_db.execute(text("SET LOCAL lock_timeout = '50ms'"))
                writer_db.add(AuthSessionDeviceBinding(
                    auth_session_id=SESSION_ID, registered_device_id=DEVICE_ID, device_state="trusted",
                ))
                try:
                    await writer_db.flush()
                except DBAPIError as error:
                    blocked.append(error.orig.sqlstate)
                await writer_db.rollback()
            return None
        assert not await service.admit_result_view(
            principal=actor, workspace_id=WORKSPACE_ID, sessionmaker=sessions,
            verify_view=verify, surface="cabinet_web",
        )
        assert blocked == ["55P03"]
        async with sessions() as db:
            db.add(AuthSessionDeviceBinding(
                auth_session_id=SESSION_ID, registered_device_id=DEVICE_ID, device_state="trusted",
            ))
            await db.commit()
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("locked", ["session", "workspace", "member", "binding", "device", "meeting"])
def test_busy_access_or_source_fence_refuses_within_budget(
    postgres_seeded_database_url, locked,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        targets = {
            "session": select(AuthSession).where(AuthSession.id == SESSION_ID),
            "workspace": select(Workspace).where(Workspace.id == WORKSPACE_ID),
            "member": select(WorkspaceMembership).where(WorkspaceMembership.user_id == USER_ID),
            "binding": select(AuthSessionDeviceBinding).where(AuthSessionDeviceBinding.auth_session_id == SESSION_ID),
            "device": select(RegisteredDevice).where(RegisteredDevice.id == DEVICE_ID),
            "meeting": select(Meeting).where(Meeting.created_by_user_id == USER_ID),
        }
        async with sessions() as blocker:
            assert await blocker.scalar(targets[locked].with_for_update()) is not None
            began = monotonic()
            assert not await _accept(sessions, verify)
            assert monotonic() - began < 1
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("writer", ["session_revoke", "binding_insert", "meeting_delete"])
def test_analytics_first_holds_real_writer_conflict_through_commit(
    postgres_seeded_database_url, monkeypatch, writer,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        original = ingest.admit_account_milestone
        blocked = False

        async def mutate(db):
            if writer == "session_revoke":
                await db.execute(update(AuthSession).where(AuthSession.id == SESSION_ID).values(status="revoked"))
            elif writer == "binding_insert":
                db.add(AuthSessionDeviceBinding(
                    auth_session_id=SESSION_ID, registered_device_id=DEVICE_ID, device_state="blocked",
                ))
                await db.flush()
            else:
                meeting_id = await db.scalar(select(Meeting.id).where(Meeting.created_by_user_id == USER_ID))
                meeting = await lock_meeting_fence(db, workspace_id=WORKSPACE_ID, meeting_id=meeting_id)
                meeting.deleted_at = datetime.now(UTC)
                await db.flush()

        async def admit(db, event, **kwargs):
            nonlocal blocked
            row = await original(db, event, **kwargs)
            if event.event_name == "first_value_session_completed":
                async with sessions() as writer_db:
                    await writer_db.execute(text("SET LOCAL lock_timeout = '50ms'"))
                    with pytest.raises(DBAPIError) as error:
                        await mutate(writer_db)
                    assert error.value.orig.sqlstate == "55P03"
                    await writer_db.rollback()
                blocked = True
            return row

        monkeypatch.setattr(milestones, "admit_account_milestone", admit)
        assert await _accept(sessions, verify)
        assert blocked
        async with sessions() as db:
            assert len(list(await db.scalars(select(ProductActivationMilestone)))) == 2
            await mutate(db)
            await db.commit()
        assert not await _accept(sessions, verify)
    _run(postgres_seeded_database_url, scenario)


def test_limited_application_role_preserves_tenant_scope_and_can_admit(
    postgres_seeded_database_url,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        async with sessions() as db:
            await db.execute(text("CREATE ROLE graf_t112_access_test NOLOGIN NOSUPERUSER NOBYPASSRLS"))
            await db.execute(text("GRANT USAGE ON SCHEMA public TO graf_t112_access_test"))
            await db.execute(text("GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO graf_t112_access_test"))
            await db.commit()

        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
        limited = create_async_engine(postgres_seeded_database_url, connect_args={
            "server_settings": {"role": "graf_t112_access_test"},
        })
        limited_sessions = async_sessionmaker(limited, expire_on_commit=False)
        try:
            async with limited.connect() as probe:
                assert await probe.scalar(text("SELECT current_user")) == "graf_t112_access_test"
                assert not await probe.scalar(text("SELECT rolbypassrls OR rolsuper FROM pg_roles WHERE rolname = current_user"))
            assert await _accept(limited_sessions, verify)
            async with sessions() as db:
                assert len(list(await db.scalars(select(ProductActivationMilestone)))) == 2
        finally:
            await limited.dispose()
            async with sessions() as db:
                await db.execute(text("DROP OWNED BY graf_t112_access_test"))
                await db.execute(text("DROP ROLE graf_t112_access_test"))
                await db.commit()
    _run(postgres_seeded_database_url, scenario)
