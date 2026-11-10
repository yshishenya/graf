import pytest

from twobrain_rec_server.billing.events import BillingEvent, notification_kind_for
from twobrain_rec_server.billing.notifications import (
    BillingNotification,
    build_notification,
    notification_copy,
)


@pytest.mark.parametrize("event_type", tuple(BillingEvent))
def test_every_allowlisted_lifecycle_event_has_bounded_russian_copy(event_type: BillingEvent) -> None:
    kind = notification_kind_for(event_type)
    event = build_notification(
        event_id=f"{event_type.value}:synthetic-1",
        kind=kind,
        payload={"invoice": "INV-1", "action_path": "/billing"},
    )
    title, body = notification_copy(event)
    assert title and body
    assert "synthetic" not in title.lower()
    assert "provider" not in body.lower()
    assert event.safe_payload.get("action_path") == "/billing"


def test_refund_and_unknown_provider_events_are_not_customer_notifications() -> None:
    assert BillingNotification.RECEIPT_AVAILABLE in {
        notification_kind_for(BillingEvent.RECEIPT_AVAILABLE)
    }
    with pytest.raises(ValueError):
        notification_kind_for("refund.succeeded")
    with pytest.raises(ValueError):
        notification_kind_for("provider.unknown")


pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_trial_lifecycle_uses_current_owner_and_exact_windows(rls_engine, monkeypatch):
    import asyncio
    from datetime import UTC, datetime, timedelta
    from types import SimpleNamespace
    from uuid import UUID

    from sqlalchemy import select, text

    from tests.integration.test_rls_postgres_policies import _request_context, _seed_probe_rows
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
    from twobrain_rec_server.billing.trial_notifications import (
        enqueue_due_trial_notices,
        enqueue_trial_started,
        trial_notice_recipient,
    )
    from twobrain_rec_server.db.models import (
        BillingNotificationDelivery,
        BillingNotificationPreference,
        ExternalIdentity,
        TrialActivation,
        Workspace,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
    from twobrain_rec_server.workflows import worker

    ids = await _seed_probe_rows(rls_engine)
    owner, workspace = ids["user_a"], ids["workspace_a"]
    sessions = create_sessionmaker(rls_engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="test-trial",
        reason_category="trial-notices",
        feature_area="billing",
    )
    start = datetime(2026, 8, 1, 12, tzinfo=UTC)
    end = start + timedelta(days=7)
    clock = start
    calls = []
    failure = None

    class TrialClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz else clock.replace(tzinfo=None)

    async def stop_cycle(_seconds):
        raise asyncio.CancelledError()

    async def send(**kwargs):
        async with sessions() as db:
            await apply_tenant_context(db, context)
            notice = await db.scalar(select(BillingNotificationDelivery).where(
                BillingNotificationDelivery.id == UUID(kwargs["delivery_key"].split(":", 1)[1])
            ))
            assert notice.state == "failed" and notice.last_error_code == "postal_outcome_unknown"
        calls.append(kwargs)
        if failure is not None:
            raise EmailLoginDeliveryError(
                "synthetic retry", retryable=True, outcome_unknown=(failure == "unknown")
            )

    monkeypatch.setattr(worker, "datetime", TrialClock)
    monkeypatch.setattr(worker, "create_engine", lambda settings: rls_engine)
    monkeypatch.setattr(worker, "send_billing_notification", send)

    async def dispatch():
        # The worker and the SQL assertions use separate transactions.
        with monkeypatch.context() as cycle:
            cycle.setattr(worker.asyncio, "sleep", stop_cycle)
            with pytest.raises(asyncio.CancelledError):
                await worker.run_billing_notification_reconciler(SimpleNamespace(
                    billing_support_email=None, public_base_url="https://graf.example.test"
                ))

    async def poll(at):
        async with sessions.begin() as db:
            await apply_tenant_context(db, context)
            await enqueue_due_trial_notices(db, now=at)

    async def deliveries():
        async with sessions() as db:
            await apply_tenant_context(db, context)
            return {
                row.event_id.rsplit(":", 1)[1]: row
                for row in await db.scalars(select(BillingNotificationDelivery).where(
                    BillingNotificationDelivery.workspace_id == workspace
                ))
            }

    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        assert await db.scalar(text("select session_user")) == "twobrain_rec_maintenance"
        assert await db.scalar(text("select not rolbypassrls from pg_roles where rolname=session_user"))
        personal = await db.get(Workspace, workspace)
        personal.kind, personal.owner_user_id = "personal", owner
        identity = ExternalIdentity(
            user_id=owner, provider="email", provider_subject=f"trial-{owner}",
            email="first@example.test", is_verified=True, is_active=True,
        )
        activation = TrialActivation(
            user_id=owner, workspace_id=workspace, starts_at=start, ends_at=end,
            policy_version="trial-v1",
        )
        db.add_all([
            identity, activation,
            WorkspaceSubscription(
                workspace_id=workspace, state="trial", plan_code="trial", trial_ends_at=end
            ),
        ])
        await enqueue_trial_started(db, activation, now=start)

    async with sessions() as db:
        await apply_tenant_context(db, _request_context(ids, "b"))
        assert not await db.scalar(select(BillingNotificationDelivery.id).where(
            BillingNotificationDelivery.workspace_id == workspace
        ))

    started = (await deliveries())["started"]
    async with sessions() as db:
        await apply_tenant_context(db, context)
        assert await trial_notice_recipient(db, started, now=start) == "first@example.test"
    clock = start + timedelta(days=1)
    await dispatch()
    assert (await deliveries())["started"].state == "suppressed"
    assert not calls

    await poll(end - timedelta(days=3, microseconds=1))
    assert set(await deliveries()) == {"started"}
    clock = end - timedelta(days=3)
    await asyncio.gather(poll(clock), poll(clock))
    assert set(await deliveries()) == {"started", "t72"}

    # Change the verified address after the worker's initial selection.
    recipient = worker.trial_notice_recipient
    async def replace_address(db, delivery, *, now):
        async with sessions.begin() as edit:
            await apply_tenant_context(edit, context)
            (await edit.get(ExternalIdentity, identity.id)).email = "current@example.test"
        return await recipient(db, delivery, now=now)

    with monkeypatch.context() as edit:
        edit.setattr(worker, "trial_notice_recipient", replace_address)
        failure = "unknown"
        await dispatch()
    assert [call["recipient_email"] for call in calls] == ["current@example.test"]
    assert (await deliveries())["t72"].last_error_code == "postal_outcome_unknown"
    await dispatch()
    assert len(calls) == 1

    clock = end - timedelta(days=1)
    await poll(clock)
    assert set(await deliveries()) == {"started", "t72", "t24"}
    failure = "known"
    await dispatch()
    assert len(calls) == 2 and (await deliveries())["t24"].state == "retry"
    clock += timedelta(minutes=1)
    await dispatch()
    assert len(calls) == 3 and (await deliveries())["t24"].attempts == 2

    clock = end
    await poll(clock)
    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        db.add(BillingNotificationPreference(user_id=owner, optional_email_enabled=False))
    failure = None
    await dispatch()
    notices = await deliveries()
    assert len(calls) == 4 and calls[-1]["subject"] == "Пробный период закончился"
    assert calls[-1]["plain_body"].count("https://graf.example.test/billing") == 1
    assert notices["expired"].state == "delivered"
    assert (notices["t24"].state, notices["t24"].attempts) == ("suppressed", 2)
    assert notices["t72"].attempts == 1
    await poll(end + timedelta(days=1))
    await dispatch()
    assert len(await deliveries()) == 4 and len(calls) == 4
    async with sessions() as db:
        await apply_tenant_context(db, context)
        sub = await db.get(WorkspaceSubscription, workspace)
        assert (sub.state, sub.plan_code, sub.trial_ends_at, sub.paid_through) == (
            "trial", "trial", end, None
        )


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_trial_poll_bounds_batch_and_excludes_processed_or_stale_events(rls_engine):
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from sqlalchemy import select

    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing.trial_notifications import (
        enqueue_due_trial_notices,
        trial_notice_recipient,
    )
    from twobrain_rec_server.db.models import (
        BillingNotificationDelivery,
        BillingNotificationPreference,
        ExternalIdentity,
        TrialActivation,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    sessions = create_sessionmaker(rls_engine)
    ids = await _seed_probe_rows(rls_engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="test-trial",
        reason_category="trial-batch",
        feature_area="billing",
    )
    end = datetime(2027, 1, 1, 12, tzinfo=UTC)
    now = end - timedelta(hours=20)
    workspaces = [uuid4() for _ in range(107)]
    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        owners = [uuid4() for _ in workspaces]
        for user in owners:
            db.add(UserIdentity(
                id=user, organization_id=ids["org_a"], external_subject=f"trial-batch-{user}",
            ))
        await db.flush()
        for user, workspace in zip(owners, workspaces, strict=True):
            db.add(Workspace(
                id=workspace, organization_id=ids["org_a"], kind="personal",
                owner_user_id=user, slug=f"trial-batch-{workspace}", name="Trial batch",
            ))
        await db.flush()
        for i, (user, workspace) in enumerate(zip(owners, workspaces, strict=True)):
            trial_end = now - timedelta(days=1) if i == 106 else end
            db.add_all([
                WorkspaceMembership(workspace_id=workspace, user_id=user, role="owner"),
                TrialActivation(
                    user_id=user, workspace_id=workspace, starts_at=trial_end - timedelta(days=7),
                    ends_at=trial_end, policy_version="trial-v1",
                ),
                ExternalIdentity(
                    user_id=user, provider="email", provider_subject=f"trial-{user}",
                    email="trial-batch@example.test", is_verified=i != 104,
                ),
                WorkspaceSubscription(
                    workspace_id=workspace, state="trial", plan_code="trial",
                    billing_owner_id=ids["user_b"] if i == 105 else user,
                    trial_ends_at=trial_end if i != 103 else trial_end + timedelta(hours=1),
                    paid_through=now + timedelta(hours=1) if i == 102 else None,
                ),
            ])
        (await db.get(Workspace, workspaces[101])).owner_user_id = ids["user_b"]

    async def batch():
        async with sessions.begin() as db:
            await apply_tenant_context(db, context)
            await enqueue_due_trial_notices(db, now=now)
            return (
                await db.scalars(select(BillingNotificationDelivery).where(
                    BillingNotificationDelivery.workspace_id.in_(workspaces)
                ))
            ).all()

    first = await batch()
    assert len(first) == 100
    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        (await db.get(BillingNotificationDelivery, first[0].id)).state = "suppressed"
    complete = await batch()
    assert len(complete) == 101
    assert {row.workspace_id for row in complete} == set(workspaces[:101])
    assert {row.event_id.rsplit(":", 1)[1] for row in complete} == {"t24"}

    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        for i, row in enumerate(complete[:6]):
            if i == 0:
                (await db.get(Workspace, row.workspace_id)).owner_user_id = ids["user_a"]
            if i == 1:
                (await db.get(WorkspaceSubscription, row.workspace_id)).paid_through = end
            if i == 2:
                (await db.get(WorkspaceSubscription, row.workspace_id)).trial_ends_at = now
            if i == 3:
                identity = await db.scalar(select(ExternalIdentity).where(
                    ExternalIdentity.user_id == row.recipient_id
                ))
                identity.is_active = False
            if i == 4:
                db.add(BillingNotificationPreference(
                    user_id=row.recipient_id, optional_email_enabled=False
                ))
            if i < 5:
                assert await trial_notice_recipient(db, row, now=now) is None
            else:
                assert await trial_notice_recipient(db, row, now=now) == "trial-batch@example.test"


@pytest.mark.parametrize("mode, expected_calls, expected_state, attempts", [
    ("success", 1, "delivered", 1),
    ("retry_then_success", 2, "delivered", 2),
    ("retry_limit", 5, "failed", 5),
    ("nonretryable", 1, "failed", 1),
    ("ambiguous", 1, "failed", 1),
    ("generic", 1, "failed", 1),
    ("postal_object", 1, "failed", 1),
    ("postal_list", 1, "failed", 1),
    ("postal_unknown", 1, "failed", 1),
    ("crash", 1, "failed", 1),
    ("concurrent", 1, "delivered", 1),
    ("suppressed", 0, "suppressed", 0),
])
def test_billing_sender_claims_before_post_and_never_replays_unknown_outcome(
    client, monkeypatch, caplog, mode, expected_calls, expected_state, attempts
):
    import asyncio
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import select

    from tests.conftest import USER_ID
    from tests.unit.test_billing_money_path_e2e import _prepare_owner_session
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
    from twobrain_rec_server.billing.events import enqueue_billing_notification
    from twobrain_rec_server.db.models import (
        BillingAcceptanceBudget,
        BillingNotificationDelivery,
        BillingNotificationPreference,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.workflows import worker

    workspace, _ = _prepare_owner_session(client)
    event_id = "receipt:synthetic:available"
    paid_through = datetime.now(UTC) + timedelta(days=365)
    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            db.add(WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID,
                state="personal", plan_code="personal", cycle="year", recurring_allowed=False,
                capacity_bytes=10_000_000_000, paid_through=paid_through))
            db.add(BillingAcceptanceBudget(workspace_id=workspace, limit_minor=20000,
                spent_minor=16245, reserved_minor=0, enabled=False,
                expires_at=datetime.now(UTC) - timedelta(hours=1)))
            if mode == "suppressed":
                db.add(BillingNotificationPreference(user_id=USER_ID, optional_email_enabled=False))
            await enqueue_billing_notification(db, workspace_id=workspace, recipient_id=USER_ID,
                event_id=event_id, kind=BillingNotification.TRIAL_ENDING if mode == "suppressed"
                else BillingNotification.RECEIPT_AVAILABLE,
                payload={"invoice": "INV-SYNTHETIC", "action_path": "/billing/history"})
            await db.commit()
            return await db.scalar(select(BillingNotificationDelivery.id).where(
                BillingNotificationDelivery.event_id == event_id))
    notice_id = asyncio.run(seed())
    monkeypatch.setattr(worker, "create_engine", lambda settings: client.app_state["engine"])
    monkeypatch.setattr(worker, "create_sessionmaker", lambda engine: client.app_state["sessionmaker"])
    calls = []
    original_sleep = asyncio.sleep
    cycles = 0

    async def sleep(seconds):
        nonlocal cycles
        if seconds != 60:
            return await original_sleep(seconds)
        cycles += 1
        if cycles >= 6:
            raise asyncio.CancelledError()
        await original_sleep(0)
    monkeypatch.setattr(worker.asyncio, "sleep", sleep)

    async def send(**kwargs):
        calls.append(kwargs["delivery_key"])
        assert kwargs["delivery_key"] == f"billing:{notice_id}"
        async with client.app_state["sessionmaker"]() as db:
            claimed = await db.get(BillingNotificationDelivery, notice_id)
            assert claimed.state == "failed" and claimed.last_error_code == "postal_outcome_unknown"
            assert claimed.attempts == len(calls)
        if mode.startswith("postal_"):
            import httpx

            from twobrain_rec_server.auth.email_delivery import PostalEmailLoginClient
            response = {"postal_object": {}, "postal_list": [],
                        "postal_unknown": {"status": "unknown"}}[mode]
            postal = PostalEmailLoginClient(api_url="http://postal.example.test",
                api_key="synthetic-key", from_address="sender@example.test",
                transport=httpx.MockTransport(lambda request: httpx.Response(200, json=response)))
            await postal.send_billing_notification(**{
                key: value for key, value in kwargs.items() if key != "settings"})
        if mode == "crash":
            raise asyncio.CancelledError()
        if mode in {"ambiguous", "nonretryable", "retry_limit"} or (
            mode == "retry_then_success" and len(calls) == 1
        ):
            raise EmailLoginDeliveryError("synthetic-sensitive-address-secret",
                outcome_unknown=mode == "ambiguous", retryable=mode != "nonretryable")
        if mode == "generic":
            raise RuntimeError("synthetic-sensitive-address-secret")
        if mode == "concurrent":
            await original_sleep(0.05)
    monkeypatch.setattr(worker, "send_billing_notification", send)

    async def run():
        if mode == "concurrent":
            results = await asyncio.gather(
                worker.run_billing_notification_reconciler(client.app.state.settings),
                worker.run_billing_notification_reconciler(client.app.state.settings),
                return_exceptions=True)
            assert all(isinstance(item, asyncio.CancelledError) for item in results)
        else:
            with pytest.raises(asyncio.CancelledError):
                await worker.run_billing_notification_reconciler(client.app.state.settings)
            if mode == "crash":
                with pytest.raises(asyncio.CancelledError):
                    await worker.run_billing_notification_reconciler(client.app.state.settings)
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(BillingNotificationDelivery, notice_id)
            assert (row.state, row.attempts) == (expected_state, attempts)
            assert (row.event_id, row.recipient_id, row.workspace_id) == (event_id, USER_ID, workspace)
            assert (row.delivered_at is not None) == (expected_state == "delivered")
            assert row.last_error_code == (
                "postal_outcome_unknown" if mode in {"ambiguous", "generic", "crash"} or mode.startswith("postal_")
                else "EmailLoginDeliveryError" if mode in {"nonretryable", "retry_limit"} else None)
            sub = await db.get(WorkspaceSubscription, workspace)
            assert not sub.recurring_allowed and sub.capacity_bytes == 10_000_000_000
            assert sub.paid_through == paid_through
            budget = await db.scalar(select(BillingAcceptanceBudget).where(
                BillingAcceptanceBudget.workspace_id == workspace))
            assert (budget.spent_minor, budget.reserved_minor, budget.enabled) == (16245, 0, False)
    asyncio.run(run())
    assert len(calls) == expected_calls
    assert "synthetic-sensitive-address-secret" not in caplog.text
