"""Observer/scan/claim invariants; causal publication/expiry lives in notification_flow."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from tests.integration.test_billing_notification_flow import (
    billing_maintenance_probe_url as billing_maintenance_probe_url,
)
from tests.integration.test_billing_notification_flow import (
    rls_engine as rls_engine,
)
from tests.integration.test_rls_postgres_policies import _seed_probe_rows
from twobrain_rec_server.billing import storage_notifications as storage
from twobrain_rec_server.billing.storage import CANONICAL_PLAYBACK_PROFILE
from twobrain_rec_server.db.models import (
    BillingNotificationDelivery,
    BillingNotificationPreference,
    ExternalIdentity,
    MediaRevision,
    StorageNotificationScan,
    StorageNotificationState,
    TrackArtifact,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
from twobrain_rec_server.workflows import worker

pytestmark = [pytest.mark.strict_rls, pytest.mark.asyncio]

CONTEXT = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-storage",
                                 reason_category="storage-invariants", feature_area="billing")


@pytest.fixture
async def storage_case(rls_engine):
    ids = await _seed_probe_rows(rls_engine)
    sessions = create_sessionmaker(rls_engine)
    workspace, owner = ids["workspace_a"], ids["user_a"]
    async with sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        personal = await db.get(Workspace, workspace)
        personal.kind, personal.owner_user_id = "personal", owner
        email = ExternalIdentity(user_id=owner, provider="email", provider_subject=f"storage-{owner}",
                                 email="first@example.test", is_active=True, is_verified=True)
        revision = MediaRevision(id=uuid4(), workspace_id=workspace, meeting_id=ids["meeting_a"],
                                 local_media_revision_id="synthetic-history", status="accepted")
        db.add_all([email, revision])
        await db.flush()
        artifact = TrackArtifact(workspace_id=workspace, meeting_id=ids["meeting_a"], media_revision_id=revision.id,
                                 track_role="playback", codec="aac", sample_rate_hz=48000, channel_count=1,
                                 duration_seconds=60, byte_length=200_000_000, sha256="a" * 64,
                                 storage_object_key="synthetic/history/meeting-review.m4a", status="stored",
                                 normalization_profile_version=CANONICAL_PLAYBACK_PROFILE, validated_at=datetime.now(UTC),
                                 derivation_kind="uploaded_candidate", source_fingerprint_sha256="b" * 64,
                                 validation_version="playback_validator_v1")
        db.add(artifact)
        await db.flush()
    return SimpleNamespace(ids=ids, sessions=sessions, workspace=workspace, owner=owner,
                           artifact=artifact.id, email=email.id, engine=rls_engine)


async def observe(case):
    async with case.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        return await storage.observe_storage_workspace(db, workspace_id=case.workspace)


async def rows(case):
    async with case.sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        state = await db.get(StorageNotificationState, case.workspace)
        deliveries = list(await db.scalars(select(BillingNotificationDelivery).where(
            BillingNotificationDelivery.workspace_id == case.workspace,
            BillingNotificationDelivery.template_key == "storage_threshold",
        ).order_by(BillingNotificationDelivery.created_at, BillingNotificationDelivery.id)))
        scan = await db.get(StorageNotificationScan, 1)
        return state, deliveries, scan


async def edit_bytes(case, used):
    async with case.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        (await db.get(TrackArtifact, case.artifact)).byte_length = used


async def test_storage_transitions_and_transaction_rollback(storage_case):
    c = storage_case
    # Free without subscription, first high, no duplicates, individual rises and one jump.
    async with c.sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        assert await db.get(WorkspaceSubscription, c.workspace) is None
    await observe(c)
    for used in [200_000_000, 237_500_000, 250_000_000, 237_500_000, 200_000_000, 1, 250_000_000]:
        await edit_bytes(c, used)
        await observe(c)
    state, notices, _ = await rows(c)
    assert (state.band, state.generation) == ("100", 4)
    assert sorted(n.safe_payload["storage_level"] for n in notices) == ["100", "100", "80", "95"]
    await edit_bytes(c, 1)
    await observe(c)
    await edit_bytes(c, 200_000_000)
    async with c.sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        await storage.observe_storage_workspace(db, workspace_id=c.workspace)
        # A different session cannot see the uncommitted event or generation.
        assert len((await rows(c))[1]) == 4
        await db.rollback()
    assert (await rows(c))[0].band == "normal"
    await asyncio.gather(observe(c), observe(c))
    state, notices, _ = await rows(c)
    assert state.generation == 5 and len(notices) == 5
    assert len({n.event_id for n in notices}) == 5


@pytest.mark.parametrize("missing", ["email", "preference", "membership", "billing_owner"])
async def test_absence_advances_band_without_backlog_but_later_rise_is_new(storage_case, missing):
    c = storage_case
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        if missing == "email":
            (await db.get(ExternalIdentity, c.email)).is_verified = False
        elif missing == "preference":
            db.add(BillingNotificationPreference(user_id=c.owner, optional_email_enabled=False))
        elif missing == "membership":
            (await db.get(WorkspaceMembership, (c.workspace, c.owner))).status = "inactive"
        else:
            db.add(WorkspaceSubscription(workspace_id=c.workspace, plan_code="free", state="free",
                                         billing_owner_id=c.ids["user_b"]))
    await observe(c)
    assert (await rows(c))[0].band == "80" and not (await rows(c))[1]
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        if missing == "email":
            (await db.get(ExternalIdentity, c.email)).is_verified = True
        elif missing == "preference":
            (await db.get(BillingNotificationPreference, c.owner)).optional_email_enabled = True
        elif missing == "membership":
            (await db.get(WorkspaceMembership, (c.workspace, c.owner))).status = "active"
        else:
            (await db.get(WorkspaceSubscription, c.workspace)).billing_owner_id = c.owner
    await observe(c)
    assert not (await rows(c))[1]
    await edit_bytes(c, 237_500_000)
    await observe(c)
    assert [n.safe_payload["storage_level"] for n in (await rows(c))[1]] == ["95"]


async def test_owner_a_b_a_keeps_distinct_generations(storage_case):
    c = storage_case
    await observe(c)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        db.add(WorkspaceMembership(workspace_id=c.workspace, user_id=c.ids["user_b"], role="owner", status="active"))
        db.add(ExternalIdentity(user_id=c.ids["user_b"], provider="email", provider_subject="storage-b",
                               email="second@example.test", is_active=True, is_verified=True))
    for owner in [c.ids["user_b"], c.owner]:
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, CONTEXT)
            (await db.get(Workspace, c.workspace)).owner_user_id = owner
        await observe(c)
    state, notices, _ = await rows(c)
    assert state.generation == 3 and len({n.event_id for n in notices}) == 3
    assert sorted(str(n.recipient_id) for n in notices) == sorted(map(str, [c.owner, c.owner, c.ids["user_b"]]))


@pytest.mark.parametrize("n", [0, 1, 100, 101, 201])
async def test_finite_scan_covers_full_cohort_across_restarts(rls_engine, n):
    ids = await _seed_probe_rows(rls_engine)
    sessions = create_sessionmaker(rls_engine)
    async with sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        created = datetime.now(UTC) - timedelta(days=1)
        db.add_all([UserIdentity(id=UUID(int=1000 + i), organization_id=ids["org_a"],
                                 external_subject=f"scan-owner-{i}", display_name="Synthetic") for i in range(n)])
        await db.flush()
        db.add_all([Workspace(id=UUID(int=i + 1), organization_id=ids["org_a"], slug=f"scan-{i}",
                              name="Synthetic", kind="personal", owner_user_id=UUID(int=1000 + i), created_at=created)
                    for i in range(n)])
    started = asyncio.get_running_loop().time()
    results = []
    for _ in range((n + 99) // 100 + 1):
        # Recreate sessions like a restarted process; only committed cursor survives.
        result = await storage.reconcile_storage_notifications(create_sessionmaker(rls_engine), CONTEXT)
        results.append(result)
        if result["storage_finished"]:
            break
    assert sum(r["storage_attempted"] for r in results) == n
    assert results[-1]["storage_finished"] == 1
    assert all(r["storage_failed"] == 0 and r["storage_attempted"] <= 100 for r in results)
    async with sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        scan = await db.get(StorageNotificationScan, 1)
        assert scan.cycle_started_at is scan.upper_workspace_id is scan.after_workspace_id is None
        assert scan.last_finished_summary["attempted"] == n
        assert scan.last_finished_summary["incomplete"] is False
    assert asyncio.get_running_loop().time() - started < 60


async def test_snapshot_error_rolls_back_state_and_advances_only_cursor(storage_case, monkeypatch):
    c = storage_case
    await observe(c)
    initial = (await rows(c))[0]
    await edit_bytes(c, 237_500_000)
    original = storage.enqueue_billing_event

    async def fail_after_enqueue(*args, **kwargs):
        await original(*args, **kwargs)
        raise ValueError("private synthetic snapshot failure")

    with monkeypatch.context() as patch:
        patch.setattr(storage, "enqueue_billing_event", fail_after_enqueue)
        result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    state, notices, scan = await rows(c)
    assert result["storage_failed"] == 1 and result["storage_incomplete"] == 1
    assert (state.band, state.generation, state.observed_at) == (initial.band, initial.generation, initial.observed_at)
    assert len(notices) == 1
    summary = scan.last_finished_summary
    assert summary["failed"] == 1 and summary["incomplete"] is True
    result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    assert result["storage_observed"] == 1
    assert len((await rows(c))[1]) == 2


@pytest.mark.parametrize("interrupt", ["cancel", "deadline", "database"])
async def test_scan_interruption_does_not_claim_uncommitted_progress(storage_case, monkeypatch, interrupt):
    c = storage_case
    original = storage.observe_storage_workspace
    entered = asyncio.Event()

    async def interrupted(db, **kwargs):
        await original(db, **kwargs)
        entered.set()
        if interrupt == "database":
            # Simulate a broken connection, which cannot be isolated by a savepoint.
            from sqlalchemy.exc import DBAPIError
            raise DBAPIError(None, None, Exception("synthetic"), connection_invalidated=True)
        await asyncio.sleep(10)

    monkeypatch.setattr(storage, "observe_storage_workspace", interrupted)
    if interrupt == "deadline":
        monkeypatch.setattr(storage, "STORAGE_SCAN_TIMEOUT", 0.1)
        result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
        assert result["storage_incomplete"] == 1 and result["storage_attempted"] == 0
    elif interrupt == "database":
        with pytest.raises(SQLAlchemyError):
            await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    else:
        task = asyncio.create_task(storage.reconcile_storage_notifications(c.sessions, CONTEXT))
        await entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    state, notices, scan = await rows(c)
    assert state is None and notices == [] and scan is None


async def dispatch(case, monkeypatch, send):
    async def stop(_seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "create_engine", lambda _: case.engine)
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _: case.sessions)
    monkeypatch.setattr(worker, "send_billing_notification", send)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    with pytest.raises(asyncio.CancelledError):
        await worker.run_billing_notification_reconciler(SimpleNamespace(
            billing_support_email=None, public_base_url="https://graf.example.test"))


@pytest.mark.parametrize("lost", ["email", "preference", "membership", "billing_owner", "owner", "closed", "merged"])
@pytest.mark.parametrize("after_selection", [False, True])
async def test_storage_claim_rechecks_original_recipient(storage_case, monkeypatch, lost, after_selection):
    c = storage_case
    await observe(c)
    real_lock = worker.lock_storage_workspace
    changed = False

    async def lose_access():
        nonlocal changed
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, CONTEXT)
            if lost == "email":
                (await db.get(ExternalIdentity, c.email)).is_verified = False
            elif lost == "preference":
                db.add(BillingNotificationPreference(user_id=c.owner, optional_email_enabled=False))
            elif lost == "membership":
                (await db.get(WorkspaceMembership, (c.workspace, c.owner))).role = "member"
            elif lost == "billing_owner":
                db.add(WorkspaceSubscription(workspace_id=c.workspace, plan_code="free", state="free",
                                             billing_owner_id=c.ids["user_b"]))
            elif lost == "owner":
                (await db.get(Workspace, c.workspace)).owner_user_id = c.ids["user_b"]
            elif lost == "closed":
                (await db.get(UserIdentity, c.owner)).status = "closed"
            else:
                (await db.get(UserIdentity, c.owner)).merged_into_user_id = c.ids["user_b"]
        changed = True

    async def before_claim(db, workspace_id):
        if not changed:
            await lose_access()
        await real_lock(db, workspace_id)

    if after_selection:
        monkeypatch.setattr(worker, "lock_storage_workspace", before_claim)
    else:
        await lose_access()

    async def forbid_send(**kwargs):
        raise AssertionError("ineligible storage recipient must be suppressed")

    await dispatch(c, monkeypatch, forbid_send)
    notice = (await rows(c))[1][0]
    assert notice.state == "suppressed" and notice.attempts == 0


@pytest.mark.parametrize("metadata", ["bad", True, -1, 9223372036854775808, "9" * 200, {}, [], "9223372036854775807"])
async def test_malformed_retry_metadata_is_terminal_without_breaking_poll(storage_case, monkeypatch, metadata):
    c = storage_case
    await observe(c)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        notice = (await db.scalars(select(BillingNotificationDelivery))).one()
        notice.safe_payload = {**notice.safe_payload, "_retry_not_before": metadata}

    async def forbid_send(**kwargs):
        raise AssertionError("invalid retry metadata cannot send")

    await dispatch(c, monkeypatch, forbid_send)
    notice = (await rows(c))[1][0]
    assert notice.state == "suppressed" and notice.attempts == 0


async def test_exhausted_storage_retry_never_makes_sixth_attempt(storage_case, monkeypatch):
    c = storage_case
    await observe(c)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        notice = (await db.scalars(select(BillingNotificationDelivery))).one()
        notice.attempts, notice.state = 5, "retry"

    async def forbid_send(**kwargs):
        raise AssertionError("sixth storage attempt forbidden")

    await dispatch(c, monkeypatch, forbid_send)
    notice = (await rows(c))[1][0]
    assert notice.state == "failed" and notice.attempts == 5


async def test_unknown_plan_preserves_snapshot_and_reports_incomplete(storage_case):
    c = storage_case
    await observe(c)
    initial = (await rows(c))[0]
    await edit_bytes(c, 250_000_000)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        db.add(WorkspaceSubscription(workspace_id=c.workspace, billing_owner_id=c.owner,
                                     plan_code="unknown-future", state="free"))
    result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    state, notices, scan = await rows(c)
    assert result["storage_failed"] == result["storage_incomplete"] == 1
    assert scan.last_error_code == "snapshot_unavailable"
    assert (state.band, state.generation, state.observed_at) == (initial.band, initial.generation, initial.observed_at)
    assert len(notices) == 1


@pytest.mark.parametrize("plan,field", [("trial", "trial_ends_at"), ("personal", "paid_through")])
@pytest.mark.parametrize("cutoff", [None, "infinity", "-infinity"])
async def test_unknown_capacity_cutoff_preserves_snapshot(storage_case, plan, field, cutoff):
    c = storage_case
    await observe(c)
    initial = (await rows(c))[0]
    await edit_bytes(c, 250_000_000)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        db.add(WorkspaceSubscription(workspace_id=c.workspace, billing_owner_id=c.owner,
                                     plan_code=plan, state=plan))
        await db.flush()
        # The field is a fixed parameter above; only this synthetic row changes.
        await db.execute(text(f"UPDATE workspace_subscriptions SET {field} = CAST(CAST(:cutoff AS text) AS timestamptz) "
                              "WHERE workspace_id = :workspace"),
                         {"cutoff": cutoff, "workspace": c.workspace})
    result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    state, notices, scan = await rows(c)
    assert result["storage_failed"] == result["storage_incomplete"] == 1
    assert scan.last_error_code == "snapshot_unavailable"
    assert (state.band, state.generation, state.observed_at) == (initial.band, initial.generation, initial.observed_at)
    assert len(notices) == 1


@pytest.mark.parametrize("writer", ["preference_absent", "preference_existing", "unlink", "membership", "closed"])
async def test_eligibility_locks_serialize_with_writers_before_committed_claim(storage_case, monkeypatch, writer):
    c = storage_case
    if writer == "preference_existing":
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, CONTEXT)
            db.add(BillingNotificationPreference(user_id=c.owner, optional_email_enabled=True))
    await observe(c)
    original = worker.storage_notice_owner
    guard_read, release_claim, mutation_started, mutation_finished = (asyncio.Event() for _ in range(4))

    async def guard(db, **kwargs):
        result = await original(db, **kwargs)
        guard_read.set()
        await release_claim.wait()
        return result

    async def mutate():
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, CONTEXT)
            mutation_started.set()
            if writer.startswith("preference"):
                from twobrain_rec_server.cabinet.web_routes.settings import (
                    _save_notification_preferences,
                )
                await _save_notification_preferences(db, user_id=c.owner,
                                                    form={"optional_email_enabled": "false"})
            elif writer == "unlink":
                identity = await db.get(ExternalIdentity, c.email, with_for_update=True)
                identity.is_verified = identity.is_active = False
            elif writer == "membership":
                (await db.get(WorkspaceMembership, (c.workspace, c.owner), with_for_update=True)).role = "member"
            else:
                (await db.get(UserIdentity, c.owner, with_for_update=True)).status = "closed"
        mutation_finished.set()

    calls = []

    async def send(**kwargs):
        async with c.sessions() as db:
            await apply_tenant_context(db, CONTEXT)
            notice = (await db.scalars(select(BillingNotificationDelivery))).one()
            assert notice.state == "failed" and notice.last_error_code == "postal_outcome_unknown"
        calls.append(kwargs)

    monkeypatch.setattr(worker, "storage_notice_owner", guard)
    task = asyncio.create_task(dispatch(c, monkeypatch, send))
    await asyncio.wait_for(guard_read.wait(), 3)
    writer_task = asyncio.create_task(mutate())
    try:
        await mutation_started.wait()
        await asyncio.sleep(0.05)
        assert not mutation_finished.is_set(), "a withdrawal cannot commit between guard and claim"
        release_claim.set()
        await asyncio.wait_for(task, 3)
        await asyncio.wait_for(writer_task, 3)
        assert len(calls) == 1 and mutation_finished.is_set()
    finally:
        release_claim.set()
        for pending in (task, writer_task):
            if not pending.done():
                pending.cancel()
        await asyncio.gather(task, writer_task, return_exceptions=True)


@pytest.mark.parametrize("failure", ["guard", "known_postal", "unknown_postal"])
async def test_storage_retry_is_durable_bounded_and_unknown_is_never_replayed(storage_case, monkeypatch, failure):
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError

    c = storage_case
    await observe(c)
    clock = datetime.now(UTC)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz else clock.replace(tzinfo=None)

    monkeypatch.setattr(worker, "datetime", Clock)
    calls = []
    if failure == "guard":
        async def failed_guard(*args, **kwargs):
            raise SQLAlchemyError("synthetic private read failure")
        monkeypatch.setattr(worker, "storage_notice_owner", failed_guard)

    async def failed_transport(**kwargs):
        calls.append(kwargs)
        raise EmailLoginDeliveryError("synthetic", retryable=True, outcome_unknown=failure == "unknown_postal")

    for attempt in range(1, 6):
        await dispatch(c, monkeypatch, failed_transport)
        notice = (await rows(c))[1][0]
        if failure == "unknown_postal":
            assert notice.attempts == 1 and notice.state == "failed"
            assert notice.last_error_code == "postal_outcome_unknown"
        else:
            assert notice.attempts == attempt
            assert notice.state == ("retry" if attempt < 5 else "failed")
            if attempt < 5:
                assert notice.safe_payload["_retry_not_before"] >= clock.timestamp() + 60
        # Restart before the saved deadline cannot consume another attempt.
        await dispatch(c, monkeypatch, failed_transport)
        assert (await rows(c))[1][0].attempts == notice.attempts
        clock += timedelta(seconds=61)
    await dispatch(c, monkeypatch, failed_transport)
    assert len(calls) == {"guard": 0, "known_postal": 5, "unknown_postal": 1}[failure]


async def test_preexisting_identity_writer_causes_retry_then_suppression(storage_case, monkeypatch):
    c = storage_case
    await observe(c)

    async def forbid_send(**kwargs):
        raise AssertionError("a pre-claim identity conflict cannot send")

    async with c.sessions.begin() as writer:
        await apply_tenant_context(writer, CONTEXT)
        identity = await writer.get(UserIdentity, c.owner, with_for_update=True)
        identity.status = "closed"
        await writer.flush()
        await asyncio.wait_for(dispatch(c, monkeypatch, forbid_send), 3)
        notice = (await rows(c))[1][0]
        assert notice.state == "retry" and notice.attempts == 1
    # Saved retry remains delayed even though the writer has now committed.
    await dispatch(c, monkeypatch, forbid_send)
    assert (await rows(c))[1][0].attempts == 1


async def test_row_lock_timeout_moves_cursor_and_next_cycle_recovers(storage_case):
    c = storage_case
    await observe(c)
    async with c.sessions.begin() as blocker:
        await apply_tenant_context(blocker, CONTEXT)
        await blocker.get(Workspace, c.workspace, with_for_update=True)
        result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
        assert result["storage_failed"] == 1 and result["storage_finished"] == 1
        state, notices, scan = await rows(c)
        assert state.generation == 1 and len(notices) == 1
        assert scan.last_error_code == "lock_timeout" and scan.last_finished_summary["incomplete"] is True
    assert (await storage.reconcile_storage_notifications(c.sessions, CONTEXT))["storage_observed"] == 1


async def test_scan_cutoff_and_late_commits_do_not_starve_original_cohort(rls_engine, monkeypatch):
    ids = await _seed_probe_rows(rls_engine)
    sessions = create_sessionmaker(rls_engine)
    base = datetime.now(UTC) - timedelta(days=1)

    async def add(db, number, created_at):
        owner = UUID(int=1000 + number)
        db.add(UserIdentity(id=owner, organization_id=ids["org_a"], external_subject=f"insert-{number}", display_name="Synthetic"))
        await db.flush()
        db.add(Workspace(id=UUID(int=number), organization_id=ids["org_a"], slug=f"insert-{number}",
                         name="Synthetic", kind="personal", owner_user_id=owner, created_at=created_at))
        await db.flush()

    async with sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        for i in (10, 20, 30):
            await add(db, i, base)
    monkeypatch.setattr(storage, "STORAGE_SCAN_LIMIT", 1)
    async with sessions.begin() as late:
        await apply_tenant_context(late, CONTEXT)
        await add(late, 5, base)  # Older, but not visible until after cursor passes it.
        first = await storage.reconcile_storage_notifications(sessions, CONTEXT)
        assert first["storage_attempted"] == 1
        async with sessions.begin() as new:
            await apply_tenant_context(new, CONTEXT)
            await add(new, 15, datetime.now(UTC))  # New after cutoff, despite UUID ahead.
            await add(new, 25, base)  # Old created_at committed ahead enters as L.
    results = [await storage.reconcile_storage_notifications(sessions, CONTEXT) for _ in range(4)]
    assert sum(r["storage_attempted"] for r in results) == 3  # 20,25,30; +one finish.
    assert results[-1]["storage_finished"] == 1
    async with sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        states = set(await db.scalars(select(StorageNotificationState.workspace_id)))
        assert states == {UUID(int=i) for i in (10, 20, 25, 30)}
    for _ in range(7):
        await storage.reconcile_storage_notifications(sessions, CONTEXT)
    async with sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        assert set(await db.scalars(select(StorageNotificationState.workspace_id))) == {UUID(int=i) for i in (5,10,15,20,25,30)}


async def test_storage_force_rls_and_bootstrap_preserve_minimum_grants(
    storage_case, postgres_isolated_cluster_database_url, billing_maintenance_probe_url, monkeypatch,
):
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine

    from scripts import bootstrap_runtime_database_roles as bootstrap
    from tests.integration.test_rls_postgres_policies import _create_probe_role
    from twobrain_rec_server.billing.database import (
        BillingMaintenanceDatabaseError,
        require_billing_maintenance_database,
    )

    c = storage_case
    owner_url, maintenance_url = map(make_url, [postgres_isolated_cluster_database_url, billing_maintenance_probe_url])
    passwords = {"TWOBRAIN_DB_OWNER_PASSWORD_FILE": owner_url.password,
                 "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE": maintenance_url.password,
                 "TWOBRAIN_DB_APP_PASSWORD_FILE": uuid4().hex, "TWOBRAIN_DB_MEDIA_PASSWORD_FILE": uuid4().hex}
    monkeypatch.setattr(bootstrap, "_read_secret", passwords.__getitem__)
    for key, value in {"HOST": owner_url.host, "PORT": str(owner_url.port), "NAME": owner_url.database}.items():
        monkeypatch.setenv(f"TWOBRAIN_DB_{key}", value)
    for _ in range(2):
        await bootstrap._bootstrap()
    await observe(c)
    admin = create_async_engine(postgres_isolated_cluster_database_url)
    try:
        async with admin.connect() as conn:
            flags = (await conn.execute(text("select relrowsecurity,relforcerowsecurity from pg_class where relname in ('storage_notification_states','storage_notification_scan')"))).all()
            assert flags == [(True, True), (True, True)]
            for table in ("storage_notification_states", "storage_notification_scan"):
                for role in ("twobrain_rec_app", "twobrain_rec_media"):
                    assert await conn.scalar(text("select not has_table_privilege(:role,:table,'SELECT,INSERT,UPDATE,DELETE')"), {"role": role, "table": table})
                assert await conn.scalar(text("select has_table_privilege('twobrain_rec_maintenance',:table,'SELECT,INSERT,UPDATE')"), {"table": table})
            assert not await conn.scalar(text("select has_table_privilege('twobrain_rec_maintenance','storage_notification_scan','DELETE')"))
        async with create_sessionmaker(admin)() as db:
            await apply_tenant_context(db, CONTEXT)
            with pytest.raises(BillingMaintenanceDatabaseError):
                await require_billing_maintenance_database(db)
        for role, key in [("twobrain_rec_app", "TWOBRAIN_DB_APP_PASSWORD_FILE"), ("twobrain_rec_media", "TWOBRAIN_DB_MEDIA_PASSWORD_FILE")]:
            engine = create_async_engine(owner_url.set(username=role, password=passwords[key]))
            try:
                async with create_sessionmaker(engine)() as db:
                    await apply_tenant_context(db, CONTEXT)
                    with pytest.raises(SQLAlchemyError):
                        await db.scalar(select(StorageNotificationState))
            finally:
                await engine.dispose()
        for context in [None, MaintenanceTenantContext(operation_name="migration_verification", actor_id="test", reason_category="wrong", feature_area="billing"),
                        MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test", reason_category="wrong", feature_area="security")]:
            async with c.sessions() as db:
                if context:
                    await apply_tenant_context(db, context)
                assert await db.scalar(select(StorageNotificationState)) is None
                assert await db.scalar(select(StorageNotificationScan)) is None
        async with c.sessions() as db:
            await apply_tenant_context(db, CONTEXT)
            await db.execute(text("SET LOCAL row_security=off"))
            with pytest.raises(SQLAlchemyError):
                await db.scalar(select(StorageNotificationState))
        # SET ROLE cannot replace the authenticated login identity.
        role, password = await _create_probe_role(postgres_isolated_cluster_database_url, role_name="storage_impersonator")
        async with admin.begin() as conn:
            await conn.execute(text("grant twobrain_rec_maintenance to storage_impersonator"))
        engine = create_async_engine(owner_url.set(username=role, password=password))
        try:
            async with create_sessionmaker(engine)() as db:
                await db.execute(text("SET LOCAL ROLE twobrain_rec_maintenance"))
                await apply_tenant_context(db, CONTEXT)
                assert await db.scalar(select(StorageNotificationState)) is None
                with pytest.raises(BillingMaintenanceDatabaseError):
                    await require_billing_maintenance_database(db)
        finally:
            await engine.dispose()
        # Account can read/delete states, but cannot insert/update or touch cursor.
        account = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-account",
                                           reason_category="finalize", feature_area="account")
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, account)
            assert await db.get(StorageNotificationState, c.workspace) is not None
            assert await db.scalar(select(StorageNotificationScan)) is None
            assert (await db.execute(text("update storage_notification_states set generation=99"))).rowcount == 0
            assert (await db.execute(text("delete from storage_notification_states"))).rowcount == 1
    finally:
        await admin.dispose()


async def test_storage_schema_checks_and_summary_are_closed(storage_case):
    import json

    c = storage_case
    await observe(c)
    summary = {"started_at": "2026-11-11T00:00:00+00:00", "finished_at": "2026-11-11T00:01:00+00:00",
               "attempted": 2, "observed": 1, "skipped": 0, "failed": 1, "incomplete": True}
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        for key, value in [("attempted", -1), ("failed", 1.5), ("incomplete", False), ("private", "forbidden"),
                           ("finished_at", "2025-01-01T00:00:00Z"), ("started_at", "infinityZ"),
                           ("started_at", "2026-11-11T00:00:00+03:00"), ("observed", None)]:
            assert await db.scalar(text("select rec_storage_scan_summary_valid(cast(:v as jsonb))"), {"v": json.dumps({**summary, key: value})}) is False
        assert await db.scalar(text("select rec_storage_scan_summary_valid(cast(:v as jsonb))"), {"v": json.dumps(summary)}) is True
        for statement in ["update storage_notification_states set band='81'", "update storage_notification_states set generation=-1",
                          "update storage_notification_states set observed_at='infinity'",
                          "insert into storage_notification_scan (id) values(2)",
                          "insert into storage_notification_scan (id,attempted) values(1,1)",
                          "insert into storage_notification_scan (id,last_error_code) values(1,'private-error')",
                          "insert into storage_notification_scan (id,cycle_started_at) values(1,now())"]:
            with pytest.raises(SQLAlchemyError):
                async with db.begin_nested():
                    await db.execute(text(statement))


async def test_begin_finalization_cleans_frozen_state_atomically_without_resurrection(storage_case, monkeypatch):
    from twobrain_rec_server.auth.account_closure import begin_account_close_finalization
    from twobrain_rec_server.db.models import AccountClosureRequest

    c = storage_case
    await observe(c)
    now = datetime.now(UTC)
    account = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-close",
                                       reason_category="finalize", feature_area="account")
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, account)
        closure = AccountClosureRequest(workspace_id=c.workspace, requested_by_user_id=c.owner,
                                         request_key="synthetic", state="scheduled", finalize_at=now)
        db.add(closure)
        await db.flush()
    async with c.sessions() as db:
        await apply_tenant_context(db, account)
        await begin_account_close_finalization(db, request_id=closure.id, now=now)
        # Closed/state cleanup is one transaction and still invisible before commit.
        assert (await rows(c))[0] is not None
        await db.rollback()
    assert (await rows(c))[0] is not None
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, account)
        await begin_account_close_finalization(db, request_id=closure.id, now=now)
    assert (await rows(c))[0] is None
    assert await observe(c) == "skipped"
    # Frozen blocked/retry re-entry also cannot recreate state.
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, account)
        (await db.get(AccountClosureRequest, closure.id)).state = "blocked"
        await begin_account_close_finalization(db, request_id=closure.id, now=now)
    assert await observe(c) == "skipped" and (await rows(c))[0] is None

    async def forbid_send(**kwargs):
        raise AssertionError("closed account cannot send")
    await dispatch(c, monkeypatch, forbid_send)
    assert (await rows(c))[1][0].state == "suppressed"


async def test_failed_savepoint_concurrent_finalizer_cannot_resurrect_state(storage_case, monkeypatch):
    from twobrain_rec_server.auth.account_closure import begin_account_close_finalization
    from twobrain_rec_server.db.models import AccountClosureRequest

    c = storage_case
    await observe(c)
    await edit_bytes(c, 237_500_000)
    now = datetime.now(UTC)
    account = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-close-race",
                                       reason_category="finalize", feature_area="account")
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, account)
        closure = AccountClosureRequest(workspace_id=c.workspace, requested_by_user_id=c.owner,
                                         request_key="race", state="scheduled", finalize_at=now)
        db.add(closure)
        await db.flush()
    snapshot_written, release, closing = asyncio.Event(), asyncio.Event(), asyncio.Event()
    original = storage.observe_storage_workspace

    async def fail_snapshot(db, **kwargs):
        await original(db, **kwargs)
        snapshot_written.set()
        await release.wait()
        raise ValueError("synthetic snapshot rollback")

    async def finalize():
        async with c.sessions.begin() as db:
            await apply_tenant_context(db, account)
            closing.set()
            await begin_account_close_finalization(db, request_id=closure.id, now=now)

    monkeypatch.setattr(storage, "observe_storage_workspace", fail_snapshot)
    observer = asyncio.create_task(storage.reconcile_storage_notifications(c.sessions, CONTEXT))
    await asyncio.wait_for(snapshot_written.wait(), 3)
    finalizer = asyncio.create_task(finalize())
    try:
        await closing.wait()
        await asyncio.sleep(0.05)
        assert not finalizer.done()
        release.set()
        result, _ = await asyncio.wait_for(asyncio.gather(observer, finalizer), 5)
        assert result["storage_failed"] == 1 and result["storage_incomplete"] == 1
        state, notices, scan = await rows(c)
        assert state is None and len(notices) == 1
        assert scan.last_finished_summary["failed"] == 1
    finally:
        release.set()
        for task in (observer, finalizer):
            if not task.done():
                task.cancel()
        await asyncio.gather(observer, finalizer, return_exceptions=True)


async def test_storage_migration_roundtrip_refuses_nonempty_and_restore_keeps_generations(
    storage_case, postgres_isolated_cluster_database_url, tmp_path, monkeypatch,
):
    import subprocess
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.engine import make_url
    from sqlalchemy.ext.asyncio import create_async_engine

    from twobrain_rec_server.config import get_settings

    c = storage_case
    server = Path(__file__).resolve().parents[2]
    config = Config(str(server / "alembic.ini"))
    config.set_main_option("script_location", str(server / "src/twobrain_rec_server/db/migrations"))
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_isolated_cluster_database_url)
    get_settings.cache_clear()
    parsed = make_url(postgres_isolated_cluster_database_url)
    container = None
    for candidate in subprocess.check_output(["docker", "ps", "--filter", "name=graf-postgres-test-bootstrap-", "--format", "{{.Names}}"], text=True).split():
        if subprocess.check_output(["docker", "port", candidate, "5432/tcp"], text=True).strip() == f"127.0.0.1:{parsed.port}":
            container = candidate
            break
    assert container is not None
    restored_name = f"test_storage_restore_{uuid4().hex}"
    dump = tmp_path / "synthetic-storage.dump"
    created = False

    def docker(*args, **kwargs):
        result = subprocess.run(["docker", "exec", container, *args], capture_output=True, timeout=30, **kwargs)
        assert result.returncode == 0, "synthetic storage backup command failed"
        return result

    try:
        await asyncio.to_thread(command.downgrade, config, "0111_receipt_observation_deltas")
        await asyncio.to_thread(command.upgrade, config, "head")
        await observe(c)
        await edit_bytes(c, 1)
        await observe(c)
        await edit_bytes(c, 200_000_000)
        await observe(c)
        await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
        expected_state, expected_notices, expected_scan = await rows(c)
        assert expected_state.generation == 2 and len(expected_notices) == 2
        with pytest.raises(SQLAlchemyError, match="storage notification state exists"):
            await asyncio.to_thread(command.downgrade, config, "0111_receipt_observation_deltas")
        dump.write_bytes(docker("pg_dump", "-U", "twobrain_rec", "-d", parsed.database, "--format=custom").stdout)
        docker("createdb", "-U", "twobrain_rec", restored_name)
        created = True
        result = subprocess.run(["docker", "exec", "-i", container, "pg_restore", "-U", "twobrain_rec", "-d", restored_name],
                                input=dump.read_bytes(), capture_output=True, timeout=30)
        assert result.returncode == 0, "synthetic storage restore failed"
        restored_url = c.engine.url.set(database=restored_name)
        engine = create_async_engine(restored_url)
        try:
            restored = SimpleNamespace(sessions=create_sessionmaker(engine), workspace=c.workspace)
            state, notices, scan = await rows(restored)
            assert (state.band, state.generation, state.owner_user_id) == (expected_state.band, 2, c.owner)
            assert {n.event_id for n in notices} == {n.event_id for n in expected_notices}
            assert scan.last_finished_summary == expected_scan.last_finished_summary
            assert (await storage.reconcile_storage_notifications(restored.sessions, CONTEXT))["storage_observed"] == 1
            assert len((await rows(restored))[1]) == 2
        finally:
            await engine.dispose()
    finally:
        if created:
            docker("dropdb", "-U", "twobrain_rec", "--force", restored_name)
        dump.unlink(missing_ok=True)
        get_settings.cache_clear()


async def test_query_timeout_rolls_back_only_candidate_and_preserves_finished_summary(storage_case, monkeypatch):
    c = storage_case
    await observe(c)
    initial = (await rows(c))[0]
    original = storage.observe_storage_workspace

    async def query_timeout(db, **kwargs):
        await original(db, **kwargs)
        await db.execute(text("select pg_sleep(3)"))

    with monkeypatch.context() as patch:
        patch.setattr(storage, "observe_storage_workspace", query_timeout)
        result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    state, notices, scan = await rows(c)
    assert result["storage_failed"] == result["storage_incomplete"] == 1
    assert scan.last_error_code == "query_timeout"
    assert (state.band, state.generation, state.observed_at) == (initial.band, initial.generation, initial.observed_at)
    summary = scan.last_finished_summary
    monkeypatch.setattr(storage, "STORAGE_SCAN_LIMIT", 1)
    result = await storage.reconcile_storage_notifications(c.sessions, CONTEXT)
    assert result["storage_observed"] == 1 and result["storage_finished"] == 0
    assert (await rows(c))[2].last_finished_summary == summary


async def test_concurrent_scans_and_lost_commit_ack_do_not_repeat_notice(storage_case):
    from sqlalchemy import event

    c = storage_case
    seen = False

    def lost_ack(session):
        nonlocal seen
        if not seen and not session.in_nested_transaction():
            seen = True
            raise RuntimeError("synthetic lost commit acknowledgement")

    # A commit that reached PostgreSQL but lost its response remains durable.
    # The subsequent process must recover from the cursor/state, not replay it.
    session = c.sessions()
    event.listen(session.sync_session, "after_commit", lost_ack)

    def one_session():
        return session

    with pytest.raises(RuntimeError, match="lost commit acknowledgement"):
        await storage.reconcile_storage_notifications(one_session, CONTEXT)
    committed_state, committed_notices, committed_scan = await rows(c)
    assert committed_state.generation == 1 and len(committed_notices) == 1
    assert committed_scan.attempted == 1
    result = await asyncio.gather(storage.reconcile_storage_notifications(c.sessions, CONTEXT),
                                  storage.reconcile_storage_notifications(c.sessions, CONTEXT))
    state, notices, scan = await rows(c)
    assert state.generation == 1 and len(notices) == 1
    assert sum(r["storage_failed"] for r in result) == 0


async def test_physical_workspace_delete_cascades_only_its_state(storage_case):
    c = storage_case
    await observe(c)
    workspace, owner = uuid4(), uuid4()
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        db.add(UserIdentity(id=owner, organization_id=c.ids["org_a"], external_subject=str(owner), display_name="Synthetic"))
        await db.flush()
        db.add(Workspace(id=workspace, organization_id=c.ids["org_a"], slug=str(workspace), name="Synthetic",
                         kind="personal", owner_user_id=owner))
        await db.flush()
        await storage.observe_storage_workspace(db, workspace_id=workspace)
    async with c.sessions.begin() as db:
        await apply_tenant_context(db, CONTEXT)
        assert await db.get(StorageNotificationState, workspace) is not None
        await db.execute(text("delete from workspaces where id=:id"), {"id": workspace})
    async with c.sessions() as db:
        await apply_tenant_context(db, CONTEXT)
        assert await db.get(StorageNotificationState, workspace) is None
        assert await db.get(StorageNotificationState, c.workspace) is not None
