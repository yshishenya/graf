"""Isolated account transaction, not runtime T113 or an HTTP visibility proof."""

import asyncio
from contextlib import asynccontextmanager
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID

import pytest
from sqlalchemy import select

from tests.contract.test_activation_milestone_ingress import isolated_admission  # noqa: F401
from tests.contract.test_result_view_projection import _seed_projection
from tests.contract.test_result_visibility import START, _run
from tests.fakes.auth_contexts import (
    AUTH_BOOTSTRAP_WORKSPACE_ID,
    DEVICE_ID,
    USER_ID,
    WORKSPACE_ID,
    principal,
)
from twobrain_rec_server.cabinet.result_visibility import (
    issue_result_view_proof,
    load_fresh_result_view_bindings,
    load_result_view_bindings,
    verify_result_view_proof,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    MediaRevision,
    ProcessingWorkflow,
    ProductActivationMilestone,
    UserIdentity,
)
from twobrain_rec_server.ingest.media_revisions import source_fingerprint_for_revision
from twobrain_rec_server.product_analytics import ingest

pytestmark = pytest.mark.usefixtures("isolated_admission")

SECRET = "synthetic-result-view-admission-secret"
SESSION_ID = UUID("50000000-0000-0000-0000-000000000001")


def _result_principal():
    return replace(principal(), session_id=SESSION_ID, auth_via_session=True,
                   session_workspace_id=WORKSPACE_ID, session_device_id=DEVICE_ID)


@pytest.fixture
def result_period(monkeypatch):
    @asynccontextmanager
    async def period(self, sessionmaker):
        async with sessionmaker() as db:
            yield ingest._AccountAdmissionContext(db, started_at=START, recheck=lambda: None)

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)


async def _prepare(sessions, *, capture_unknown=False):
    async with sessions() as db:
        review, _, _, _ = await _seed_projection(db)
        db.add(AuthSession(
            id=SESSION_ID, user_id=USER_ID, workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID, provider="email", session_token_hash="synthetic-result-session",
            status="active", expires_at=datetime.now(UTC) + timedelta(hours=1),
        ))
        await db.flush()
        db.add(AuthSessionDeviceBinding(
            auth_session_id=SESSION_ID, registered_device_id=DEVICE_ID, device_state="trusted",
        ))
        await db.commit()
        if capture_unknown:
            revision = await db.get(MediaRevision, review.provenance.media_revision_id)
            revision.source_kind = "initial_mixed_recording"
            workflow = await db.scalar(select(ProcessingWorkflow).where(
                ProcessingWorkflow.media_revision_id == revision.id,
            ))
            workflow.source_fingerprint = source_fingerprint_for_revision(revision)
            await db.commit()
        params = dict(owner_id=USER_ID, workspace_id=WORKSPACE_ID, auth_session_id=SESSION_ID,
                      session_device_id=DEVICE_ID, started_at=START)
        now = datetime.now(UTC)
        bindings = await load_result_view_bindings(db, review=review, now=now, **params)
        proof = issue_result_view_proof(bindings["transcript:0"], secret=SECRET, issued_at=now)

    async def verify(db, started_at):
        assert started_at == START
        bindings = await load_fresh_result_view_bindings(
            db, principal=_result_principal(), workspace_id=WORKSPACE_ID,
            meeting_id=review.meeting.meeting_id, started_at=started_at,
        )
        return next((binding for binding in bindings.values() if verify_result_view_proof(
            proof, binding, secret=SECRET, now=datetime.now(UTC),
        ) == "valid"), None)

    return verify


async def _accept(sessions, verify, surface="cabinet_web"):
    return await ingest.ProductAnalyticsIngestService(
        Settings(product_analytics_enabled=True, web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID),
    ).admit_result_view(
        principal=_result_principal(),
        workspace_id=WORKSPACE_ID, sessionmaker=sessions,
        verify_view=verify, surface=surface,
    )


def test_real_context_is_absent_even_if_test_legal_gate_is_open(
    postgres_seeded_database_url,
):
    async def scenario(sessions):
        called = False

        async def forbidden(*args):
            nonlocal called
            called = True
            raise AssertionError("a missing runtime context cannot run a verifier")

        assert not await _accept(sessions, forbidden)
        assert not called
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []

    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("surface,capture_unknown", [
    ("cabinet_web", False), ("cabinet_desktop", False), ("cabinet_web", True),
])
def test_pair_commits_once_and_replay_preserves_original_payload(
    postgres_seeded_database_url, result_period, surface, capture_unknown,
):
    async def scenario(sessions):
        verify = await _prepare(sessions, capture_unknown=capture_unknown)
        assert await _accept(sessions, verify, surface)
        async with sessions() as db:
            original = {row.event_name: row.safe_payload for row in
                        await db.scalars(select(ProductActivationMilestone))}
        assert set(original) == {"first_result_viewed", "first_value_session_completed"}
        value = original["first_value_session_completed"]
        if capture_unknown:
            assert "first_recording_completed" not in value["properties"]
        else:
            assert value["properties"]["first_recording_completed"] is False
        assert value["properties"]["attribution_reliability"] == "unknown"
        assert "synthetic" not in str(original) and "proof" not in str(original)
        assert await _accept(sessions, verify, surface)
        async with sessions() as db:
            rows = list(await db.scalars(select(ProductActivationMilestone)))
            assert {row.event_name: row.safe_payload for row in rows} == original
            assert all(row.source_kind == ("browser" if surface == "cabinet_web" else "desktop")
                       for row in rows)
    _run(postgres_seeded_database_url, scenario)


def test_unknown_commit_is_not_retried_and_next_showing_resolves_existing_keys(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        original = ingest.admit_account_milestone
        calls = 0

        async def admit(db, event, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 1:
                commit = db.commit

                async def unknown_commit():
                    await commit()
                    raise RuntimeError("synthetic lost commit acknowledgement")

                monkeypatch.setattr(db, "commit", unknown_commit)
            return await original(db, event, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(ingest, "admit_account_milestone", admit)
            assert not await _accept(sessions, verify)
        assert calls == 2
        async with sessions() as db:
            before = {row.event_name: row.safe_payload for row in
                      await db.scalars(select(ProductActivationMilestone))}
        assert len(before) == 2
        assert await _accept(sessions, verify)
        async with sessions() as db:
            assert {row.event_name: row.safe_payload for row in
                    await db.scalars(select(ProductActivationMilestone))} == before
    _run(postgres_seeded_database_url, scenario)


def test_existing_first_result_from_another_showing_is_kept_when_value_is_added(
    postgres_seeded_database_url, result_period,
):
    from twobrain_rec_server.cabinet.web import build_first_result_viewed_product_analytics_payload
    from twobrain_rec_server.product_analytics.events import build_activation_event
    from twobrain_rec_server.product_analytics.identity import build_safe_identity

    async def scenario(sessions):
        verify = await _prepare(sessions)
        payload = build_first_result_viewed_product_analytics_payload(
            stable_pseudonymous_user_id=build_safe_identity(user_source_id=str(USER_ID)).stable_pseudonymous_user_id,
            result_state="ready", useful_output_present=True, surface="earlier_showing",
        )
        async with sessions() as db:
            event = build_activation_event(
                payload["event_name"], stable_pseudonymous_user_id=payload["stable_pseudonymous_user_id"],
                properties=payload["properties"],
            )
            row, created = await ingest.admit_account_milestone(db, event, account_id=USER_ID, source_kind="server")
            assert created
            before = row.safe_payload
            await db.commit()
        assert await _accept(sessions, verify)
        async with sessions() as db:
            rows = {row.event_name: row for row in await db.scalars(select(ProductActivationMilestone))}
            assert len(rows) == 2
            assert rows["first_result_viewed"].safe_payload == before
            assert rows["first_result_viewed"].source_kind == "server"
            assert rows["first_value_session_completed"].safe_payload["properties"]["first_recording_completed"] is False
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["owner", "workspace", "session", "device"])
def test_callback_binding_cannot_change_the_trusted_account_or_session(
    postgres_seeded_database_url, result_period, broken,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)

        async def other(db, started_at):
            binding = await verify(db, started_at)
            foreign = UUID("90000000-0000-0000-0000-000000000001")
            if broken in {"owner", "workspace"}:
                return replace(binding, source=replace(binding.source, **{
                    "owner_id" if broken == "owner" else "workspace_id": foreign,
                }))
            return replace(binding, **{
                "auth_session_id" if broken == "session" else "session_device_id": foreign,
            })

        assert not await _accept(sessions, other)
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


def test_busy_identity_lock_and_closed_identity_do_not_run_the_verifier(
    postgres_seeded_database_url, result_period,
):
    async def scenario(sessions):
        called = False

        async def forbidden(*args):
            nonlocal called
            called = True
            raise AssertionError("identity has not passed")

        async with sessions() as blocker:
            account = await blocker.scalar(select(UserIdentity).where(
                UserIdentity.id == USER_ID,
            ).with_for_update())
            began = monotonic()
            assert not await _accept(sessions, forbidden)
            assert monotonic() - began < 1 and not called
            account.status = "closed"
            await blocker.commit()
        assert not await _accept(sessions, forbidden) and not called
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["unknown", "naive", "future", "guard"])
def test_incomplete_period_context_is_never_an_authorization(
    postgres_seeded_database_url, monkeypatch, broken,
):
    @asynccontextmanager
    async def period(self, sessionmaker):
        async with sessionmaker() as db:
            yield ingest._AccountAdmissionContext(
                db, started_at={"unknown": None, "naive": START.replace(tzinfo=None),
                                "future": datetime.now(UTC) + timedelta(days=1), "guard": START}[broken],
                recheck=None if broken == "guard" else lambda: None,
            )

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)

    async def scenario(sessions):
        called = False

        async def forbidden(*args):
            nonlocal called
            called = True
            raise AssertionError("period has not passed")

        assert not await _accept(sessions, forbidden)
        assert not called
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


def test_period_revoked_after_the_pair_is_written_rolls_back_before_commit(
    postgres_seeded_database_url, monkeypatch,
):
    written = False

    def current():
        if written:
            raise PermissionError("synthetic period revoked")

    @asynccontextmanager
    async def period(self, sessionmaker):
        async with sessionmaker() as db:
            yield ingest._AccountAdmissionContext(db, started_at=START, recheck=current)

    original = ingest.admit_account_milestone

    async def admit(db, event, **kwargs):
        nonlocal written
        row = await original(db, event, **kwargs)
        if event.event_name == "first_value_session_completed":
            written = True
        return row

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
    monkeypatch.setattr(ingest, "admit_account_milestone", admit)

    async def scenario(sessions):
        verify = await _prepare(sessions)
        assert not await _accept(sessions, verify)
        assert written
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


def test_caller_cancellation_closes_the_verifier_and_propagates(
    postgres_seeded_database_url, result_period,
):
    async def scenario(sessions):
        await _prepare(sessions)
        entered = asyncio.Event()
        stopped = False

        async def verify(db, started_at):
            nonlocal stopped
            entered.set()
            try:
                await asyncio.sleep(10)
            finally:
                stopped = True

        task = asyncio.create_task(_accept(sessions, verify))
        await asyncio.wait_for(entered.wait(), timeout=2)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.done() and stopped
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("failure", ["second_insert", "gate", "commit"])
def test_second_write_or_commit_failure_cannot_leave_a_new_partial_pair(
    postgres_seeded_database_url, result_period, monkeypatch, failure,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        original = ingest.admit_account_milestone
        calls = 0

        async def admit(db, event, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 2 and failure == "second_insert":
                raise RuntimeError("synthetic second insert failure")
            if calls == 2 and failure == "gate":
                monkeypatch.setattr(ingest, "activation_milestone_write_blockers", lambda s: ("withdrawn",))
            if calls == 1 and failure == "commit":
                async def broken_commit():
                    raise RuntimeError("synthetic commit failure")
                monkeypatch.setattr(db, "commit", broken_commit)
            return await original(db, event, **kwargs)

        monkeypatch.setattr(ingest, "admit_account_milestone", admit)
        assert not await _accept(sessions, verify)
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
        assert calls == 2
    _run(postgres_seeded_database_url, scenario)


def test_two_independent_sessions_reconcile_one_pair(
    postgres_seeded_database_url, result_period,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        assert all(await asyncio.gather(*(_accept(sessions, verify) for _ in range(2))))
        async with sessions() as db:
            assert len(list(await db.scalars(select(ProductActivationMilestone)))) == 2
    _run(postgres_seeded_database_url, scenario)


def test_missing_fact_and_timeout_leave_no_rows_or_running_verifier(
    postgres_seeded_database_url, result_period,
):
    async def scenario(sessions):
        await _prepare(sessions)
        stopped = False

        async def absent(db, started_at):
            return None

        async def slow(db, started_at):
            nonlocal stopped
            try:
                await asyncio.sleep(10)
            finally:
                stopped = True

        assert not await _accept(sessions, absent)
        began = monotonic()
        assert not await _accept(sessions, slow)
        assert stopped and monotonic() - began < 2
        async with sessions() as db:
            assert list(await db.scalars(select(ProductActivationMilestone))) == []
    _run(postgres_seeded_database_url, scenario)
