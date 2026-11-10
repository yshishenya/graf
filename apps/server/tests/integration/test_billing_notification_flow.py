import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration import test_billing_renewal_planner_postgres as planner
from tests.integration.test_billing_renewal_planner_postgres import paid_workspace as paid_workspace
from tests.integration.test_rls_postgres_policies import _create_probe_role
from twobrain_rec_server.billing.events import BillingEvent, notification_kind_for
from twobrain_rec_server.billing.notifications import (
    REFERRAL_NOTICE_KINDS,
    BillingNotification,
    build_notification,
    notification_copy,
)
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingNotificationDelivery,
    BillingNotificationPreference,
    BillingOperation,
    WorkspaceSubscription,
)
from twobrain_rec_server.workflows import worker


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
    assert event.safe_payload.get("action_path") == ("/referrals" if kind in REFERRAL_NOTICE_KINDS else "/billing")


def test_refund_and_unknown_provider_events_are_not_customer_notifications() -> None:
    assert BillingNotification.RECEIPT_AVAILABLE in {
        notification_kind_for(BillingEvent.RECEIPT_AVAILABLE)
    }
    with pytest.raises(ValueError):
        notification_kind_for("refund.succeeded")
    with pytest.raises(ValueError):
        notification_kind_for("provider.unknown")


@pytest.fixture
async def billing_maintenance_probe_url(postgres_isolated_cluster_database_url):
    # Keep the fixed maintenance role and the whole sender queue isolated.
    url = postgres_isolated_cluster_database_url
    role, password = await _create_probe_role(url, role_name="twobrain_rec_maintenance")
    return make_url(url).set(username=role, password=password).render_as_string(hide_password=False)


@pytest.fixture
async def trial_maintenance_engine(billing_maintenance_probe_url):
    engine = create_async_engine(billing_maintenance_probe_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_trial_lifecycle_uses_current_owner_and_exact_windows(trial_maintenance_engine, monkeypatch):
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

    ids = await _seed_probe_rows(trial_maintenance_engine)
    owner, workspace = ids["user_a"], ids["workspace_a"]
    sessions = create_sessionmaker(trial_maintenance_engine)
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
    monkeypatch.setattr(worker, "create_engine", lambda settings: trial_maintenance_engine)
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
async def test_trial_poll_bounds_batch_and_excludes_processed_or_stale_events(trial_maintenance_engine):
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

    sessions = create_sessionmaker(trial_maintenance_engine)
    ids = await _seed_probe_rows(trial_maintenance_engine)
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


@pytest.mark.parametrize("case", [
    "restart", "retry_limit", "lost_address", "merged", "opt_out", "lost_owner", "unknown",
    "cap_zero", "immediate", "opt_out_at_enqueue", "lost_membership", "enqueue_failure",
])
def test_referral_notice_from_reward_transition_to_delivery(client, monkeypatch, case):
    import asyncio
    from datetime import UTC, datetime, timedelta
    from uuid import uuid4

    from pydantic import AnyUrl
    from sqlalchemy import select, update
    from sqlalchemy.exc import OperationalError

    from tests.conftest import ORG_ID, USER_ID
    from tests.unit.test_billing_money_path_e2e import RECEIPT_EMAIL, _prepare_owner_session
    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError
    from twobrain_rec_server.billing import referral_notifications
    from twobrain_rec_server.billing.referral_rewards import (
        create_pending_credit,
        mature_pending_credits,
        reverse_credit_for_payment,
    )
    from twobrain_rec_server.db.models import (
        BillingNotificationDelivery,
        BillingNotificationPreference,
        ExternalIdentity,
        ReferralAttribution,
        ReferralLink,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.workflows import worker

    workspace, _ = _prepare_owner_session(client)
    sessions = client.app_state["sessionmaker"]
    monkeypatch.setattr(client.app.state.settings, "public_base_url", AnyUrl("https://graf.example.invalid"))
    paid_at = datetime(2026, 10, 1, tzinfo=UTC)
    clock = paid_at + timedelta(days=14)
    invitee = uuid4()
    link = uuid4()
    payment = "synthetic-first-payment"

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz is not None else clock.replace(tzinfo=None)

    monkeypatch.setattr(worker, "datetime", Clock)
    monkeypatch.setattr(worker, "create_engine", lambda settings: client.app_state["engine"])
    monkeypatch.setattr(worker, "create_sessionmaker", lambda engine: sessions)
    real_sleep = asyncio.sleep

    async def sleep(seconds):
        if seconds == 60:
            raise asyncio.CancelledError()
        await real_sleep(seconds)

    monkeypatch.setattr(worker.asyncio, "sleep", sleep)
    sends = []
    authorization_calls = 0
    real_authorize = worker.referral_notice_recipient

    async def authorize(*args, **kwargs):
        nonlocal authorization_calls
        authorization_calls += 1
        if case == "retry_limit" or (case == "restart" and authorization_calls == 1):
            if case == "restart":
                await real_sleep(0.05)
            raise OperationalError("synthetic authorization", {}, RuntimeError("unavailable"))
        return await real_authorize(*args, **kwargs)

    async def send(**kwargs):
        assert kwargs["recipient_email"] == RECEIPT_EMAIL
        assert kwargs["plain_body"].endswith("https://graf.example.invalid/referrals")
        assert 'href="https://graf.example.invalid/referrals"' in kwargs["html_body"]
        assert "synthetic-first-payment" not in kwargs["plain_body"]
        assert "_retry_not_before" not in kwargs["plain_body"]
        sends.append(kwargs["subject"])
        if case == "unknown":
            raise EmailLoginDeliveryError("synthetic", outcome_unknown=True, retryable=True)

    monkeypatch.setattr(worker, "referral_notice_recipient", authorize)
    monkeypatch.setattr(worker, "send_billing_notification", send)

    async def run_once():
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(client.app.state.settings)

    async def run():
        nonlocal clock
        async with sessions() as db:
            db.add(UserIdentity(id=invitee, organization_id=ORG_ID, external_subject=str(invitee)))
            db.add(ReferralLink(id=link, workspace_id=workspace, inviter_user_id=USER_ID,
                token_hash=link.hex * 2))
            await db.flush()
            db.add(ReferralAttribution(workspace_id=workspace, inviter_user_id=USER_ID,
                invitee_user_id=invitee, referral_link_id=link, token_hash=link.hex * 2, state="bound"))
            await db.flush()
            assert await create_pending_credit(db, workspace_id=workspace, invitee_user_id=invitee,
                provider_payment_id=payment, paid_at=paid_at, cycle="month") == "created"
            await db.commit()
            assert await mature_pending_credits(db, now=clock) == 0
            await db.rollback()

        async def read():
            async with sessions() as db:
                return (await db.scalars(select(BillingNotificationDelivery)
                    .where(BillingNotificationDelivery.workspace_id == workspace)
                    .order_by(BillingNotificationDelivery.event_id))).all()

        assert not await read()
        if case == "enqueue_failure":
            async def unavailable(*args, **kwargs):
                raise OperationalError("synthetic authorization", {}, RuntimeError("unavailable"))

            with monkeypatch.context() as patch:
                patch.setattr(referral_notifications, "referral_notice_recipient", unavailable)
                with pytest.raises(OperationalError):
                    async with sessions() as db:
                        await mature_pending_credits(db, now=clock)
            assert not await read()
            async with sessions() as db:
                assert await mature_pending_credits(db, now=clock) == 0
                await db.commit()
            retried, = await read()
            assert (retried.template_key, retried.state) == ("referral_available", "pending")
            return
        if case in {"cap_zero", "immediate", "opt_out_at_enqueue"}:
            async with sessions() as db:
                if case == "immediate":
                    db.add(WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID,
                        state="personal", plan_code="personal", cycle="month", recurring_allowed=False,
                        capacity_bytes=10_000_000_000, paid_through=clock + timedelta(days=30)))
                elif case == "opt_out_at_enqueue":
                    db.add(BillingNotificationPreference(user_id=USER_ID, optional_email_enabled=False))
                await db.flush()
                assert await mature_pending_credits(
                    db, now=clock, rolling_days=180 if case == "cap_zero" else 0,
                ) == (7 if case == "immediate" else 0)
                await db.commit()
            if case == "immediate":
                applied, = await read()
                assert applied.template_key == "referral_applied"
                assert applied.safe_payload["referral_days"] == "7"
            else:
                assert not await read()
            return
        async with sessions() as db:
            assert await mature_pending_credits(db, now=clock) == 0
            await db.commit()
            assert await mature_pending_credits(db, now=clock) == 0
            if case == "lost_address":
                await db.execute(update(ExternalIdentity).where(ExternalIdentity.user_id == USER_ID)
                    .values(is_verified=False))
            elif case == "merged":
                await db.execute(update(UserIdentity).where(UserIdentity.id == USER_ID)
                    .values(merged_into_user_id=invitee))
            elif case == "opt_out":
                db.add(BillingNotificationPreference(user_id=USER_ID, optional_email_enabled=False))
            elif case == "lost_owner":
                await db.execute(update(Workspace).where(Workspace.id == workspace).values(owner_user_id=invitee))
            elif case == "lost_membership":
                await db.execute(update(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace, WorkspaceMembership.user_id == USER_ID,
                ).values(status="inactive"))
            await db.commit()

        available, = await read()
        assert available.template_key == "referral_available"
        assert available.recipient_id == USER_ID
        assert available.safe_payload == {"referral_expiry": "15.10.2027 03:00", "action_path": "/referrals"}
        if case == "restart":
            await asyncio.gather(run_once(), run_once())
        else:
            await run_once()
        if case in {"lost_address", "merged", "opt_out", "lost_owner", "lost_membership"}:
            suppressed, = await read()
            assert (suppressed.state, suppressed.attempts) == ("suppressed", 0)
            assert not sends
            return
        if case == "unknown":
            await run_once()
            failed, = await read()
            assert (failed.state, failed.attempts, failed.last_error_code) == ("failed", 1, "postal_outcome_unknown")
            assert len(sends) == 1
            return

        retried, = await read()
        assert (retried.state, retried.attempts) == ("retry", 1)
        assert retried.safe_payload["_retry_not_before"] == clock.timestamp() + 60
        clock += timedelta(seconds=59)
        await run_once()
        assert authorization_calls == 1 and not sends
        clock += timedelta(seconds=1)
        await run_once()
        if case == "retry_limit":
            for _ in range(4):
                clock += timedelta(seconds=60)
                await run_once()
            failed, = await read()
            assert (failed.state, failed.attempts, failed.last_error_code) == (
                "failed", 5, "referral_authorization_unavailable",
            )
            assert authorization_calls == 5 and not sends
            return

        delivered, = await read()
        assert (delivered.state, delivered.attempts) == ("delivered", 2)
        async with sessions() as db:
            db.add(WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID,
                state="personal", plan_code="personal", cycle="month", recurring_allowed=False,
                capacity_bytes=10_000_000_000, paid_through=clock + timedelta(days=30)))
            await db.flush()
            assert await mature_pending_credits(db, now=clock, rolling_days=177) == 3
            await db.commit()
            assert await reverse_credit_for_payment(db, workspace_id=workspace, provider_payment_id=payment,
                invitee_user_id=invitee, now=clock) == "reversed"
            await db.commit()
            assert await reverse_credit_for_payment(db, workspace_id=workspace, provider_payment_id=payment,
                invitee_user_id=invitee, now=clock) == "none"

        applied, _, reversed_notice = await read()
        assert applied.safe_payload["referral_days"] == "3"
        assert applied.safe_payload["referral_start"] != applied.safe_payload["referral_end"]
        assert set(reversed_notice.safe_payload) == {"referral_reversed", "action_path"}
        assert {row.recipient_id for row in await read()} == {USER_ID}
        await run_once()
        assert len(sends) == 3
        assert {row.state for row in await read()} == {"delivered"}

    asyncio.run(run())


@pytest.mark.asyncio
@pytest.mark.strict_rls
async def test_committed_billing_events_reach_one_delivery_each(paid_workspace, monkeypatch):
    case = paid_workspace
    cutoff = case.original["subscription"]["paid_through"]
    charge = planner.renewal_charge

    async def notices(db):
        return {
            row.id: row for row in await db.scalars(
                select(BillingNotificationDelivery)
                .where(BillingNotificationDelivery.workspace_id == case.workspace)
            )
        }

    operation_id, invoice_id = await planner._stage_unresolved_renewal(case)
    async with planner._session(case.factory) as db:
        db.add(BillingNotificationPreference(user_id=case.owner, optional_email_enabled=False))
        subscription = await db.get(WorkspaceSubscription, case.workspace)
        subscription.recurring_allowed = False
        subscription.recurring_authority_version += 1
        operation = await db.get(BillingOperation, operation_id)
        operation.provider_id = None
        await charge.project_renewal_cutoffs(db, now=cutoff - timedelta(microseconds=1))
        assert {row.template_key for row in (await notices(db)).values()} == {
            "payment_succeeded", "receipt_available", "renewal_upcoming",
        }
        await db.commit()

    async with planner._session(case.factory) as db:
        await charge.project_renewal_cutoffs(db, now=cutoff)
        await db.commit()

    unknown_id = f"renewal:{invoice_id}:unknown"
    async with planner._session(case.factory) as db:
        expected = {
            f"payment:{case.invoice_id}:succeeded": ("Платеж подтвержден", "Предоставленные периоды:"),
            f"receipt:{case.invoice_id}:available": ("Чек доступен", "историю платежей"),
            await planner._assert_upcoming_notice(db, case): (
                "Напоминание о продлении", "по расписанию на момент события",
            ),
            unknown_id: ("Статус продления на конец периода", "результат платежа ещё не был известен"),
        }
        before = list((await notices(db)).values())
        assert len(before) == 4 and {row.event_id for row in before} == expected.keys()
        assert next(row.template_key for row in before if row.event_id == unknown_id) == "renewal_unknown"

        await charge.lock_storage_workspace(db, case.workspace)
        subscription = await db.scalar(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == case.workspace)
            .with_for_update()
        )
        assert subscription.plan_code == "free" and subscription.renewal_resolution == "unknown_pending"
        operation = await db.get(BillingOperation, operation_id)
        invoice = await db.get(BillingInvoice, invoice_id)
        # A late confirmation identifies the original operation, without another charge.
        operation.provider_id = f"synthetic-confirmed-{operation_id}"
        await charge.record_renewal_decline(
            db, subscription=subscription, operation=operation, invoice=invoice,
            now=cutoff + timedelta(seconds=1),
        )
        await db.commit()

    async with planner._session(case.factory) as db:
        await planner._assert_final_failure_notice(db, case, invoice_id)
        failed_id = f"renewal:{invoice_id}:failed"
        before = await notices(db)
        failed = next(row for row in before.values() if row.event_id == failed_id)
        expected[failed_id] = (
            "Продление не состоялось",
            f"Оплаченный период завершился {failed.safe_payload['access_until']} МСК",
        )
        assert len(before) == 5 and {row.event_id for row in before.values()} == expected.keys()
        assert all(
            (row.recipient_id, row.channel, row.state, row.attempts) == (case.owner, "email", "pending", 0)
            for row in before.values()
        )

    by_key = {f"billing:{row_id}": row for row_id, row in before.items()}
    calls = []

    async def stop_after_poll(seconds):
        assert seconds == 60
        raise asyncio.CancelledError

    async def synthetic_transport(*, delivery_key, recipient_email, subject, plain_body, **_):
        old = by_key[delivery_key]
        async with planner._session(case.factory) as db:
            claim = await db.get(BillingNotificationDelivery, old.id)
            calls.append((
                old.event_id, recipient_email, subject, plain_body,
                (claim.state, claim.attempts, claim.last_error_code),
            ))

    monkeypatch.setattr(worker, "send_billing_notification", synthetic_transport)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(
        CancelledError=asyncio.CancelledError, sleep=stop_after_poll,
    ))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(case.settings)
        assert len(calls) == 5 and {call[0] for call in calls} == expected.keys()
    for event_id, recipient, subject, body, claim in calls:
        assert recipient == "planner@example.invalid"
        expected_subject, phrase = expected[event_id]
        assert subject == expected_subject and phrase in body
        assert claim == ("failed", 1, "postal_outcome_unknown")

    async with planner._session(case.factory) as db:
        after = await notices(db)
        assert after.keys() == before.keys()
        for row_id, row in after.items():
            old = before[row_id]
            assert (row.event_id, row.recipient_id, row.channel, row.safe_payload) == (
                old.event_id, old.recipient_id, old.channel, old.safe_payload,
            )
            assert (row.state, row.attempts, row.last_error_code) == ("delivered", 1, None)
            assert row.delivered_at is not None
