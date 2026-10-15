"""Synthetic regression coverage for explicit, revocable summary automation."""

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.cabinet.summary_autosend import (
    evaluate_google_roster,
    get_preferences,
    update_preferences,
)
from twobrain_rec_server.db.models.summary_autosend import SummarySharingPreference

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def _prepare_auto(client, tmp_path, *, series=False):
    from cryptography.fernet import Fernet

    from tests.fakes.auth_contexts import tenant_scope
    from tests.fixtures.cabinet import create_ready_meeting
    from tests.fixtures.cabinet_access import SHARED_USER_ID, add_workspace_user
    from twobrain_rec_server.calendar.google import _normalize_google_event
    from twobrain_rec_server.calendar.normalize import normalize_calendar_event
    from twobrain_rec_server.calendar.sync import upsert_event_snapshot
    from twobrain_rec_server.db.models import (
        CalendarSource,
        ExternalCalendar,
        ExternalIdentity,
        RecordingCalendarContextLink,
    )

    add_workspace_user(client)
    key = tmp_path / "synthetic-auto-key"
    key.write_bytes(Fernet.generate_key())
    settings = client.app.state.settings
    settings.credential_encryption_key_file = key
    settings.share_external_invitations_enabled = True
    settings.public_base_url = "https://graf.example.test"
    meeting_id = create_ready_meeting(client)
    now = datetime.now(UTC)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            for uid, email in (
                (USER_ID, "owner@example.test"),
                (SHARED_USER_ID, "member@example.test"),
            ):
                db.add(
                    ExternalIdentity(
                        user_id=uid,
                        provider="email",
                        provider_subject=str(uid),
                        email=email,
                        is_active=True,
                        is_verified=True,
                    )
                )
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="google_calendar",
                auth_mode="oauth",
                credential_state="active",
                connection_state="active",
                sync_state="synced",
                last_successful_sync_at=now,
            )
            db.add(source)
            await db.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="primary",
                display_label="Synthetic",
                visibility="available",
                selected=True,
            )
            db.add(calendar)
            await db.flush()
            start = now + timedelta(minutes=1) if series else now - timedelta(minutes=1)
            payload = {
                "id": "synthetic-instance",
                "iCalUID": "synthetic-auto@example.test",
                "status": "confirmed",
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": (start + timedelta(minutes=1)).isoformat()},
                "organizer": {"email": "owner@example.test", "self": True},
                "attendees": [{"email": "member@example.test", "responseStatus": "accepted"}],
            }
            if series:
                payload |= {
                    "recurringEventId": "synthetic-series",
                    "originalStartTime": {"dateTime": start.isoformat()},
                }
            snapshot = await upsert_event_snapshot(
                db,
                tenant_scope=tenant_scope(),
                source=source,
                calendar=calendar,
                event=normalize_calendar_event(
                    _normalize_google_event(payload, calendar_id="primary")
                ),
                credential_encryption_key=key.read_bytes(),
            )
            link = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            link.calendar_event_snapshot_id = snapshot.id
            link.context_state = "matched_user"
            await db.commit()
            return snapshot.id, payload

    event_id, payload = asyncio.run(seed())
    return meeting_id, event_id, payload, settings, now, SHARED_USER_ID


async def _publish_ready(db, meeting_id, ready_at):
    from twobrain_rec_server.db.models import (
        MeetingOutcomeSet,
        MeetingSummarySlot,
        ProcessingResult,
    )

    result = await db.scalar(
        select(ProcessingResult).where(ProcessingResult.meeting_id == meeting_id)
    )
    outcome = MeetingOutcomeSet(
        workspace_id=WORKSPACE_ID,
        meeting_id=meeting_id,
        media_revision_id=result.media_revision_id,
        processing_result_id=result.id,
        template_key="summary",
        generator_version="synthetic-auto-v1",
        status="available",
        summary_state="available",
        source_result_hash=result.source_result_hash,
        revision_state="accepted",
        accepted_at=ready_at,
        lifecycle_state="active",
    )
    db.add(outcome)
    await db.flush()
    db.add(
        MeetingSummarySlot(
            workspace_id=WORKSPACE_ID,
            meeting_id=meeting_id,
            template_key="summary",
            current_outcome_set_id=outcome.id,
            current_binding_class="verified_complete",
        )
    )
    await db.flush()
    return outcome


def test_explicit_rule_creates_one_delayed_batch_and_no_access(client, tmp_path, monkeypatch):
    from twobrain_rec_server.cabinet.summary_autosend import (
        guard_auto_batch,
        reconcile_meeting_autosend,
        save_rule,
    )
    from twobrain_rec_server.db.models.summary_sharing import (
        SummaryDeliveryBatch,
        SummaryRecipientDelivery,
    )

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)
    monkeypatch.setattr("twobrain_rec_server.config.get_settings", lambda: settings)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            state = await save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=now,
            )
            assert state["state"] == "waiting_summary" and state["batch"] is None
            await _publish_ready(db, meeting_id, now + timedelta(seconds=1))
            batch = await reconcile_meeting_autosend(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                now=now + timedelta(seconds=2),
            )
            assert batch.scheduled_at == now + timedelta(minutes=5, seconds=1)
            assert batch.deadline_at == now + timedelta(hours=24, seconds=1)
            again = await reconcile_meeting_autosend(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                now=now + timedelta(seconds=3),
            )
            assert again.id == batch.id
            rows = (
                await db.scalars(
                    select(SummaryRecipientDelivery).where(
                        SummaryRecipientDelivery.batch_id == batch.id
                    )
                )
            ).all()
            assert len(rows) == 1 and rows[0].invitation_id is None and rows[0].grant_id is None
            assert not (
                await guard_auto_batch(
                    db, batch=batch, settings=settings, now=now + timedelta(minutes=4)
                )
            ).allowed
            assert (
                await guard_auto_batch(
                    db, batch=batch, settings=settings, now=now + timedelta(minutes=5, seconds=1)
                )
            ).allowed
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=0,
                paused=True,
            )
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=1,
                paused=False,
            )
            stopped = await guard_auto_batch(
                db, batch=batch, settings=settings, now=now + timedelta(minutes=6)
            )
            assert not stopped.allowed and stopped.reason_code == "auto_paused"
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            assert len((await db.scalars(select(SummaryDeliveryBatch))).all()) == 1

    asyncio.run(exercise())


def test_changed_roster_review_remains_after_roster_returns(client, tmp_path, monkeypatch):
    from twobrain_rec_server.cabinet.summary_autosend import (
        guard_auto_batch,
        reconcile_meeting_autosend,
        save_rule,
    )
    from twobrain_rec_server.calendar.owner_content import (
        OWNER_CONTENT_ENVELOPE_KEY,
        seal_owner_event_content,
    )
    from twobrain_rec_server.db.models import CalendarEventSnapshot
    from twobrain_rec_server.db.models.summary_autosend import SummaryAutoSendException

    meeting_id, event_id, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)
    monkeypatch.setattr("twobrain_rec_server.config.get_settings", lambda: settings)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=now,
            )
            await _publish_ready(db, meeting_id, now + timedelta(seconds=1))
            batch = await reconcile_meeting_autosend(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                now=now + timedelta(seconds=2),
            )
            event = await db.get(CalendarEventSnapshot, event_id)
            original = dict(event.provider_extras_json)
            from twobrain_rec_server.calendar.owner_content import owner_event_content

            content = owner_event_content(
                event, settings.credential_encryption_key_file.read_bytes()
            )
            content["participants"].append(
                {
                    "email": "external@example.test",
                    "participant_kind": "required_attendee",
                    "response_status": "accepted",
                }
            )
            # Seal a synthetic complete event shape using the same protected envelope.
            altered = SimpleNamespace(
                title=content["title"],
                description=None,
                location=None,
                participants=content["participants"],
                attachments_metadata=[],
                provider_extras=content["provider_extras"],
                conference_links=[],
            )
            event.provider_extras_json = original | {
                OWNER_CONTENT_ENVELOPE_KEY: seal_owner_event_content(
                    altered, settings.credential_encryption_key_file.read_bytes()
                )
            }
            await db.flush()
            guard = await guard_auto_batch(
                db, batch=batch, settings=settings, now=now + timedelta(minutes=5, seconds=1)
            )
            assert not guard.allowed and guard.requires_review
            event.provider_extras_json = original
            await db.flush()
            guard = await guard_auto_batch(
                db, batch=batch, settings=settings, now=now + timedelta(minutes=6)
            )
            assert not guard.allowed and guard.requires_review
            assert await db.scalar(select(SummaryAutoSendException.id)) is not None

    asyncio.run(exercise())


def _roster_case():
    now = datetime.now(UTC)
    event = SimpleNamespace(
        privacy_class="public", source_status="confirmed", source_deleted_at=None
    )
    source = SimpleNamespace(
        provider_family="google_calendar", sync_state="synced", last_successful_sync_at=now
    )
    content = {
        "provider_extras": {"google_attendees_complete": True, "google_organizer_self": True},
        "participants": [
            {
                "participant_kind": "organizer",
                "email": "owner@example.test",
                "response_status": "unknown",
                "provider_details": {"self": True},
            },
            {
                "participant_kind": "required_attendee",
                "email": "member@example.test",
                "response_status": "accepted",
            },
        ],
    }
    return now, event, source, content


def test_only_explicit_complete_fresh_google_roster_is_eligible():
    now, event, source, content = _roster_case()
    assert evaluate_google_roster(event, source, content, now=now).allowed
    source.last_successful_sync_at = now - timedelta(minutes=15, seconds=1)
    assert evaluate_google_roster(event, source, content, now=now).reason_code == "calendar_stale"


@pytest.mark.parametrize(
    "case,reason",
    [
        ("unsupported", "calendar_unsupported"),
        ("private", "calendar_private"),
        ("omitted", "calendar_incomplete"),
        ("missing_proof", "calendar_incomplete"),
        ("not_organizer", "distributor_unverified"),
        ("declined", "calendar_declined"),
        ("resource", "calendar_resource"),
        ("group", "calendar_resource"),
        ("extra_guest", "calendar_incomplete"),
    ],
)
def test_roster_uncertainty_never_silently_approves_subset(case, reason):
    now, event, source, content = _roster_case()
    if case == "unsupported":
        source.provider_family = "custom_caldav"
    elif case == "private":
        event.privacy_class = "private"
    elif case == "omitted":
        content["provider_extras"]["google_attendees_complete"] = False
    elif case == "missing_proof":
        content["provider_extras"].clear()
    elif case == "not_organizer":
        content["provider_extras"]["google_organizer_self"] = False
    elif case == "declined":
        content["participants"][1]["response_status"] = "declined"
    elif case in {"resource", "group"}:
        content["participants"][1]["participant_kind"] = case
    elif case == "extra_guest":
        content["participants"][1]["provider_details"] = {"additionalGuests": 1}
    guard = evaluate_google_roster(event, source, content, now=now)
    assert not guard.allowed and guard.requires_review and guard.reason_code == reason


def test_preferences_are_ask_only_and_pause_epoch_prevents_resurrection(client):
    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            initial = await get_preferences(db, workspace_id=WORKSPACE_ID, owner_user_id=USER_ID)
            assert initial.ask_enabled and not initial.paused and initial.version == 0
            saved = await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=0,
                ask_enabled=False,
            )
            assert saved.version == 1 and saved.auto_epoch == 0
            noop = await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=1,
                ask_enabled=False,
            )
            assert noop.version == 1
            paused = await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=1,
                paused=True,
            )
            assert paused.version == 2 and paused.auto_epoch == 1
            resumed = await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=2,
                paused=False,
            )
            assert resumed.version == 3 and resumed.auto_epoch == 2
            with pytest.raises(ProblemDetail) as exc:
                await update_preferences(
                    db,
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    expected_version=1,
                    paused=True,
                )
            assert exc.value.status == 409
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            other = await db.scalar(
                select(SummarySharingPreference).where(
                    SummarySharingPreference.workspace_id == uuid4()
                )
            )
            assert other is None

    asyncio.run(exercise())


def test_resume_does_not_send_results_ready_during_pause(client, tmp_path):
    from twobrain_rec_server.cabinet.summary_autosend import (
        list_autosend_readiness_candidates,
        reconcile_meeting_autosend,
        save_rule,
    )

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=now,
            )
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=0,
                paused=True,
                now=now + timedelta(seconds=1),
            )
            await _publish_ready(db, meeting_id, now + timedelta(seconds=2))
            assert (
                await reconcile_meeting_autosend(
                    db,
                    settings=settings,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    now=now + timedelta(seconds=3),
                )
                is None
            )
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=1,
                paused=False,
                now=now + timedelta(seconds=4),
            )
            assert (
                await reconcile_meeting_autosend(
                    db,
                    settings=settings,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    now=now + timedelta(minutes=6),
                )
                is None
            )
            assert (WORKSPACE_ID, meeting_id) not in await list_autosend_readiness_candidates(db)
            await db.commit()

    asyncio.run(exercise())


def test_auto_rule_version_disable_and_settings_without_javascript(client, tmp_path):
    from twobrain_rec_server.cabinet.summary_autosend import disable_rule, save_rule

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path, series=True)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            result = await save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="series",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=now,
            )
            rule = result["rules"]["series"]
            with pytest.raises(ProblemDetail) as caught:
                await disable_rule(
                    db,
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    rule_id=rule["id"],
                    expected_version=0,
                )
            assert caught.value.status == 409
            result = await disable_rule(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                rule_id=rule["id"],
                expected_version=rule["version"],
            )
            assert not result["enabled"]
            await db.commit()

    asyncio.run(exercise())
    from tests.contract.test_ingest_openapi_contract import auth_headers

    response = client.get(
        "/api/v1/cabinet/summary-sharing/preferences/form", headers=auth_headers()
    )
    assert response.status_code == 200
    assert "Предлагать отправить итоги" in response.text
    assert "csrf_token" in response.text
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["referrer-policy"] == "no-referrer"


@pytest.mark.strict_rls
def test_real_maintenance_role_scans_ready_and_reserves_auto(
    client, tmp_path, migrated_postgres_urls
):
    from sqlalchemy import text
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from twobrain_rec_server.cabinet.summary_autosend import (
        list_autosend_readiness_candidates,
        reconcile_meeting_autosend,
        save_rule,
    )
    from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
    from twobrain_rec_server.workflows.summary_delivery import reserve_recipient

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)
    ready_at = now - timedelta(minutes=6)
    role = "twobrain_rec_maintenance"
    role_url = make_url(migrated_postgres_urls.probe_url)
    assert role_url.username == role
    owner_url = make_url(settings.database_url)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            from twobrain_rec_server.db.models import CalendarSource

            source = await db.scalar(
                select(CalendarSource).where(CalendarSource.workspace_id == WORKSPACE_ID)
            )
            source.last_successful_sync_at = ready_at - timedelta(seconds=2)
            await db.flush()
            await save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=ready_at - timedelta(seconds=1),
            )
            await _publish_ready(db, meeting_id, ready_at)
            await db.commit()
        owner_engine = create_async_engine(settings.database_url, isolation_level="AUTOCOMMIT")
        engine = None
        try:
            async with owner_engine.connect() as conn:
                await conn.execute(text(f"GRANT USAGE ON SCHEMA public TO {role}"))
                await conn.execute(
                    text(
                        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO {role}"
                    )
                )
            engine = create_async_engine(
                owner_url.set(username=role, password=role_url.password).render_as_string(
                    hide_password=False
                )
            )
            maker = async_sessionmaker(engine, expire_on_commit=False)
            async with maker() as db:
                row = (
                    await db.execute(
                        text(
                            "SELECT session_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname=session_user"
                        )
                    )
                ).one()
                assert row[0] == role and not row[1] and not row[2]
                await db.rollback()
                await apply_tenant_context(
                    db,
                    MaintenanceTenantContext(
                        operation_name="summary_delivery_reconciliation",
                        actor_id="synthetic-auto-test",
                        reason_category="validation",
                        feature_area="sharing",
                    ),
                )
                assert await db.scalar(text("SELECT rec_maintenance_allowed()")) is True
                assert (WORKSPACE_ID, meeting_id) in await list_autosend_readiness_candidates(db)
                await db.commit()
                await apply_tenant_context(
                    db,
                    MaintenanceTenantContext(
                        operation_name="summary_delivery_reconciliation",
                        actor_id="synthetic-auto-test",
                        reason_category="validation",
                        feature_area="sharing",
                    ),
                )
                batch = await reconcile_meeting_autosend(
                    db, settings=settings, workspace_id=WORKSPACE_ID, meeting_id=meeting_id
                )
                assert batch is not None
                recipient = await db.scalar(
                    select(SummaryRecipientDelivery).where(
                        SummaryRecipientDelivery.batch_id == batch.id
                    )
                )
                batch_id, delivery_id = batch.id, recipient.id
                await db.commit()
            payload = await reserve_recipient(
                maker,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                batch_id=batch_id,
                recipient_id=delivery_id,
            )
            assert payload is not None and payload["automatic"] is True
            async with maker() as db:
                # A maintenance login without an approved context has no cross-workspace view.
                assert (await db.scalars(select(SummaryRecipientDelivery))).all() == []
        finally:
            if engine is not None:
                await engine.dispose()
            async with owner_engine.connect() as conn:
                await conn.execute(text(f"DROP OWNED BY {role}"))
            await owner_engine.dispose()

    asyncio.run(exercise())


def test_ai_publication_and_auto_outbox_roll_back_together(client, tmp_path, monkeypatch):
    from twobrain_rec_server.cabinet import summary_autosend
    from twobrain_rec_server.db.models import Meeting, MeetingSummarySlot
    from twobrain_rec_server.db.models.summary_sharing import (
        PublishedMeetingSummary,
        SummaryDeliveryBatch,
    )
    from twobrain_rec_server.outcomes.ai_service import _cas_summary_slot

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)
    monkeypatch.setattr("twobrain_rec_server.outcomes.ai_service.get_settings", lambda: settings)
    real_reconcile = summary_autosend.reconcile_meeting_autosend

    async def fail_after_outbox(db, **kwargs):
        batch = await real_reconcile(db, **kwargs)
        assert batch is not None
        raise RuntimeError("synthetic-before-commit")

    monkeypatch.setattr(summary_autosend, "reconcile_meeting_autosend", fail_after_outbox)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            await summary_autosend.save_rule(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                enabled=True,
                template_key="summary",
                recipient_user_ids=[recipient_id],
                expected_version=0,
                now=now,
            )
            outcome = await _publish_ready(db, meeting_id, now)
            slot = await db.scalar(
                select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id)
            )
            slot.current_outcome_set_id = None
            slot.current_binding_class = None
            outcome.revision_state = "candidate"
            outcome.accepted_at = None
            outcome_id = outcome.id
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            with pytest.raises(RuntimeError, match="synthetic-before-commit"):
                await _cas_summary_slot(
                    db,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    template_key="summary",
                    replacement_outcome_set_id=outcome_id,
                    expected_current_outcome_set_id=None,
                    expected_source_fingerprint=None,
                    expected_deletion_epoch=meeting.deletion_epoch,
                )
            await db.rollback()
        async with client.app_state["sessionmaker"]() as db:
            slot = await db.scalar(
                select(MeetingSummarySlot).where(MeetingSummarySlot.meeting_id == meeting_id)
            )
            assert slot.current_outcome_set_id is None
            assert (await db.scalars(select(SummaryDeliveryBatch))).all() == []
            assert (await db.scalars(select(PublishedMeetingSummary))).all() == []

    asyncio.run(exercise())


def test_preferences_forms_keep_csrf_and_return_human_conflicts(client):
    from tests.integration.test_cabinet_csrf import (
        OWNER_REVIEW_TEST_TOKEN,
        _seed_owner_review_session,
    )
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME

    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    path = "/api/v1/cabinet/summary-sharing/preferences/form"
    response = client.get(path)
    assert response.status_code == 200 and 'name="csrf_token"' in response.text
    assert client.post(path, data={"expected_version": "0"}).status_code == 403
    csrf = issue_csrf_token(session_id=session.id, secret=str(client.app.state.web_csrf_secret))
    response = client.post(
        path, data={"expected_version": "broken", "csrf_token": csrf}, follow_redirects=False
    )
    assert response.status_code == 422 and response.headers["content-type"].startswith("text/html")
    response = client.post(
        path,
        data={"expected_version": "0", "paused": "true", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 303
    response = client.post(
        path,
        data={"expected_version": "0", "ask_enabled": "true", "csrf_token": csrf},
        follow_redirects=False,
    )
    assert response.status_code == 409 and "Настройки уже изменились" in response.text
    assert response.headers["content-type"].startswith("text/html")


@pytest.mark.parametrize("fresh_consent", [False, True])
def test_ready_after_resume_skips_started_meeting_unless_new_preauthorization(
    client, tmp_path, fresh_consent
):
    from twobrain_rec_server.cabinet.summary_autosend import (
        disable_rule,
        list_autosend_readiness_candidates,
        reconcile_meeting_autosend,
        save_rule,
    )

    meeting_id, _, _, settings, now, recipient_id = _prepare_auto(client, tmp_path)

    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            args = dict(
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                owner_user_id=USER_ID,
                scope="meeting",
                template_key="summary",
                recipient_user_ids=[recipient_id],
            )
            saved = await save_rule(db, **args, enabled=True, expected_version=0, now=now)
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=0,
                paused=True,
                now=now + timedelta(seconds=1),
            )
            await update_preferences(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                expected_version=1,
                paused=False,
                now=now + timedelta(seconds=2),
            )
            if fresh_consent:
                rule = saved["rules"]["meeting"]
                disabled = await disable_rule(
                    db,
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    rule_id=rule["id"],
                    expected_version=rule["version"],
                )
                await save_rule(
                    db,
                    **args,
                    enabled=True,
                    expected_version=disabled["version"],
                    now=now + timedelta(seconds=3),
                )
            await _publish_ready(db, meeting_id, now + timedelta(seconds=4))
            candidates = await list_autosend_readiness_candidates(db)
            assert ((WORKSPACE_ID, meeting_id) in candidates) == fresh_consent
            batch = await reconcile_meeting_autosend(
                db,
                settings=settings,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                now=now + timedelta(seconds=5),
            )
            assert (batch is not None) == fresh_consent
            if batch is not None:
                from twobrain_rec_server.cabinet.summary_autosend import (
                    auto_state,
                    preferences_view,
                )
                from twobrain_rec_server.db.models.summary_sharing import SummaryRecipientDelivery

                view = await auto_state(
                    db,
                    settings=settings,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    owner_user_id=USER_ID,
                    now=now + timedelta(seconds=6),
                )
                assert view["state"] == "scheduled" and view["batch"]["can_cancel"]
                row = await db.scalar(
                    select(SummaryRecipientDelivery).where(
                        SummaryRecipientDelivery.batch_id == batch.id
                    )
                )
                row.state = "accepted"
                batch.state = "completed"
                await db.flush()
                await update_preferences(
                    db,
                    workspace_id=WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    expected_version=2,
                    paused=True,
                    now=now + timedelta(seconds=7),
                )
                view = await auto_state(
                    db,
                    settings=settings,
                    workspace_id=WORKSPACE_ID,
                    meeting_id=meeting_id,
                    owner_user_id=USER_ID,
                    now=now + timedelta(seconds=8),
                )
                assert view["state"] == "sent" and not view["batch"]["can_cancel"]
                assert (
                    await preferences_view(db, workspace_id=WORKSPACE_ID, owner_user_id=USER_ID)
                )["queue"] == []
            await db.commit()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "counts,expected",
    [
        ({"pending": 2}, "scheduled"),
        ({"accepted": 2}, "sent"),
        ({"accepted": 1, "failed": 1}, "partial"),
        ({"suppressed": 1}, "partial"),
        ({"accepted": 1, "unknown": 1}, "unknown"),
        ({"failed": 1, "unknown": 1}, "partial"),
        ({"pending": 1, "unknown": 1}, "scheduled"),
        ({"sending": 1, "failed": 1}, "sending"),
        ({"sending": 1}, "sending"),
    ],
)
def test_auto_presentation_uses_recipient_outcomes(counts, expected):
    from twobrain_rec_server.cabinet.summary_autosend import _delivery_presentation

    assert _delivery_presentation(SimpleNamespace(state="completed"), counts) == expected


def test_auto_owner_api_cookie_versions_and_disable(client, tmp_path):
    from tests.integration.test_cabinet_csrf import (
        OWNER_REVIEW_TEST_TOKEN,
        _seed_owner_review_session,
    )
    from twobrain_rec_server.auth.csrf import issue_csrf_token
    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME

    meeting_id, _, _, _, _, recipient_id = _prepare_auto(client, tmp_path, series=True)
    session = client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    token = issue_csrf_token(session_id=session.id, secret=str(client.app.state.web_csrf_secret))
    headers = {"X-CSRF-Token": token}
    path = f"/api/v1/cabinet/meetings/{meeting_id}/summary-sharing/auto-send"
    body = dict(
        scope="series",
        enabled=True,
        template_key="summary",
        recipient_user_ids=[str(recipient_id)],
        expected_version=0,
    )
    assert client.post(path, json=body).status_code == 403
    response = client.post(path, json=body, headers=headers)
    assert response.status_code == 200, response.text
    assert "no-store" in response.headers["cache-control"]
    assert response.headers["referrer-policy"] == "no-referrer"
    rule = response.json()["rules"]["series"]
    assert client.post(path, json=body, headers=headers).status_code == 409
    response = client.post(
        f"/api/v1/cabinet/summary-sharing/preferences/rules/{rule['id']}/disable",
        json={"expected_version": rule["version"]},
        headers=headers,
    )
    assert response.status_code == 200 and not response.json()["enabled"]
    response = client.patch(
        "/api/v1/cabinet/summary-sharing/preferences",
        json={"expected_version": 0, "ask_enabled": False},
        headers=headers,
    )
    assert response.status_code == 200 and not response.json()["ask_enabled"]
    assert (
        client.patch(
            "/api/v1/cabinet/summary-sharing/preferences",
            json={"expected_version": 0, "paused": True},
            headers=headers,
        ).status_code
        == 409
    )
