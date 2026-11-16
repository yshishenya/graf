"""Isolated account transaction, not runtime T113 or an HTTP visibility proof."""

import asyncio
from contextlib import asynccontextmanager, suppress
from dataclasses import asdict, replace
from datetime import UTC, datetime, timedelta
from time import monotonic
from uuid import UUID

import pytest
from sqlalchemy import event, insert, select, text

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
from twobrain_rec_server.cabinet.result_projection_budget import (
    ProjectionBudgetExceeded,
    ProjectionReadBudget,
)
from twobrain_rec_server.cabinet.result_projection_session import result_admission_session
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
from twobrain_rec_server.product_analytics import ingest, milestones

pytestmark = pytest.mark.usefixtures("isolated_admission")

SECRET = "synthetic-result-view-admission-secret"
SESSION_ID = UUID("50000000-0000-0000-0000-000000000001")


def _result_principal():
    return replace(principal(), session_id=SESSION_ID, auth_via_session=True,
                   session_workspace_id=WORKSPACE_ID, session_device_id=DEVICE_ID)


@pytest.fixture
def result_period(monkeypatch):
    owners = []
    @asynccontextmanager
    async def period(self, sessionmaker, *, work_deadline, cleanup_deadline):
        async with result_admission_session(
            sessionmaker, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
        ) as owner:
            owners.append(owner)
            yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=lambda: None, owner=owner)

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
    return owners


async def _prepare(sessions, *, capture_unknown=False, ordinary=False, observed=None):
    async with sessions() as db:
        if ordinary:
            from tests.contract.test_result_projection_session import _seed_ordinary_projection
            from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
            seed, *_ = await _seed_ordinary_projection(db)
            review = await get_cabinet_meeting_review(
                db, workspace_id=WORKSPACE_ID, meeting_id=seed.meeting.meeting_id, viewer_user_id=USER_ID,
            )
        else:
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
        if observed is not None:
            observed.append(bindings)
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


@pytest.mark.parametrize("kind", ["plain", "foreign", "readonly", "unstarted"])
def test_unowned_period_session_is_refused_before_verifier(postgres_seeded_database_url, monkeypatch, kind):
    from twobrain_rec_server.cabinet.result_projection_session import (
        ResultAdmissionSession,
        result_projection_session,
    )
    @asynccontextmanager
    async def period(self, sessionmaker, **deadlines):
        if kind == "readonly":
            async with result_projection_session(sessionmaker, deadline=deadlines["cleanup_deadline"]) as owner:
                yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=lambda: None, owner=owner)
        elif kind == "foreign":
            async with result_admission_session(sessionmaker, **deadlines) as owner, sessionmaker() as foreign:
                yield ingest._AccountAdmissionContext(foreign, started_at=START, recheck=lambda: None, owner=owner)
        else:
            async with sessionmaker() as db:
                owner = ResultAdmissionSession(db, deadlines["work_deadline"]) if kind == "unstarted" else None
                yield ingest._AccountAdmissionContext(db, started_at=START, recheck=lambda: None, owner=owner)
    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
    async def scenario(sessions):
        await _prepare(sessions)
        called = []

        async def verify(db, started_at):
            called.append(True)
            return None

        assert not await _accept(sessions, verify)
        assert called == []
    _run(postgres_seeded_database_url, scenario)


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


def test_complete_hour_meeting_uses_one_budget_through_pair_commit(
    postgres_seeded_database_url, result_period,
):
    from twobrain_rec_server.db.models import Meeting
    async def scenario(sessions):
        observed = []
        verify = await _prepare(sessions, ordinary=True, observed=observed)
        async with sessions() as db:
            meeting_id = await db.scalar(select(Meeting.id).where(Meeting.local_recording_id == "synthetic-current-session-guard"))
            expected = await load_fresh_result_view_bindings(
                db, principal=_result_principal(), workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id, started_at=START,
            )
        assert await _accept(sessions, verify)
        assert len(observed) == 1
        assert {key: asdict(value) for key, value in observed[0].items()} == {
            key: asdict(value) for key, value in expected.items()
        }
        owner = result_period[-1]
        assert owner._committed and owner._terminal and not owner._listeners
        assert not owner.db.in_transaction() and not owner.db.identity_map
        assert 1200 <= owner.budget.rows <= 16384 and owner.sql_count <= 128
        async with sessions() as db:
            rows = list(await db.scalars(select(ProductActivationMilestone)))
            assert len(rows) == 2
            assert all(row.safe_payload["properties"]["attribution_reliability"] == "unknown" for row in rows)
        print(f"ordinary_admission sql={owner.sql_count} rows={owner.budget.rows} "
              f"bytes={owner.budget.raw_bytes} nodes={owner.budget.json_nodes}")
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("operation", ["dml", "flush", "commit", "rollback", "raw_connection"])
def test_verifier_cannot_write_or_end_snapshot_even_if_it_catches_refusal(
    postgres_seeded_database_url, result_period, operation,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        failures = []
        async def forbidden(db, started_at):
            owner = result_period[-1]
            before = owner.sql_count
            try:
                if operation == "dml":
                    await db.execute(insert(ProductActivationMilestone).values())
                elif operation == "flush":
                    db.add(ProductActivationMilestone(account_id=USER_ID))
                    await db.flush()
                elif operation == "commit":
                    await db.commit()
                elif operation == "rollback":
                    await db.rollback()
                else:
                    await (await db.connection()).execute(select(UserIdentity.id))
            except ProjectionBudgetExceeded:
                pass
            failures.append((owner.failed, owner.sql_count == before))
            return await verify(db, started_at)
        assert not await _accept(sessions, forbidden)
        assert failures == [(True, True)]
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
    _run(postgres_seeded_database_url, scenario)


def test_insert_identity_uuid_charge_and_conflict_zero_keep_same_guard(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        charges, inserts = [], []
        reserve = ProjectionReadBudget.reserve_uuid
        def charge(budget):
            before = (budget.rows, budget.raw_bytes)
            reserve(budget)
            charges.append((budget.rows - before[0], budget.raw_bytes - before[1]))
        monkeypatch.setattr(ProjectionReadBudget, "reserve_uuid", charge)
        engine = sessions.kw["bind"].sync_engine
        def capture(connection, statement, multiparams, params, options):
            if statement.is_insert:
                owner = result_period[-1]
                inserts.append((statement is owner._expected, connection is owner._connection,
                                tuple(item["expr"].key for item in statement.returning_column_descriptions)))
        event.listen(engine, "before_execute", capture)
        try:
            assert await _accept(sessions, verify)
            assert await _accept(sessions, verify)
        finally:
            event.remove(engine, "before_execute", capture)
        assert charges == [(1, 32)] * 4  # Including both ON CONFLICT zero-row outcomes.
        assert inserts == [(True, True, ("id",))] * 4
        assert all(owner._committed and owner.sql_count <= 128 for owner in result_period)
    _run(postgres_seeded_database_url, scenario)


def test_provider_intent_change_before_exact_insert_rolls_back_pair(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    from types import SimpleNamespace
    async def scenario(sessions):
        verify = await _prepare(sessions)
        calls, changed = [], []
        allowed = True
        def gate(settings, *, provider):
            calls.append(provider)
            return SimpleNamespace(allowed=allowed)
        primitive = milestones.admit_account_milestone
        async def revoke_at_insert(db, value, **kwargs):
            execute = kwargs["_execute_insert"]
            async def revoked(statement):
                nonlocal allowed
                allowed = False
                changed.append(True)
                return await execute(statement)
            kwargs["_execute_insert"] = revoked
            return await primitive(db, value, **kwargs)
        monkeypatch.setattr(ingest, "resolve_provider_delivery_gate", gate)
        monkeypatch.setattr(milestones, "admit_account_milestone", revoke_at_insert)
        assert not await _accept(sessions, verify)
        assert changed == [True] and len(calls) >= 2
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
    _run(postgres_seeded_database_url, scenario)


def test_caught_precommit_guard_failure_is_terminal_and_never_retries(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    from twobrain_rec_server.cabinet.result_projection_session import ResultAdmissionSession
    async def scenario(sessions):
        verify = await _prepare(sessions)
        commit = ResultAdmissionSession.commit_pair
        seen = []
        async def catch_failure(owner, recheck):
            def revoked():
                raise PermissionError("synthetic precommit revoke")
            with suppress(PermissionError):
                await commit(owner, revoked)
            state, before = (owner.failed, owner._terminal), owner.sql_count
            read_refused = retry_refused = False
            try:
                await owner.db.scalar(select(UserIdentity.id))
            except ProjectionBudgetExceeded:
                read_refused = True
            try:
                await commit(owner, lambda: None)
            except ProjectionBudgetExceeded:
                retry_refused = True
            seen.append((state, read_refused, retry_refused, owner.sql_count == before))
        monkeypatch.setattr(ResultAdmissionSession, "commit_pair", catch_failure)
        assert not await _accept(sessions, verify)
        assert seen == [((True, True), True, True, True)]
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["repeat_insert", "wrong_order", "extra_event", "uuid_budget", "commit_budget"])
def test_pair_operation_never_refunds_or_accepts_an_extra_phase(
    postgres_seeded_database_url, result_period, monkeypatch, broken,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        primitive = milestones.admit_account_milestone
        reached = []
        if broken == "wrong_order":
            from twobrain_rec_server.cabinet.result_projection_session import ResultAdmissionSession
            original_admit = ResultAdmissionSession.admit_event
            async def reordered(owner, value, **kwargs):
                return await original_admit(owner, replace(value, event_name="first_value_session_completed"), **kwargs)
            monkeypatch.setattr(ResultAdmissionSession, "admit_event", reordered)
        async def changed(db, milestone, **kwargs):
            owner = result_period[-1]
            reached.append(milestone.event_name)
            if broken in {"repeat_insert", "uuid_budget"}:
                execute = kwargs["_execute_insert"]
                async def insert_twice(statement):
                    if broken == "uuid_budget":
                        owner.budget.raw_bytes = 8 * 1024 * 1024
                    result = await execute(statement)
                    return await execute(statement) if broken == "repeat_insert" else result
                kwargs["_execute_insert"] = insert_twice
            result = await primitive(db, milestone, **kwargs)
            if milestone.event_name == "first_value_session_completed":
                if broken == "extra_event":
                    await owner.admit_event(milestone, account_id=USER_ID, source_kind="browser",
                                            before_insert=kwargs["before_insert"])
                elif broken == "commit_budget":
                    owner.sql_count = 128
            return result
        monkeypatch.setattr(milestones, "admit_account_milestone", changed)
        assert not await _accept(sessions, verify)
        assert reached or broken == "wrong_order"
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("broken", ["partial", "nan", "infinite", "string", "bool", "expired", "extended", "reserve", "inverse"])
def test_invalid_deadlines_refuse_before_period_or_verifier(postgres_seeded_database_url, monkeypatch, broken):
    async def scenario(sessions):
        called = []
        @asynccontextmanager
        async def period(*args, **kwargs):
            called.append("period")
            yield None
        async def verify(*args):
            called.append("verify")
        monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
        now = asyncio.get_running_loop().time()
        work, end = now + 1, now + 1.5
        work, end = {
            "partial": (work, None), "nan": (float("nan"), end), "infinite": (work, float("inf")),
            "string": ("invalid", end), "bool": (True, end), "expired": (now - 1, end),
            "extended": (now + 2, now + 2.5), "reserve": (work, work + 0.1), "inverse": (end, work),
        }[broken]
        service = ingest.ProductAnalyticsIngestService(Settings(product_analytics_enabled=True))
        assert not await service.admit_result_view(
            principal=_result_principal(), workspace_id=WORKSPACE_ID, sessionmaker=sessions,
            verify_view=verify, surface="cabinet_web", work_deadline=work, cleanup_deadline=end,
        )
        assert called == []
    _run(postgres_seeded_database_url, scenario)


def test_delay_before_period_uses_original_work_and_cleanup_deadlines(postgres_seeded_database_url, monkeypatch):
    async def scenario(sessions):
        await _prepare(sessions)
        seen = []
        @asynccontextmanager
        async def period(self, sessionmaker, *, work_deadline, cleanup_deadline):
            await asyncio.sleep(0.1)
            async with result_admission_session(
                sessionmaker, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
            ) as owner:
                seen.append(owner.deadline)
                yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=lambda: None, owner=owner)
        monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
        entered = []
        async def verify(*args):
            entered.append(True)
            await asyncio.sleep(10)
        start = asyncio.get_running_loop().time()
        work, end = start + 0.3, start + 0.8
        assert not await ingest.ProductAnalyticsIngestService(Settings(
            product_analytics_enabled=True, web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
        )).admit_result_view(
            principal=_result_principal(), workspace_id=WORKSPACE_ID, sessionmaker=sessions,
            verify_view=verify, surface="cabinet_web", work_deadline=work, cleanup_deadline=end,
        )
        assert seen == [work] and entered == [True]
        assert 0.28 <= asyncio.get_running_loop().time() - start < 0.6
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
    _run(postgres_seeded_database_url, scenario)


def test_busy_shared_period_db_fence_does_not_enter_verifier(postgres_seeded_database_url, result_period):
    async def scenario(sessions):
        await _prepare(sessions)
        called = []
        async def verify(*args):
            called.append(True)
        async with sessions() as operator:
            await operator.execute(text("SELECT pg_advisory_xact_lock(273, 3)"))
            assert not await _accept(sessions, verify)
        assert called == []
    _run(postgres_seeded_database_url, scenario)


def test_rr_access_change_after_snapshot_is_40001_without_retry(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    from twobrain_rec_server.auth.sessions import revoke_auth_sessions
    from twobrain_rec_server.cabinet.result_projection_session import ResultAdmissionSession
    async def scenario(sessions):
        await _prepare(sessions)
        start = ResultAdmissionSession.start
        attempts, errors, called = [], [], []
        async def changed(owner):
            await start(owner)
            attempts.append(True)
            async with sessions() as writer:
                session = await writer.get(AuthSession, SESSION_ID)
                await revoke_auth_sessions(writer, [session])
                await writer.commit()
        monkeypatch.setattr(ResultAdmissionSession, "start", changed)
        def error(context):
            errors.append(context.original_exception.sqlstate)
        async def verify(*args):
            called.append(True)
        engine = sessions.kw["bind"].sync_engine
        event.listen(engine, "handle_error", error)
        try:
            assert not await _accept(sessions, verify)
        finally:
            event.remove(engine, "handle_error", error)
        assert attempts == [True] and errors == ["40001"] and called == []
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
    _run(postgres_seeded_database_url, scenario)


@pytest.mark.parametrize("phase", ["insert", "commit"])
def test_cancellation_during_actual_insert_or_deferred_commit_cleans_the_owned_transaction(
    postgres_seeded_database_url, result_period, phase,
):
    async def scenario(sessions):
        verify = await _prepare(sessions)
        entered = asyncio.Event()
        engine = sessions.kw["bind"].sync_engine
        def insert_entered(connection, cursor, sql, params, context, many):
            if sql.startswith("INSERT INTO product_activation_milestones"):
                entered.set()
        def commit_entered(connection):
            if result_period and connection is result_period[-1]._connection:
                entered.set()
        async with sessions() as blocker:
            if phase == "insert":
                from twobrain_rec_server.cabinet.web import (
                    build_first_result_viewed_product_analytics_payload,
                )
                from twobrain_rec_server.product_analytics.events import build_activation_event
                from twobrain_rec_server.product_analytics.identity import build_safe_identity
                payload = build_first_result_viewed_product_analytics_payload(
                    stable_pseudonymous_user_id=build_safe_identity(user_source_id=str(USER_ID)).stable_pseudonymous_user_id,
                    result_state="ready", useful_output_present=True, surface="synthetic",
                )
                value = build_activation_event(payload["event_name"],
                    stable_pseudonymous_user_id=payload["stable_pseudonymous_user_id"], properties=payload["properties"])
                await milestones.admit_account_milestone(blocker, value, account_id=USER_ID, source_kind="server")
            else:
                await blocker.execute(text("""CREATE FUNCTION t112_slow_commit() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN PERFORM pg_sleep(10); RETURN NEW; END $$"""))
                await blocker.execute(text("""CREATE CONSTRAINT TRIGGER t112_commit_wait
                    AFTER INSERT ON product_activation_milestones DEFERRABLE INITIALLY DEFERRED
                    FOR EACH ROW EXECUTE FUNCTION t112_slow_commit()"""))
                await blocker.commit()
            name, callback = ("before_cursor_execute", insert_entered) if phase == "insert" else ("commit", commit_entered)
            event.listen(engine, name, callback)
            task = asyncio.create_task(_accept(sessions, verify))
            try:
                await asyncio.wait_for(entered.wait(), 1.5)
                await asyncio.sleep(0.02)  # The observed statement is now waiting inside PostgreSQL.
                task.cancel()
                with pytest.raises(asyncio.CancelledError):
                    await task
            finally:
                event.remove(engine, name, callback)
                if not task.done():
                    task.cancel()
                    await asyncio.gather(task, return_exceptions=True)
                await blocker.rollback()
                if phase == "commit":
                    await blocker.execute(text("DROP TRIGGER t112_commit_wait ON product_activation_milestones"))
                    await blocker.execute(text("DROP FUNCTION t112_slow_commit()"))
                    await blocker.commit()
        owner = result_period[-1]
        assert not owner.db.in_transaction() and not owner.db.identity_map and not owner._listeners
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
        async with sessions() as db:
            assert not list(await db.scalars(select(ProductActivationMilestone)))
        assert await _accept(sessions, verify)
    _run(postgres_seeded_database_url, scenario)


def test_checkout_delay_consumes_original_deadline_without_a_background_tail(postgres_seeded_database_url, result_period):
    from sqlalchemy.util import await_only
    async def scenario(sessions):
        await _prepare(sessions)
        entered, called = [], []
        def delay(*args):
            entered.append(True)
            await_only(asyncio.sleep(10))
        async def verify(*args):
            called.append(True)
        engine = sessions.kw["bind"].sync_engine
        event.listen(engine, "do_connect", delay)
        start = asyncio.get_running_loop().time()
        try:
            assert not await ingest.ProductAnalyticsIngestService(Settings(
                product_analytics_enabled=True, web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
            )).admit_result_view(
                principal=_result_principal(), workspace_id=WORKSPACE_ID, sessionmaker=sessions,
                verify_view=verify, surface="cabinet_web", work_deadline=start + 0.2, cleanup_deadline=start + 0.7,
            )
        finally:
            event.remove(engine, "do_connect", delay)
        assert entered == [True] and not called and not result_period
        assert asyncio.get_running_loop().time() - start < 0.5
        assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
    _run(postgres_seeded_database_url, scenario)


def test_cleanup_timeout_after_commit_preserves_handed_off_pool_connection(
    postgres_seeded_database_url, result_period, monkeypatch,
):
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
    async def scenario(sessions):
        verify = await _prepare(sessions)
        engine = create_async_engine(postgres_seeded_database_url, pool_size=1, max_overflow=0)
        pooled = async_sessionmaker(engine, expire_on_commit=False)
        primitive = milestones.admit_account_milestone
        handoff = []
        try:
            async with pooled() as replacement:
                async def changed(db, value, **kwargs):
                    result = await primitive(db, value, **kwargs)
                    if value.event_name == "first_value_session_completed":
                        close = db.close
                        async def stalled_close():
                            await close()
                            await replacement.scalar(text("SELECT 1"))
                            connection = await replacement.connection()
                            handoff.append(connection.sync_connection.connection.driver_connection is result_period[-1]._driver)
                            await asyncio.sleep(10)
                        db.close = stalled_close
                    return result
                with monkeypatch.context() as patch:
                    patch.setattr(milestones, "admit_account_milestone", changed)
                    assert not await _accept(pooled, verify)
                assert handoff == [True]
                assert not result_period[-1]._driver.is_closed()
                assert await replacement.scalar(text("SELECT 2")) == 2
                assert not result_period[-1].db.in_transaction() and not result_period[-1]._listeners
            assert await _accept(pooled, verify)
            async with pooled() as db:
                assert len(list(await db.scalars(select(ProductActivationMilestone)))) == 2
            assert not [task for task in asyncio.all_tasks() if task is not asyncio.current_task() and not task.done()]
        finally:
            await engine.dispose()
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
            patch.setattr(milestones, "admit_account_milestone", admit)
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
    async def period(self, sessionmaker, *, work_deadline, cleanup_deadline):
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
    async def period(self, sessionmaker, *, work_deadline, cleanup_deadline):
        async with result_admission_session(
            sessionmaker, work_deadline=work_deadline, cleanup_deadline=cleanup_deadline,
        ) as owner:
            yield ingest._AccountAdmissionContext(owner.db, started_at=START, recheck=current, owner=owner)

    original = ingest.admit_account_milestone

    async def admit(db, event, **kwargs):
        nonlocal written
        row = await original(db, event, **kwargs)
        if event.event_name == "first_value_session_completed":
            written = True
        return row

    monkeypatch.setattr(ingest.ProductAnalyticsIngestService, "_result_period_context", period)
    monkeypatch.setattr(milestones, "admit_account_milestone", admit)

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

        monkeypatch.setattr(milestones, "admit_account_milestone", admit)
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
        outcomes = await asyncio.gather(*(_accept(sessions, verify) for _ in range(2)))
        assert any(outcomes)
        # RR serialization failure is unavailable; only a new showing may reconcile.
        assert await _accept(sessions, verify)
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
