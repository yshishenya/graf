import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from tests.integration import test_billing_renewal_planner_postgres as planner
from tests.integration.test_billing_renewal_planner_postgres import paid_workspace as paid_workspace
from tests.integration.test_provider_refund_observation import (
    refund_queue_case as refund_queue_case,
)
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
    if kind in {BillingNotification.STORAGE_THRESHOLD, BillingNotification.ACCOUNT_CLOSE}:
        assert event.safe_payload == {}  # Incomplete historical snapshots are suppressed by the sender.
    elif kind == BillingNotification.FAIR_USE_REVIEW:
        assert event.safe_payload.get("action_path") == "/account/fair-use"
    else:
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
async def rls_engine(billing_maintenance_probe_url):
    engine = create_async_engine(billing_maintenance_probe_url, pool_pre_ping=True)
    try:
        yield engine
    finally:
        await engine.dispose()


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


@pytest.mark.parametrize("scenario", [
    "late", "early", "exact", "missing_cutoff", "different_cutoff", "changed_period",
    "wrong_payer", "pending", "rollback",
])
@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_renewal_confirmation_reports_only_a_proven_late_grant(
    paid_workspace, tmp_path, monkeypatch, scenario,
):
    from datetime import datetime
    from uuid import uuid4
    from zoneinfo import ZoneInfo

    import httpx

    from twobrain_rec_server.billing import entitlements, webhook_reconciliation
    from twobrain_rec_server.billing.yookassa import YooKassaClient
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db.models import BillingEntitlementGrant

    case = paid_workspace
    cutoff = case.original["subscription"]["paid_through"]
    captured = cutoff - timedelta(hours=2)
    applied = {"early": cutoff - timedelta(hours=1), "exact": cutoff}.get(
        scenario, cutoff + timedelta(hours=3),
    )
    secret = tmp_path / "synthetic-provider-secret"
    secret.write_text("synthetic-offline-not-a-real-key")
    secret.chmod(0o600)
    settings = Settings(_env_file=None, **{**case.settings.model_dump(),
        "public_base_url": "https://example.invalid",
        "billing_checkout_enabled": True,
        "billing_provider_observation_enabled": True,
        "billing_checkout_workspace_ids": frozenset({case.workspace}),
        "billing_yookassa_base_url": "https://api.yookassa.test",
        "billing_yookassa_environment": "test",
        "billing_yookassa_shop_id": "1",
        "billing_yookassa_secret_file": secret,
        "billing_yookassa_webhook_secret_file": secret,
        "billing_referral_secret_file": secret,
        "billing_support_email": "support@example.invalid",
        "billing_receipt_tax_system_code": 2,
        "billing_receipt_vat_code": 1,
    })
    charge = planner.renewal_charge
    async with planner._session(case.factory) as db:
        (operation_id,) = await charge.plan_due_renewals(
            db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace}),
        )
        await db.commit()

    reference = str(uuid4())
    calls = []

    def offline_provider(request):
        calls.append(request.method)
        if request.method == "POST":
            assert request.url.path == "/v3/payments"
            return httpx.Response(200, json={"id": reference, "status": "pending"})
        assert request.method == "GET" and request.url.path == f"/v3/payments/{reference}"
        return httpx.Response(200, json=reply)

    transport = httpx.MockTransport(offline_provider)

    async def mock_only_send(client, request, **kwargs):
        assert request.url.host == "api.yookassa.test"
        assert client._transport_for_url(request.url) is transport
        return await planner._ASYNC_HTTP_SEND(client, request, **kwargs)

    monkeypatch.setattr(httpx.AsyncClient, "send", mock_only_send)
    for module in (charge, worker):
        monkeypatch.setattr(
            module, "YooKassaClient", lambda config: YooKassaClient(config, transport=transport),
        )
    async with planner._session(case.factory) as db:
        dispatched = await charge.charge_renewal_operation(
            db, settings, operation_id=operation_id, workspace_id=case.workspace, now=case.t0,
        )
        assert dispatched.status == "sent" and dispatched.provider_id == reference

    async def notices(db):
        return {row.event_id: row for row in await db.scalars(
            select(BillingNotificationDelivery)
            .where(BillingNotificationDelivery.workspace_id == case.workspace)
        )}

    async with planner._session(case.factory) as db:
        subscription = await db.get(WorkspaceSubscription, case.workspace)
        # Model an already recorded refusal; the cancellation UI has its own acceptance.
        subscription.recurring_allowed = False
        subscription.recurring_authority_version += 1
        authority = subscription.recurring_authority_version
        db.add(BillingNotificationPreference(user_id=case.owner, optional_email_enabled=False))
        operation = await db.get(BillingOperation, operation_id)
        invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.operation_id == operation_id))
        assert operation.request_snapshot["purchase_schema"] == invoice.plan_snapshot["purchase_schema"] == 2
        if applied > cutoff:
            assert await charge.project_renewal_cutoffs(db, now=cutoff) == 1
        if scenario == "missing_cutoff":
            invoice.plan_snapshot = {k: v for k, v in invoice.plan_snapshot.items() if k != "paid_through_at"}
        elif scenario == "different_cutoff":
            invoice.plan_snapshot = {**invoice.plan_snapshot, "paid_through_at": captured.isoformat()}
        elif scenario == "changed_period":
            subscription.paid_through = cutoff + timedelta(hours=1)
        elif scenario == "wrong_payer":
            operation.request_snapshot = {**operation.request_snapshot, "billing_actor_user_id": str(uuid4())}
        invoice_id = invoice.id
        amount = invoice.amount_minor
        reply = {
            "id": reference, "status": "succeeded", "paid": True, "test": True,
            "created_at": case.t0.isoformat(), "captured_at": captured.isoformat(),
            "recipient": {"account_id": "1"},
            "amount": {"value": f"{amount // 100}.{amount % 100:02d}", "currency": "RUB"},
            "metadata": {
                "workspace_id": str(case.workspace), "operation_id": str(operation_id),
                "invoice_number": invoice.safe_number,
            },
        }
        if scenario == "pending":
            reply.update(status="pending", paid=False, captured_at=None)
        action_path = f"/billing/invoices/{invoice.safe_number}"
        await db.commit()

    unknown_id = f"renewal:{invoice_id}:unknown"
    event_id = f"payment:{invoice_id}:succeeded"
    async with planner._session(case.factory) as db:
        subscription = await db.get(WorkspaceSubscription, case.workspace)
        before = await notices(db)
        assert event_id not in before
        if applied > cutoff:
            assert subscription.plan_code == "free" and subscription.renewal_resolution == "unknown_pending"
            assert before[unknown_id].template_key == "renewal_unknown"
        else:
            assert unknown_id not in before

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return applied.astimezone(tz)

    for module in (worker, webhook_reconciliation, entitlements):
        monkeypatch.setattr(module, "datetime", Clock)
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    request = {"operation_id": str(operation_id), "workspace_id": str(case.workspace)}

    if scenario == "rollback":
        async def fail_after_enqueue(db, **_):
            await db.flush()
            assert event_id in await notices(db)
            raise RuntimeError("synthetic rollback after enqueue")

        monkeypatch.setattr(entitlements, "settle_acceptance_budget", fail_after_enqueue)
        with pytest.raises(RuntimeError, match="synthetic rollback after enqueue"):
            await worker.run_billing_renewal_activity(request)
    elif scenario == "pending":
        assert (await worker.run_billing_renewal_activity(request))["status"] == "manual_resolution"
    else:
        status = "reconciliation_gap" if scenario == "wrong_payer" else "succeeded"
        assert (await worker.run_billing_renewal_activity(request))["status"] == status
        if status == "succeeded":
            assert (await worker.run_billing_renewal_activity(request))["status"] == status
    assert calls == ["POST", "GET"]

    phrase = "В GRAF новый оплаченный период начался после окончания предыдущего периода"
    async with planner._session(case.factory) as db:
        subscription = await db.get(WorkspaceSubscription, case.workspace)
        assert subscription.recurring_allowed is False and subscription.recurring_authority_version == authority
        grants = list(await db.scalars(
            select(BillingEntitlementGrant).where(BillingEntitlementGrant.invoice_id == invoice_id)
        ))
        after = await notices(db)
        if scenario in {"wrong_payer", "pending", "rollback"}:
            assert not grants and event_id not in after
            assert subscription.plan_code == "free" and subscription.paid_through == cutoff
            extra = {f"payment:{invoice_id}:service_gap"} if scenario == "wrong_payer" else set()
            assert after.keys() == before.keys() | extra
            return
        grant, = grants
        assert grant.starts_at == max(cutoff, applied)
        assert grant.ends_at == subscription.paid_through and subscription.plan_code == "personal"
        assert timedelta(days=28) <= grant.ends_at - grant.starts_at <= timedelta(days=31)
        invoice = await db.get(BillingInvoice, invoice_id)
        assert datetime.fromisoformat(invoice.plan_snapshot["provider_paid_at"]) == captured < cutoff
        assert after.keys() == before.keys() | {event_id}
        row = after[event_id]
        assert (row.template_key, row.recipient_id, row.state, row.attempts) == (
            "payment_succeeded", case.owner, "pending", 0,
        )
        assert row.safe_payload["action_path"] == action_path
        assert row.safe_payload["amount_minor"] == str(amount)
        assert row.safe_payload.get("renewal_timing") == ("after_cutoff" if scenario == "late" else None)
        msk = ZoneInfo("Europe/Moscow")
        dates = f"{grant.starts_at.astimezone(msk):%d.%m.%Y %H:%M} — {grant.ends_at.astimezone(msk):%d.%m.%Y %H:%M}"
        row_id = row.id

    sends = []

    async def offline_send(*, delivery_key, recipient_email, subject, plain_body, **_):
        if delivery_key == f"billing:{row_id}":
            async with planner._session(case.factory) as db:
                claim = await db.get(BillingNotificationDelivery, row_id)
                assert (claim.state, claim.attempts, claim.last_error_code) == ("failed", 1, "postal_outcome_unknown")
            sends.append((recipient_email, subject, plain_body))

    async def stop_after_poll(seconds):
        assert seconds == 60
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "send_billing_notification", offline_send)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(
        CancelledError=asyncio.CancelledError, sleep=stop_after_poll,
    ))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(case.settings)
        assert len(sends) == 1
    recipient, subject, body = sends[0]
    assert (recipient, subject) == ("planner@example.invalid", "Платеж подтвержден")
    rubles, kopecks = divmod(amount, 100)
    assert f"{rubles:,}".replace(",", " ") + f",{kopecks:02d} ₽" in body
    assert f"{dates} МСК" in body
    assert (phrase in body) == (scenario == "late")
    async with planner._session(case.factory) as db:
        delivered = await db.get(BillingNotificationDelivery, row_id)
        assert (delivered.state, delivered.attempts) == ("delivered", 1)


def test_payment_confirmation_ignores_unknown_stored_renewal_timing():
    from twobrain_rec_server.billing.notifications import NotificationEvent

    kind = BillingNotification.PAYMENT_SUCCEEDED
    regular = build_notification(event_id="payment:test", kind=kind, payload={})
    raw = {"renewal_timing": "after_cutoff_extra"}
    sanitized = build_notification(event_id=regular.event_id, kind=kind, payload=raw)
    assert sanitized.safe_payload == regular.safe_payload
    assert notification_copy(NotificationEvent(regular.event_id, kind, raw)) == notification_copy(regular)


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("reply", ["unavailable", "canceled", "succeeded", "pending", "incomplete"])
async def test_receipt_poll_checks_provider_before_overdue_and_keeps_payment(refund_queue_case, reply, monkeypatch):
    from datetime import UTC, datetime

    from pydantic import AnyUrl
    from sqlalchemy import update

    from twobrain_rec_server.billing.receipt_poll import reconcile_pending_receipts
    from twobrain_rec_server.db.models import ExternalIdentity
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    recipient_email = "receipt-contact@example.invalid"
    public_base_url = AnyUrl("https://graf.example.invalid")
    settings = case.settings.model_copy(update={"public_base_url": public_base_url})
    if reply != "unavailable":
        case.provider_state["payment_receipt_status"] = "canceled" if reply == "incomplete" else reply
        case.provider_state["incomplete_payment_receipt"] = reply == "incomplete"
    first = datetime.now(UTC) - timedelta(hours=72, seconds=1)
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        await db.execute(update(BillingOperation).where(
            BillingOperation.workspace_id == case.workspace_id
        ).values(created_at=first))
        if reply == "succeeded":
            assert case.another_user_id != case.owner_id
            db.add(ExternalIdentity(
                user_id=case.another_user_id, provider="email", provider_subject="receipt-contact",
                email=recipient_email, is_active=True, is_verified=True,
            ))
            db.add(BillingNotificationPreference(user_id=case.another_user_id, optional_email_enabled=False))
            await db.execute(update(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == case.workspace_id
            ).values(billing_owner_id=case.another_user_id))
        invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.id == case.invoice_id))
        action_path = f"/billing/invoices/{invoice.safe_number}"
        invoice.plan_snapshot = {
            "receipt_registration": "pending",
            "receipt_registration_timing": {"first_confirmed_pending_at": first.isoformat()},
        }
        await db.commit()
        counters = await reconcile_pending_receipts(db, case.settings)
        assert counters["receipt_gets"] == 1

    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        assert (await reconcile_pending_receipts(db, case.settings))["receipt_gets"] == 0

    assert len(case.calls) == 1 and case.calls[0][0] == "GET"
    snapshot = (await case.rows(BillingInvoice))[0]["plan_snapshot"]
    timing = snapshot["receipt_registration_timing"]
    assert timing["last_poll_result"] == {"unavailable": "unavailable", "incomplete": "conflict"}.get(reply, "confirmed")
    assert snapshot["receipt_registration"] == ("pending" if reply in {"unavailable", "incomplete"} else reply)
    if reply in {"unavailable", "pending"}:
        overdue = timing["pending_overdue"]
        assert overdue["due_at"] == (first + timedelta(hours=72)).isoformat()
        assert overdue["freshness"] == ("unknown" if reply == "unavailable" else "confirmed")
    else:
        assert "pending_overdue" not in timing
        assert ("canceled" in timing) == (reply == "canceled")
    deliveries = await case.rows(BillingNotificationDelivery)
    assert [row["recipient_id"] for row in deliveries] == ([case.another_user_id] if reply == "succeeded" else [])
    assert (await case.rows(BillingOperation))[0]["state"] == "succeeded"

    if deliveries:
        notice = deliveries[0]
        assert (notice["template_key"], notice["state"], notice["attempts"]) == ("receipt_available", "pending", 0)
        assert notice["safe_payload"]["action_path"] == action_path

    calls = []

    async def transport(*, recipient_email, subject, plain_body, delivery_key, **_):
        assert len(deliveries) == 1
        assert delivery_key == f"billing:{deliveries[0]['id']}"
        [claim] = await case.rows(BillingNotificationDelivery)
        assert (claim["state"], claim["attempts"], claim["last_error_code"]) == (
            "failed", 1, "postal_outcome_unknown",
        )
        calls.append((recipient_email, subject, plain_body))

    async def stop_cycle(seconds):
        assert seconds == 60
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "create_engine", lambda _: case.sessions.kw["bind"])
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _: case.sessions)
    monkeypatch.setattr(worker, "send_billing_notification", transport)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(
        CancelledError=asyncio.CancelledError, sleep=stop_cycle,
    ))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(settings)
        assert len(calls) == (1 if reply == "succeeded" else 0)

    result = await case.rows(BillingNotificationDelivery)
    if reply == "succeeded":
        [(email, subject, plain)] = calls
        assert email == recipient_email and subject == "Чек доступен"
        assert plain == (
            "Откройте историю платежей, чтобы посмотреть чек.\n\n"
            f"Открыть кабинет: {str(public_base_url).rstrip('/')}{action_path}"
        )
        [notice] = result
        assert notice["id"] == deliveries[0]["id"]
        assert (notice["state"], notice["attempts"], notice["last_error_code"]) == ("delivered", 1, None)
        assert notice["delivered_at"] is not None
    else:
        assert result == []


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("used,level", [(200_000_000, "80"), (237_500_000, "95"), (250_000_000, "100")])
async def test_trial_capacity_expiry_causes_one_storage_notice(rls_engine, monkeypatch, used, level):
    import sys
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    import httpx
    from sqlalchemy import text

    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing.purchases import effective_paid_storage
    from twobrain_rec_server.billing.storage import (
        CANONICAL_PLAYBACK_PROFILE,
        project_active_playback_storage,
    )
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db.models import (
        ExternalIdentity,
        MediaRevision,
        TrackArtifact,
        Workspace,
    )
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    ids = await _seed_probe_rows(rls_engine)
    workspace, owner = ids["workspace_a"], ids["user_a"]
    sessions = create_sessionmaker(rls_engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation", actor_id="test-storage",
        reason_category="storage-causal-expiry", feature_area="billing",
    )
    clock = datetime.now(UTC)
    cutoff = clock + timedelta(hours=1)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return clock.astimezone(tz) if tz else clock.replace(tzinfo=None)

    monkeypatch.setattr(worker, "datetime", Clock)
    for name, module in tuple(sys.modules.items()):
        if name.startswith("twobrain_rec_server.billing.") and getattr(module, "datetime", None) is datetime:
            monkeypatch.setattr(module, "datetime", Clock)
    settings = Settings(_env_file=None, env="test", billing_checkout_enabled=False,
                        billing_provider_observation_enabled=False)

    def forbid_http(*_args, **_kwargs):
        raise AssertionError("storage regression must not contact a real provider")

    monkeypatch.setattr(httpx.AsyncClient, "send", forbid_http)
    monkeypatch.setattr(httpx.Client, "send", forbid_http)
    monkeypatch.setattr(worker, "get_settings", lambda: settings)
    monkeypatch.setattr(worker, "create_engine", lambda _: rls_engine)
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _: sessions)
    # Seed history once; then advance only the synthetic clock across expiry.
    async with sessions.begin() as db:
        await apply_tenant_context(db, context)
        assert (await db.execute(text(
            "select session_user, current_user, rolsuper, rolbypassrls "
            "from pg_roles where rolname=current_user"
        ))).one() == ("twobrain_rec_maintenance", "twobrain_rec_maintenance", False, False)
        personal = await db.get(Workspace, workspace)
        personal.kind, personal.owner_user_id = "personal", owner
        subscription = WorkspaceSubscription(
            workspace_id=workspace, billing_owner_id=owner, plan_code="trial", state="trial",
            trial_ends_at=cutoff, capacity_bytes=500_000_000,
        )
        revision = MediaRevision(
            id=uuid4(), workspace_id=workspace, meeting_id=ids["meeting_a"],
            local_media_revision_id="synthetic-storage-history", status="accepted",
        )
        db.add_all([subscription, revision, ExternalIdentity(
            user_id=owner, provider="email", provider_subject=f"storage-{owner}",
            email="storage@example.test", is_active=True, is_verified=True,
        )])
        await db.flush()
        db.add(TrackArtifact(
            workspace_id=workspace, meeting_id=ids["meeting_a"], media_revision_id=revision.id,
            track_role="playback", codec="aac", sample_rate_hz=48000, channel_count=1,
            duration_seconds=60, byte_length=used, sha256="a" * 64,
            storage_object_key="synthetic/history/meeting-review.m4a", status="stored",
            normalization_profile_version=CANONICAL_PLAYBACK_PROFILE, validated_at=cutoff,
            derivation_kind="uploaded_candidate", source_fingerprint_sha256="b" * 64,
            validation_version="playback_validator_v1",
        ))
        await db.flush()
        for at, capacity, band in [(cutoff - timedelta(microseconds=1), 500_000_000, "normal"),
                                   (cutoff, 250_000_000, level)]:
            actual = await effective_paid_storage(db, subscription=subscription, now=at)
            projection = await project_active_playback_storage(db, workspace_id=workspace, capacity_bytes=actual)
            assert (projection.capacity_bytes, projection.threshold) == (
                capacity, {"80": "80%", "95": "95%", "100": "full"}.get(band, band),
            )

    async def notices():
        async with sessions() as db:
            await apply_tenant_context(db, context)
            return list(await db.scalars(select(BillingNotificationDelivery).where(
                BillingNotificationDelivery.workspace_id == workspace,
                BillingNotificationDelivery.template_key == "storage_threshold",
            )))

    assert await notices() == []
    await worker._run_billing_reconciliation_activity({"run_id": str(uuid4())})
    assert await notices() == []
    clock = cutoff
    await worker._run_billing_reconciliation_activity({"run_id": str(uuid4())})
    queued = await notices()
    assert len(queued) == 1, "capacity expiry must reach the durable storage outbox"
    notice = queued[0]
    assert (notice.recipient_id, notice.state, notice.attempts) == (owner, "pending", 0)
    assert {k: notice.safe_payload[k] for k in (
        "storage_level", "storage_used_bytes", "storage_capacity_bytes", "action_path",
    )} == {"storage_level": level, "storage_used_bytes": str(used),
          "storage_capacity_bytes": "250000000", "action_path": "/billing/usage"}
    calls = []

    async def transport(**kwargs):
        async with sessions() as db:
            await apply_tenant_context(db, context)
            claimed = await db.get(BillingNotificationDelivery, UUID(kwargs["delivery_key"].partition(":")[2]))
            assert (claimed.state, claimed.attempts, claimed.last_error_code) == ("failed", 1, "postal_outcome_unknown")
        assert kwargs["recipient_email"] == "storage@example.test"
        assert f"{used} из 250000000 байт" in kwargs["plain_body"]
        calls.append(kwargs["delivery_key"])

    async def stop(_seconds):
        raise asyncio.CancelledError

    monkeypatch.setattr(worker, "send_billing_notification", transport)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    for _ in range(2):
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(settings)
        await worker._run_billing_reconciliation_activity({"run_id": str(uuid4())})
    assert calls == [f"billing:{notice.id}"]
    final = await notices()
    assert len(final) == 1 and (final[0].state, final[0].attempts) == ("delivered", 1)


@pytest.fixture
def storage_publication_client(postgres_isolated_cluster_database_url, monkeypatch):
    from uuid import uuid4

    from scripts import bootstrap_runtime_database_roles as bootstrap
    from tests.conftest import _seed_database, _SessionScopedApplication
    from tests.fakes.auth_contexts import AUTH_BOOTSTRAP_WORKSPACE_ID
    from twobrain_rec_server.config import Settings

    url = postgres_isolated_cluster_database_url
    asyncio.run(_seed_database(url))
    parsed = make_url(url)
    passwords = {"TWOBRAIN_DB_OWNER_PASSWORD_FILE": parsed.password,
                 "TWOBRAIN_DB_APP_PASSWORD_FILE": uuid4().hex,
                 "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE": uuid4().hex,
                 "TWOBRAIN_DB_MEDIA_PASSWORD_FILE": uuid4().hex}
    monkeypatch.setattr(bootstrap, "_read_secret", passwords.__getitem__)
    for key, value in {"HOST": parsed.host, "PORT": str(parsed.port), "NAME": parsed.database}.items():
        monkeypatch.setenv(f"TWOBRAIN_DB_{key}", value)
    asyncio.run(bootstrap._bootstrap())
    media_url = parsed.set(username="twobrain_rec_media", password=passwords["TWOBRAIN_DB_MEDIA_PASSWORD_FILE"]).render_as_string(hide_password=False)
    app_url = parsed.set(username="twobrain_rec_app", password=passwords["TWOBRAIN_DB_APP_PASSWORD_FILE"]).render_as_string(hide_password=False)
    maintenance_url = parsed.set(username="twobrain_rec_maintenance", password=passwords["TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE"]).render_as_string(hide_password=False)
    settings = Settings(_env_file=None, env="test", database_url=url,
                        minio_endpoint="localhost:9000", minio_access_key="test", minio_secret_key="test",
                        minio_bucket="test-bucket", web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
                        billing_checkout_enabled=False, billing_provider_observation_enabled=False)
    application = _SessionScopedApplication(settings, media_url)
    try:
        yield application.client(), maintenance_url, app_url
    finally:
        application.close()


@pytest.mark.strict_rls
@pytest.mark.parametrize("level,target,archive_audio", [
    ("80", 200_000_000, True), ("95", 237_500_000, True), ("100", 250_000_000, True),
    ("80", 200_000_000, False),
])
def test_working_publication_and_replacement_cause_storage_notice(
    storage_publication_client, tmp_path, monkeypatch, level, target, archive_audio,
):
    from datetime import UTC, datetime
    from uuid import UUID, uuid4

    from tests.contract.test_ingest_openapi_contract import auth_headers
    from tests.fakes.auth_contexts import PERSONAL_WORKSPACE_ID, USER_ID, WORKSPACE_ID
    from tests.fixtures.artifacts import track_descriptor
    from tests.fixtures.processing import apply_job_worker_scope, deterministic_canonical_wav_bytes
    from tests.integration.test_playback_normalization_finalize import _accept_first_party_recording
    from tests.integration.test_playback_normalization_workflow import FakeNormalizationPipeline
    from twobrain_rec_server.billing.storage import (
        CANONICAL_PLAYBACK_PROFILE,
        project_active_playback_storage,
    )
    from twobrain_rec_server.db.models import (
        ExternalIdentity,
        PlaybackNormalizationJob,
        TrackArtifact,
        Workspace,
    )
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context
    from twobrain_rec_server.normalization.service import run_normalization_job

    client, maintenance_url, app_url = storage_publication_client
    if not archive_audio:
        from tests.fakes.fake_temporal import FakeTemporalClient
        client.app.state.settings.processing_enabled = True
        client.app.state.temporal_client = FakeTemporalClient()
    from sqlalchemy.pool import NullPool
    engine = create_async_engine(maintenance_url, poolclass=NullPool)
    sessions = create_sessionmaker(engine)
    context = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-storage-publication",
                                       reason_category="causal-publication", feature_area="billing")
    original_body = b"canonical-candidate-copy"
    meeting, _ = _accept_first_party_recording(client, local_recording_id="storage-new-causal", include_playback=True)
    # A distinct accepted history meeting stays below the desired threshold.
    history, _ = _accept_first_party_recording(client, local_recording_id="storage-seeded-history", include_playback=True)

    async def seed_history():
        async with sessions.begin() as db:
            await apply_tenant_context(db, context)
            (await db.get(Workspace, PERSONAL_WORKSPACE_ID)).kind = "corporate"
            workspace = await db.get(Workspace, WORKSPACE_ID)
            workspace.kind, workspace.owner_user_id = "personal", USER_ID
            db.add(ExternalIdentity(user_id=USER_ID, provider="email", provider_subject="storage-publication",
                                    email="publication@example.test", is_active=True, is_verified=True))
            db.add(TrackArtifact(workspace_id=WORKSPACE_ID, meeting_id=UUID(history["meeting_id"]),
                media_revision_id=UUID(history["media_revision"]["media_revision_id"]),
                track_role="playback", codec="aac", sample_rate_hz=48000, channel_count=1, duration_seconds=60,
                byte_length=target-len(original_body), sha256="a"*64, storage_object_key="synthetic/history/meeting-review.m4a",
                status="stored", normalization_profile_version=CANONICAL_PLAYBACK_PROFILE, validated_at=datetime.now(UTC),
                derivation_kind="uploaded_candidate", source_fingerprint_sha256="b"*64, validation_version="playback_validator_v1"))
    asyncio.run(seed_history())
    monkeypatch.setattr(worker, "get_settings", lambda: client.app.state.settings)
    monkeypatch.setattr(worker, "create_engine", lambda _: engine)
    monkeypatch.setattr(worker, "create_sessionmaker", lambda _: sessions)

    async def poll():
        await worker._run_billing_reconciliation_activity({"run_id": str(uuid4())})

    async def notices_and_bytes():
        async with sessions() as db:
            await apply_tenant_context(db, context)
            projection = await project_active_playback_storage(db, workspace_id=WORKSPACE_ID, capacity_bytes=250_000_000)
            notices = list(await db.scalars(select(BillingNotificationDelivery).where(
                BillingNotificationDelivery.template_key == "storage_threshold")))
            return notices, projection.used_bytes

    async def normalize(revision_id, *, recover_missing=False):
        async with client.app_state["media_sessionmaker"]() as db:
            # Worker context comes from the finalized job, not maintenance access.
            from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
            from twobrain_rec_server.auth.context import TenantScope
            from twobrain_rec_server.db.tenant_context import apply_tenant_scope
            await apply_tenant_scope(db, TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID,
                                                   user_id=USER_ID, device_id=DEVICE_ID))
            job = await db.scalar(select(PlaybackNormalizationJob).where(PlaybackNormalizationJob.media_revision_id == revision_id))
            assert job is not None
            await apply_job_worker_scope(db, job)
            if recover_missing:
                from twobrain_rec_server.normalization.service import (
                    recover_missing_ready_normalization_job,
                )
                canonical = await db.get(TrackArtifact, job.canonical_track_artifact_id)
                assert canonical.status == "stored"
                client.app_state["storage"].delete_object(canonical.storage_object_key)
                assert await recover_missing_ready_normalization_job(db, job_id=job.id)
                await apply_job_worker_scope(db, job)
            return await run_normalization_job(db=db, storage=client.app_state["storage"], job_id=job.id,
                                              work_directory=tmp_path, pipeline=FakeNormalizationPipeline("copy"))

    try:
        asyncio.run(poll())
        before, used_before = asyncio.run(notices_and_bytes())
        # At 95/100 the seeded history already has a lower-band notice.
        assert used_before == target-len(original_body)
        first = asyncio.run(normalize(UUID(meeting["media_revision"]["media_revision_id"])))
        assert first.reused is False
        assert asyncio.run(notices_and_bytes())[1] == target
        asyncio.run(poll())
        queued, _ = asyncio.run(notices_and_bytes())
        added = [n for n in queued if n.id not in {old.id for old in before}]
        assert len(added) == 1 and added[0].safe_payload["storage_level"] == level
        assert added[0].safe_payload["storage_used_bytes"] == str(target)
        calls = []

        async def transport(**kwargs):
            async with sessions() as db:
                await apply_tenant_context(db, context)
                notice = await db.get(BillingNotificationDelivery, UUID(kwargs["delivery_key"].partition(":")[2]))
                assert notice.state == "failed" and notice.last_error_code == "postal_outcome_unknown"
            calls.append(kwargs["delivery_key"])

        async def dispatch():
            async def stop(_seconds):
                raise asyncio.CancelledError
            with monkeypatch.context() as patch:
                patch.setattr(worker, "send_billing_notification", transport)
                patch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
                with pytest.raises(asyncio.CancelledError):
                    await worker.run_billing_notification_reconciler(client.app.state.settings)
        asyncio.run(dispatch())
        assert calls.count(f"billing:{added[0].id}") == 1

        # Replace via the real upload/finalize path; normalization publishes the
        # new revision and switches the logical billing primary atomically.
        from hashlib import sha256
        endpoint = f"/api/v1/meetings/{meeting['meeting_id']}/media-revisions/upload-sessions"
        response = client.post(endpoint, headers=auth_headers(), json={
            "local_media_revision_id": "storage-replacement", "source_kind": "replace", "duration_seconds": 60,
            "expected_tracks": ["manifest", "media"],
        })
        assert response.status_code == 202
        revision_id = UUID(response.json()["media_revision"]["media_revision_id"])
        session_url = f"/api/v1/upload-sessions/{response.json()['upload_session']['session_id']}"
        tracks = []
        for track, data in {"manifest": b"{}", "media": deterministic_canonical_wav_bytes()}.items():
            assert client.put(f"{session_url}/tracks/{track}/parts/0", headers=auth_headers() | {
                "X-Byte-Offset": "0", "X-Content-SHA256": sha256(data).hexdigest()}, content=data).status_code == 200
            tracks.append(track_descriptor(track, data=data))
        assert client.post(f"{session_url}/finalize", headers=auth_headers(), json={
            "manifest_sha256": tracks[0]["sha256"], "tracks": tracks, "archive_audio": archive_audio,
        }).status_code == 200
        if level == "100":
            # A larger replacement at full capacity must be refused, without
            # consuming a generation or pretending a publication occurred.
            from twobrain_rec_server.normalization.service import NormalizationExecutionFailure
            with pytest.raises(NormalizationExecutionFailure):
                asyncio.run(normalize(revision_id))
        elif not archive_audio:
            from datetime import timedelta

            from twobrain_rec_server.db.models import ProcessingWorkflow
            from twobrain_rec_server.deletion.service import reconcile_transient_media_purges

            replacement = asyncio.run(normalize(revision_id))
            expected = target - len(original_body)
            assert asyncio.run(notices_and_bytes())[1] == expected
            asyncio.run(poll())  # Observe the real decrease before cleanup.

            async def purge_replacement():
                now = datetime.now(UTC)
                async with client.app_state["sessionmaker"]() as db:
                    workflow = await db.scalar(select(ProcessingWorkflow).where(
                        ProcessingWorkflow.media_revision_id == revision_id))
                    assert workflow is not None and workflow.archive_audio is False
                    workflow.status, workflow.transient_state = "failed_terminal", "terminal"
                    workflow.transient_terminal_at = now - timedelta(minutes=20)
                    workflow.transient_purge_due_at = now - timedelta(minutes=5)
                    await db.commit()
                async with sessions() as db:
                    await apply_tenant_context(db, MaintenanceTenantContext(
                        operation_name="deletion_purge_reconciliation", actor_id="test-storage-purge",
                        reason_category="synthetic-transient", feature_area="deletion"))
                    assert await reconcile_transient_media_purges(
                        db, storage=client.app_state["storage"], now=now, object_limit=1) == 0
                assert (await notices_and_bytes())[1] == expected
                async with sessions() as db:
                    await apply_tenant_context(db, MaintenanceTenantContext(
                        operation_name="deletion_purge_reconciliation", actor_id="test-storage-purge",
                        reason_category="synthetic-transient", feature_area="deletion"))
                    assert await reconcile_transient_media_purges(
                        db, storage=client.app_state["storage"], now=now) == 1
                    assert await reconcile_transient_media_purges(
                        db, storage=client.app_state["storage"], now=now) == 0
                async with sessions() as db:
                    await apply_tenant_context(db, context)
                    purged = await db.get(TrackArtifact, replacement.canonical_track_artifact_id)
                    assert purged.status == "purged" and purged.normalization_profile_version is None
                    assert not client.app_state["storage"].object_exists(purged.storage_object_key)
                    old = await db.get(TrackArtifact, first.canonical_track_artifact_id)
                    assert old.status == "stored"
                from sqlalchemy import text

                from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
                from twobrain_rec_server.auth.context import TenantScope
                from twobrain_rec_server.db.tenant_context import apply_tenant_scope

                app_engine = create_async_engine(app_url, poolclass=NullPool)
                try:
                    for factory, role, kind in (
                        (create_sessionmaker(app_engine), "twobrain_rec_app", "request"),
                        (client.app_state["media_sessionmaker"], "twobrain_rec_media", "worker"),
                    ):
                        async with factory() as db:
                            await apply_tenant_scope(db, TenantScope(organization_id=ORG_ID,
                                workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID), context_kind=kind)
                            assert await db.scalar(text("SELECT current_user")) == role
                            assert (await project_active_playback_storage(db,
                                workspace_id=WORKSPACE_ID, capacity_bytes=250_000_000)).used_bytes == expected
                finally:
                    await app_engine.dispose()
            asyncio.run(purge_replacement())
            assert asyncio.run(notices_and_bytes())[1] == expected
        else:
            async def replace_and_recover():
                return await asyncio.gather(
                    normalize(revision_id),
                    normalize(UUID(meeting["media_revision"]["media_revision_id"]), recover_missing=True),
                )

            # Competing new publication and old-job recovery must leave the
            # newest revision primary regardless of their commit order.
            replacement, recovered = asyncio.run(replace_and_recover())
            assert replacement.reused is False
            expected = target-len(original_body)+len(b"canonical-single-source-transcode")
            assert asyncio.run(notices_and_bytes())[1] == expected
            assert recovered.canonical_track_artifact_id != first.canonical_track_artifact_id
            assert asyncio.run(notices_and_bytes())[1] == expected
        asyncio.run(poll())
        asyncio.run(dispatch())
        final, _ = asyncio.run(notices_and_bytes())
        assert len(final) == len(queued)
        assert calls.count(f"billing:{added[0].id}") == 1
    finally:
        asyncio.run(engine.dispose())
@pytest.mark.strict_rls
def test_account_close_browser_source_commits_three_historical_notices(
    storage_publication_client, monkeypatch,
):
    from sqlalchemy import text
    from sqlalchemy.pool import NullPool

    from tests.fakes.auth_contexts import USER_ID
    from tests.unit.test_billing_money_path_e2e import _prepare_owner_session
    from twobrain_rec_server.db.models import AccountClosureRequest
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    client, maintenance_url, app_url = storage_publication_client
    workspace_id, headers = _prepare_owner_session(client)
    app_engine = create_async_engine(app_url, poolclass=NullPool)
    maintenance_engine = create_async_engine(maintenance_url, poolclass=NullPool)
    app_sessions = create_sessionmaker(app_engine)
    sessions = create_sessionmaker(maintenance_engine)
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation", actor_id="test-account-close",
        reason_category="causal-account-close", feature_area="billing",
    )
    monkeypatch.setattr(client.app.state, "db_sessionmaker", app_sessions)
    monkeypatch.setattr(client.app.state.settings, "legacy_header_auth_enabled", False)
    monkeypatch.setattr(client.app.state.settings, "env", "production")

    async def seed():
        async with app_sessions() as db:
            assert await db.scalar(text("select session_user")) == "twobrain_rec_app"
            assert await db.scalar(text(
                "select not rolsuper and not rolbypassrls from pg_roles where rolname=session_user"
            ))
        async with sessions.begin() as db:
            await apply_tenant_context(db, context)
            assert await db.scalar(text("select session_user")) == "twobrain_rec_maintenance"
            assert await db.scalar(text(
                "select not rolsuper and not rolbypassrls from pg_roles where rolname=session_user"
            ))
            db.add_all([
                BillingNotificationPreference(user_id=USER_ID, optional_email_enabled=False),
                WorkspaceSubscription(
                    workspace_id=workspace_id, billing_owner_id=USER_ID,
                    recurring_allowed=True, recurring_authority_version=41,
                ),
            ])

    async def saved():
        # Every observation uses a new transaction after the real HTTP commit.
        async with sessions() as db:
            await apply_tenant_context(db, context)
            requests = list(await db.scalars(select(AccountClosureRequest).where(
                AccountClosureRequest.workspace_id == workspace_id,
            ).order_by(AccountClosureRequest.requested_at, AccountClosureRequest.id)))
            notices = list(await db.scalars(select(BillingNotificationDelivery).where(
                BillingNotificationDelivery.workspace_id == workspace_id,
            )))
            sub = await db.get(WorkspaceSubscription, workspace_id)
            return requests, notices, (sub.recurring_allowed, sub.recurring_authority_version)

    def post(path, data=None):
        response = client.post(path, headers=headers, data=data, follow_redirects=False)
        assert response.status_code == 303
        return response

    try:
        asyncio.run(seed())
        response = post("/settings/account/close", {"confirm_close": "Закрыть аккаунт"})
        assert response.headers["location"].endswith("account_close=scheduled")
        first, _, recurring = asyncio.run(saved())
        assert len(first) == 1 and first[0].state == "scheduled"
        assert recurring == (False, 42)
        post("/settings/account/close", {"confirm_close": "Закрыть аккаунт"})
        repeated, _, recurring = asyncio.run(saved())
        assert len(repeated) == 1 and repeated[0].id == first[0].id
        assert repeated[0].requested_at == first[0].requested_at
        assert recurring == (False, 42)
        response = post("/settings/account/close/cancel")
        assert response.headers["location"].endswith("account_close=canceled")
        post("/settings/account/close", {"confirm_close": "Закрыть аккаунт"})
        requests, notices, recurring = asyncio.run(saved())
        assert len(requests) == 2 and requests[0].state == "canceled" and requests[1].state == "scheduled"
        assert recurring == (False, 42)
        assert len(notices) == 3
        by_event = {row.event_id: row for row in notices}
        for request, phases in ((requests[0], ("scheduled", "canceled")), (requests[1], ("scheduled",))):
            for phase in phases:
                row = by_event[f"account.close:{request.id.hex}:{phase}"]
                assert row.recipient_id == USER_ID and row.template_key == "account_close"
                assert row.channel == "email" and row.state == "pending" and row.attempts == 0
                expected = {
                    "phase": phase, "account_close_request_id": request.id.hex,
                    "account_close_requested_at": request.requested_at.isoformat(),
                    "account_close_finalize_at": request.finalize_at.isoformat(),
                    "action_path": "/settings/account",
                }
                if phase == "canceled":
                    expected["account_close_canceled_at"] = request.canceled_at.isoformat()
                assert row.safe_payload == expected

        calls = []
        from uuid import UUID

        from twobrain_rec_server.db.models import (
            ExternalIdentity,
            UserIdentity,
            Workspace,
            WorkspaceMembership,
        )

        async def send(**kwargs):
            notice_id = UUID(kwargs["delivery_key"].removeprefix("billing:"))
            async with sessions() as db:
                await apply_tenant_context(db, context)
                saved_row = await db.scalar(select(BillingNotificationDelivery).where(
                    BillingNotificationDelivery.id == notice_id,
                ).with_for_update(nowait=True))
                assert (saved_row.state, saved_row.attempts, saved_row.last_error_code) == (
                    "failed", 1, "postal_outcome_unknown",
                )
                request = await db.scalar(select(AccountClosureRequest).where(
                    AccountClosureRequest.id == UUID(saved_row.safe_payload["account_close_request_id"]),
                ).with_for_update(nowait=True))
                assert request is not None
                for model, predicate in (
                    (Workspace, Workspace.id == workspace_id),
                    (UserIdentity, UserIdentity.id == USER_ID),
                    (WorkspaceMembership, (WorkspaceMembership.workspace_id == workspace_id) & (WorkspaceMembership.user_id == USER_ID)),
                    (ExternalIdentity, ExternalIdentity.user_id == USER_ID),
                ):
                    assert list(await db.scalars(select(model).where(predicate).with_for_update(nowait=True)))
            assert kwargs["recipient_email"] == "verified-owner@example.test"
            assert kwargs["plain_body"].count(str(client.app.state.settings.public_base_url).rstrip("/") + "/settings/account") == 1
            assert kwargs["html_body"].count("href=") == 1
            assert "МСК" in kwargs["plain_body"] and "Проверьте текущий статус" in kwargs["plain_body"]
            for private in (str(USER_ID), str(workspace_id), request.id.hex, "token=", "provider"):
                assert private not in kwargs["plain_body"] + kwargs["html_body"]
            calls.append(kwargs)

        async def stop(_seconds):
            raise asyncio.CancelledError

        async def dispatch():
            with pytest.raises(asyncio.CancelledError):
                await worker.run_billing_notification_reconciler(client.app.state.settings)

        monkeypatch.setattr(worker, "create_engine", lambda _: maintenance_engine)
        monkeypatch.setattr(worker, "send_billing_notification", send)
        monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
        asyncio.run(dispatch())
        _, delivered, recurring = asyncio.run(saved())
        assert len(calls) == 3 and len({call["delivery_key"] for call in calls}) == 3
        assert all((row.state, row.attempts, row.last_error_code) == ("delivered", 1, None) for row in delivered)
        assert recurring == (False, 42)
        assert sum("Вы запланировали" in call["plain_body"] for call in calls) == 2
        assert sum("Вы отменили" in call["plain_body"] for call in calls) == 1
        asyncio.run(dispatch())
        assert len(calls) == 3
    finally:
        asyncio.run(app_engine.dispose())
        asyncio.run(maintenance_engine.dispose())



@pytest.fixture
def account_close_case(storage_publication_client, monkeypatch, request):
    from datetime import UTC, datetime

    from sqlalchemy import text
    from sqlalchemy.pool import NullPool

    from tests.fakes.auth_contexts import USER_ID
    from tests.unit.test_billing_money_path_e2e import _prepare_owner_session
    from twobrain_rec_server.db.models import AccountClosureRequest
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    client, maintenance_url, app_url = storage_publication_client
    workspace, headers = _prepare_owner_session(client)
    app = create_async_engine(app_url, poolclass=NullPool)
    maintenance = create_async_engine(maintenance_url, poolclass=NullPool)
    sessions = create_sessionmaker(maintenance)
    context = MaintenanceTenantContext(operation_name="billing_reconciliation", actor_id="test-account-close",
        reason_category="account-close-matrix", feature_area="billing")
    x = SimpleNamespace(client=client, workspace=workspace, user=USER_ID, headers=headers,
        app=app, maintenance=maintenance, sessions=sessions, context=context,
        owner=client.app_state["sessionmaker"], calls=[], failure=None, now=datetime.now(UTC))
    monkeypatch.setattr(client.app.state, "db_sessionmaker", create_sessionmaker(app))
    monkeypatch.setattr(client.app.state.settings, "legacy_header_auth_enabled", False)
    monkeypatch.setattr(client.app.state.settings, "env", "production")

    async def seed():
        async with sessions.begin() as db:
            await apply_tenant_context(db, context)
            assert (await db.execute(text("SELECT session_user,rolsuper,rolbypassrls FROM pg_roles WHERE rolname=session_user"))).one() == ("twobrain_rec_maintenance", False, False)
            db.add_all([BillingNotificationPreference(user_id=USER_ID, optional_email_enabled=False),
                WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID,
                    recurring_allowed=True, recurring_authority_version=41)])

    def post(path="/settings/account/close", **kwargs):
        return client.post(path, headers=headers, data={"confirm_close": "Закрыть аккаунт"}, follow_redirects=False, **kwargs)

    async def snapshot():
        async with sessions() as db:
            await apply_tenant_context(db, context)
            sources = list(await db.scalars(select(AccountClosureRequest).where(AccountClosureRequest.workspace_id == workspace).order_by(AccountClosureRequest.requested_at)))
            notices = list(await db.scalars(select(BillingNotificationDelivery).where(BillingNotificationDelivery.workspace_id == workspace).order_by(BillingNotificationDelivery.created_at)))
            sub = await db.get(WorkspaceSubscription, workspace)
            return sources, notices, (sub.recurring_allowed, sub.recurring_authority_version)

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return x.now.astimezone(tz) if tz else x.now.replace(tzinfo=None)

    async def send(**kwargs):
        x.calls.append(kwargs)
        if x.failure is not None:
            raise x.failure

    async def stop(_seconds):
        raise asyncio.CancelledError

    async def dispatch():
        with pytest.raises(asyncio.CancelledError):
            await worker.run_billing_notification_reconciler(client.app.state.settings)

    # Separate synthetic tenant is seeded only by the fixture owner.
    from uuid import uuid4

    from twobrain_rec_server.db.models import (
        Organization,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
    )

    x.foreign_org, x.foreign_user, x.foreign_workspace = uuid4(), uuid4(), uuid4()

    async def foreign_tenant():
        async with x.owner() as db:
            db.add(Organization(id=x.foreign_org, slug=f"acn-foreign-{x.foreign_org.hex}", name="Synthetic foreign"))
            await db.flush()
            db.add(UserIdentity(id=x.foreign_user, organization_id=x.foreign_org, external_subject=x.foreign_user.hex))
            await db.flush()
            db.add(Workspace(id=x.foreign_workspace, organization_id=x.foreign_org, owner_user_id=x.foreign_user,
                slug="foreign-personal", name="Synthetic foreign personal", kind="personal"))
            await db.flush()
            db.add(WorkspaceMembership(workspace_id=x.foreign_workspace, user_id=x.foreign_user, role="owner", status="active"))
            await db.commit()

    x.post, x.snapshot, x.dispatch = post, snapshot, dispatch
    monkeypatch.setattr(worker, "create_engine", lambda _: maintenance)
    monkeypatch.setattr(worker, "send_billing_notification", send)
    monkeypatch.setattr(worker, "datetime", Clock)
    monkeypatch.setattr(worker, "asyncio", SimpleNamespace(CancelledError=asyncio.CancelledError, sleep=stop))
    try:
        asyncio.run(seed())
        asyncio.run(foreign_tenant())
        if getattr(request, "param", "scheduled") != "empty":
            assert post().status_code == 303
            sources, notices, _ = asyncio.run(snapshot())
            assert len(sources) == len(notices) == 1
            x.request_id, x.notice_id = sources[0].id, notices[0].id
        yield x
    finally:
        asyncio.run(app.dispose())
        asyncio.run(maintenance.dispose())


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("damage", [
    "workspace_owner", "workspace_kind", "identity_closed", "identity_merged", "membership_role",
    "membership_inactive", "email_unverified", "email_inactive", "email_empty", "email_missing",
    "source_missing", "policy", "interval", "completed", "finalizing", "finalized_at", "frozen_content", "started",
    "cancel_phase", "cancel_date_missing", "cancel_date_early", "cancel_date_late",
])
async def test_account_close_sender_suppresses_lost_source_or_original_rights(account_close_case, damage):
    from datetime import UTC, datetime

    from twobrain_rec_server.db.models import (
        AccountClosureRequest,
        ExternalIdentity,
        UserIdentity,
        Workspace,
        WorkspaceMembership,
    )

    x = account_close_case
    async with x.owner() as db:
        source = await db.get(AccountClosureRequest, x.request_id)
        if damage == "workspace_owner":
            (await db.get(Workspace, x.workspace)).owner_user_id = None
        elif damage == "workspace_kind":
            (await db.get(Workspace, x.workspace)).kind = "linked"
        elif damage in {"identity_closed", "identity_merged"}:
            identity = await db.get(UserIdentity, x.user)
            if damage == "identity_closed":
                identity.status = "closed"
            else:
                identity.merged_into_user_id = x.foreign_user
        elif damage.startswith("membership"):
            membership = await db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == x.workspace, WorkspaceMembership.user_id == x.user))
            if damage == "membership_role":
                membership.role = "member"
            else:
                membership.status = "inactive"
        elif damage.startswith("email"):
            emails = list(await db.scalars(select(ExternalIdentity).where(ExternalIdentity.user_id == x.user)))
            for email in emails:
                if damage == "email_missing":
                    await db.delete(email)
                elif damage == "email_unverified":
                    email.is_verified = False
                elif damage == "email_inactive":
                    email.is_active = False
                else:
                    email.email = ""
        elif damage == "source_missing":
            await db.delete(source)
        elif damage == "policy":
            source.policy_version = "account-close-v2"
        elif damage == "interval":
            source.finalize_at += timedelta(seconds=1)
        elif damage in {"completed", "finalizing"}:
            source.state = damage
        elif damage == "finalized_at":
            source.finalized_at = datetime.now(UTC)
        elif damage == "frozen_content":
            source.metadata_json = {"content_workspace_ids": []}
        elif damage == "started":
            source.metadata_json = {"finalization_started_at": "synthetic"}
        elif damage.startswith("cancel"):
            source.state = "canceled" if damage != "cancel_phase" else "scheduled"
            source.canceled_at = (None if damage == "cancel_date_missing" else
                source.requested_at - timedelta(seconds=1) if damage == "cancel_date_early" else source.finalize_at)
            notice = await db.get(BillingNotificationDelivery, x.notice_id)
            notice.event_id = f"account.close:{source.id.hex}:canceled"
            notice.safe_payload = {**notice.safe_payload, "phase": "canceled", "account_close_canceled_at": source.requested_at.isoformat()}
        await db.commit()
    await x.dispatch()
    _, notices, recurring = await x.snapshot()
    assert [(row.state, row.attempts) for row in notices] == [("suppressed", 0)]
    assert x.calls == [] and recurring == (False, 42)
    await x.dispatch()
    assert x.calls == []


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("damage", ["empty", "list", "phase", "request", "requested", "event", "recipient", "workspace", "cancel", "retry_null", "retry_bool", "retry_string", "retry_float", "retry_negative", "retry_overflow", "retry_dict", "retry_list"])
async def test_account_close_sender_suppresses_legacy_or_tampered_snapshot(account_close_case, damage):
    from tests.fakes.auth_contexts import WORKSPACE_ID

    x = account_close_case
    async with x.owner() as db:
        row = await db.get(BillingNotificationDelivery, x.notice_id)
        payload = dict(row.safe_payload)
        if damage in {"empty", "list"}:
            row.safe_payload = {} if damage == "empty" else []
        elif damage == "event":
            row.event_id = "account.close:foreign:scheduled"
        elif damage == "recipient":
            row.recipient_id = x.foreign_user
        elif damage == "workspace":
            row.workspace_id = WORKSPACE_ID
        else:
            changes = {"phase": ("phase", "unknown"), "request": ("account_close_request_id", "f" * 32),
                "requested": ("account_close_requested_at", "2026-01-01T00:00:00+00:00"),
                "cancel": ("phase", "canceled"),
                "retry_null": ("_retry_not_before", None), "retry_bool": ("_retry_not_before", True),
                "retry_string": ("_retry_not_before", "0"), "retry_float": ("_retry_not_before", 0.5),
                "retry_negative": ("_retry_not_before", -1), "retry_overflow": ("_retry_not_before", 9223372036854775808),
                "retry_dict": ("_retry_not_before", {}), "retry_list": ("_retry_not_before", [])}
            key, value = changes[damage]
            row.safe_payload = payload | {key: value}
        await db.commit()
    await x.dispatch()
    async with x.owner() as db:
        row = await db.get(BillingNotificationDelivery, x.notice_id)
        assert (row.state, row.attempts) == ("suppressed", 0)
    assert x.calls == []
    await x.dispatch()
    assert x.calls == []


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["known_retry", "unknown", "crash", "read_error"])
async def test_account_close_sender_bounds_retry_and_never_repeats_unknown(account_close_case, monkeypatch, outcome):
    from datetime import UTC, datetime

    from sqlalchemy import text

    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError

    x, reads = account_close_case, []
    original = worker.account_close_notice_recipient

    async def unavailable(db, row):
        await original(db, row)
        reads.append(True)
        await db.execute(text("SELECT 1/0"))

    if outcome == "read_error":
        monkeypatch.setattr(worker, "account_close_notice_recipient", unavailable)
    elif outcome == "crash":
        x.failure = asyncio.CancelledError()
    else:
        x.failure = EmailLoginDeliveryError("synthetic", retryable=True, outcome_unknown=outcome == "unknown")
    await x.dispatch()
    first = (await x.snapshot())[1][0]
    assert first.attempts == 1
    if outcome in {"unknown", "crash"}:
        assert (first.state, first.last_error_code) == ("failed", "postal_outcome_unknown")
        x.now += timedelta(days=1)
        await x.dispatch()
        assert len(x.calls) == 1
        assert (await x.snapshot())[1][0].attempts == 1
        return
    assert first.state == "retry"
    due = first.safe_payload["_retry_not_before"]
    assert type(due) is int and due >= x.now.timestamp() + 60
    await x.dispatch()
    x.now = datetime.fromtimestamp(due - 1, UTC)
    await x.dispatch()
    assert len(reads) == (1 if outcome == "read_error" else 0)
    assert len(x.calls) == (1 if outcome == "known_retry" else 0)
    for attempt in range(2, 6):
        x.now = datetime.fromtimestamp(due, UTC)
        await x.dispatch()
        row = (await x.snapshot())[1][0]
        assert row.attempts == attempt and row.state == ("retry" if attempt < 5 else "failed")
        due = row.safe_payload["_retry_not_before"]
        if attempt < 5:
            assert due >= x.now.timestamp() + 60
    x.now += timedelta(days=1)
    await x.dispatch()
    assert len(reads) == (5 if outcome == "read_error" else 0)
    assert len(x.calls) == (5 if outcome == "known_retry" else 0)
    assert (await x.snapshot())[2] == (False, 42)


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("held", ["request", "workspace", "identity", "membership", "email"])
async def test_account_close_sender_nowait_source_lock_retries_after_release(account_close_case, held):
    from datetime import UTC, datetime

    from sqlalchemy import text

    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    x = account_close_case
    statement = {
        "request": "SELECT id FROM account_closure_requests WHERE id=:request FOR UPDATE",
        "workspace": "SELECT id FROM workspaces WHERE id=:workspace FOR UPDATE",
        "identity": "SELECT id FROM user_identities WHERE id=:user FOR UPDATE",
        "membership": "SELECT user_id FROM workspace_memberships WHERE workspace_id=:workspace AND user_id=:user FOR UPDATE",
        "email": "SELECT id FROM external_identities WHERE user_id=:user AND is_active AND is_verified FOR UPDATE",
    }[held]
    async with x.sessions() as db:
        await apply_tenant_context(db, x.context)
        assert list(await db.execute(text(statement), {"request": x.request_id, "workspace": x.workspace, "user": x.user}))
        await asyncio.wait_for(x.dispatch(), timeout=3)
        row = (await x.snapshot())[1][0]
        assert (row.state, row.attempts, row.last_error_code) == ("retry", 1, "account_close_authorization_unavailable")
        due = row.safe_payload["_retry_not_before"]
        assert due >= x.now.timestamp() + 60 and x.calls == []
    await x.dispatch()
    assert x.calls == []
    x.now = datetime.fromtimestamp(due, UTC)
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts) == ("delivered", 2) and len(x.calls) == 1
    await x.dispatch()
    assert len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.parametrize("account_close_case", ["empty"], indirect=True)
@pytest.mark.parametrize("phase,failure", [("scheduled", "read"), ("scheduled", "enqueue"), ("canceled", "read"), ("canceled", "enqueue")])
def test_account_close_source_errors_roll_back_transition_renewal_and_queue(account_close_case, monkeypatch, phase, failure):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError

    from twobrain_rec_server.auth import account_closure_notifications as notices

    x = account_close_case
    if phase == "canceled":
        assert x.post().status_code == 303
    before = asyncio.run(x.snapshot())
    original = notices._recipient if failure == "read" else notices.enqueue_billing_event

    async def fail(db, *args, **kwargs):
        await original(db, *args, **kwargs)
        if failure == "read":
            await db.execute(text("SELECT 1/0"))
        raise RuntimeError("synthetic_account_close_enqueue_error")

    monkeypatch.setattr(notices, "_recipient" if failure == "read" else "enqueue_billing_event", fail)
    with pytest.raises(DBAPIError if failure == "read" else RuntimeError):
        x.post("/settings/account/close/cancel" if phase == "canceled" else "/settings/account/close")
    after = asyncio.run(x.snapshot())
    assert [(r.id, r.state, r.canceled_at) for r in after[0]] == [(r.id, r.state, r.canceled_at) for r in before[0]]
    assert [(r.id, r.safe_payload) for r in after[1]] == [(r.id, r.safe_payload) for r in before[1]]
    assert after[2] == before[2] and x.calls == []


@pytest.mark.strict_rls
@pytest.mark.parametrize("account_close_case", ["empty"], indirect=True)
def test_account_close_missing_address_does_not_backfill_and_service_rollback_is_atomic(account_close_case):
    from datetime import UTC, datetime

    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID
    from twobrain_rec_server.auth.account_closure import schedule_account_close
    from twobrain_rec_server.auth.context import TenantScope
    from twobrain_rec_server.db.models import ExternalIdentity
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    x = account_close_case

    async def rolled_back():
        async with create_sessionmaker(x.app)() as db:
            await apply_tenant_scope(db, TenantScope(organization_id=ORG_ID, workspace_id=x.workspace, user_id=x.user, device_id=DEVICE_ID))
            await schedule_account_close(db, workspace_id=x.workspace, user_id=x.user, now=datetime.now(UTC))
            assert len(list(await db.scalars(select(BillingNotificationDelivery)))) == 1
            await db.rollback()
    asyncio.run(rolled_back())
    assert asyncio.run(x.snapshot()) == ([], [], (True, 41))

    async def address(active):
        async with x.owner() as db:
            for row in await db.scalars(select(ExternalIdentity).where(ExternalIdentity.user_id == x.user)):
                row.is_verified = active
            await db.commit()
    asyncio.run(address(False))
    assert x.post().status_code == 303
    requests, notices, recurring = asyncio.run(x.snapshot())
    assert len(requests) == 1 and notices == [] and recurring == (False, 42)
    asyncio.run(address(True))
    assert x.post().status_code == 303
    asyncio.run(x.dispatch())
    assert asyncio.run(x.snapshot())[1] == [] and x.calls == []
    assert x.post("/settings/account/close/cancel").status_code == 303
    assert len(asyncio.run(x.snapshot())[1]) == 1


@pytest.mark.strict_rls
@pytest.mark.parametrize("account_close_case", ["empty"], indirect=True)
@pytest.mark.parametrize("missing", ["confirmation", "csrf", "session", "owner"])
def test_account_close_browser_refuses_missing_authority_without_queue(account_close_case, missing):
    from twobrain_rec_server.db.models import WorkspaceMembership

    x = account_close_case
    headers, data = x.headers, {"confirm_close": "Закрыть аккаунт"}
    if missing == "confirmation":
        data = {}
    elif missing == "csrf":
        headers = {}
    elif missing == "session":
        x.client.cookies.clear()
    else:
        async def demote():
            async with x.owner() as db:
                row = await db.scalar(select(WorkspaceMembership).where(WorkspaceMembership.workspace_id == x.workspace, WorkspaceMembership.user_id == x.user))
                row.role = "member"
                await db.commit()
        asyncio.run(demote())
    response = x.client.post("/settings/account/close", headers=headers, data=data, follow_redirects=False)
    assert response.status_code in {302, 303, 401, 403, 422}
    assert "account_close=scheduled" not in response.headers.get("location", "")
    assert asyncio.run(x.snapshot()) == ([], [], (True, 41))


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["payload", "template", "channel", "due", "email", "closed"])
async def test_account_close_claim_rechecks_changes_between_poll_and_claim(account_close_case, monkeypatch, change):
    from twobrain_rec_server.db.models import ExternalIdentity, UserIdentity

    x, changed = account_close_case, []
    original = worker.account_close_notice_recipient

    async def mutate(db, row):
        if not changed:
            changed.append(True)
            async with x.owner() as other:
                notice = await other.get(BillingNotificationDelivery, x.notice_id)
                if change == "payload":
                    notice.safe_payload = {**notice.safe_payload, "account_close_requested_at": "2026-01-01T00:00:00+00:00"}
                elif change == "template":
                    notice.template_key = "payment_succeeded"
                elif change == "channel":
                    notice.channel = "in_app"
                elif change == "due":
                    notice.safe_payload = {**notice.safe_payload, "_retry_not_before": int(x.now.timestamp()) + 300}
                elif change == "email":
                    for email in await other.scalars(select(ExternalIdentity).where(ExternalIdentity.user_id == x.user)):
                        email.email = "changed-owner@example.test"
                else:
                    (await other.get(UserIdentity, x.user)).status = "closed"
                await other.commit()
        return await original(db, row)

    monkeypatch.setattr(worker, "account_close_notice_recipient", mutate)
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    if change == "email":
        assert row.state == "delivered" and len(x.calls) == 1
        assert x.calls[0]["recipient_email"] == "changed-owner@example.test"
    elif change == "closed":
        assert row.state == "suppressed" and row.attempts == 0 and x.calls == []
    else:
        assert row.state == "pending" and row.attempts == 0 and x.calls == []
        if change == "payload":
            await x.dispatch()
            assert (await x.snapshot())[1][0].state == "suppressed" and x.calls == []


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("outcome", ["rejected", "ack_lost"])
async def test_account_close_claim_commit_failure_never_calls_transport(account_close_case, monkeypatch, outcome):
    from sqlalchemy import text
    from sqlalchemy.exc import DBAPIError
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    x, faults = account_close_case, []
    if outcome == "rejected":
        async with x.owner() as db:
            await db.execute(text("""CREATE FUNCTION public.test_only_acn_claim_failure() RETURNS trigger LANGUAGE plpgsql AS $$
                BEGIN
                    IF NEW.template_key='account_close' AND NEW.state='failed' AND NEW.last_error_code='postal_outcome_unknown' THEN
                        RAISE EXCEPTION 'synthetic_acn_claim_failure';
                    END IF;
                    RETURN NEW;
                END $$"""))
            await db.execute(text("""CREATE CONSTRAINT TRIGGER zz_test_acn_claim_failure AFTER UPDATE
                ON public.billing_notification_deliveries DEFERRABLE INITIALLY DEFERRED
                FOR EACH ROW EXECUTE FUNCTION public.test_only_acn_claim_failure()"""))
            await db.commit()
    else:
        class MissingAckSession(AsyncSession):
            async def commit(self):
                claim = any(isinstance(row, BillingNotificationDelivery) and row.state == "failed" and row.last_error_code == "postal_outcome_unknown" for row in self.dirty)
                await super().commit()
                if claim and not faults:
                    faults.append(True)
                    raise DBAPIError(None, None, Exception("synthetic_commit_ack_lost"), connection_invalidated=True)
        monkeypatch.setattr(worker, "create_sessionmaker", lambda engine: async_sessionmaker(engine, class_=MissingAckSession, expire_on_commit=False))
    try:
        await x.dispatch()
    finally:
        if outcome == "rejected":
            async with x.owner() as db:
                await db.execute(text("DROP TRIGGER zz_test_acn_claim_failure ON public.billing_notification_deliveries"))
                await db.execute(text("DROP FUNCTION public.test_only_acn_claim_failure()"))
                await db.commit()
    row = (await x.snapshot())[1][0]
    assert row.attempts == 1 and x.calls == []
    if outcome == "ack_lost":
        assert row.state == "failed" and row.last_error_code == "postal_outcome_unknown" and faults == [True]
        await x.dispatch()
        assert x.calls == []
    else:
        from datetime import UTC, datetime

        assert row.state == "retry"
        x.now = datetime.fromtimestamp(row.safe_payload["_retry_not_before"], UTC)
        await x.dispatch()
        row = (await x.snapshot())[1][0]
        assert row.state == "delivered" and row.attempts == 2 and len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_account_close_concurrent_senders_share_one_durable_claim(account_close_case, monkeypatch):
    x = account_close_case
    entered, release = asyncio.Event(), asyncio.Event()
    original = worker.send_billing_notification

    async def paused(**kwargs):
        entered.set()
        await release.wait()
        await original(**kwargs)

    monkeypatch.setattr(worker, "send_billing_notification", paused)
    first = asyncio.create_task(x.dispatch())
    try:
        await asyncio.wait_for(entered.wait(), timeout=3)
        await asyncio.wait_for(x.dispatch(), timeout=3)
    finally:
        release.set()
    await asyncio.wait_for(first, timeout=3)
    assert len(x.calls) == 1
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts) == ("delivered", 1)
    await x.dispatch()
    assert len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_account_close_claim_selects_minimum_current_verified_email(account_close_case):
    from uuid import uuid4

    from twobrain_rec_server.db.models import ExternalIdentity

    x = account_close_case
    async with x.owner() as db:
        db.add_all([
            ExternalIdentity(user_id=x.user, provider="email", provider_subject=uuid4().hex,
                email="aaa-current@example.test", is_verified=True, is_active=True),
            ExternalIdentity(user_id=x.user, provider="email", provider_subject=uuid4().hex,
                email="000-unverified@example.test", is_verified=False, is_active=True),
            ExternalIdentity(user_id=x.user, provider="email", provider_subject=uuid4().hex,
                email="000-inactive@example.test", is_verified=True, is_active=False),
        ])
        await db.commit()
    await x.dispatch()
    assert len(x.calls) == 1 and x.calls[0]["recipient_email"] == "aaa-current@example.test"
    row = (await x.snapshot())[1][0]
    assert row.recipient_id == x.user and "email" not in row.safe_payload


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["merge", "closure"])
async def test_account_close_sender_nowait_under_real_reverse_order_boundary(account_close_case, first):
    from datetime import UTC, datetime

    from twobrain_rec_server.auth.account_closure import begin_account_close_finalization
    from twobrain_rec_server.auth.account_merge import _lock_merge_domain_rows
    from twobrain_rec_server.db.models import AccountClosureRequest, UserIdentity
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    x = account_close_case
    async with x.sessions() as db:
        await apply_tenant_context(db, x.context)
        if first == "merge":
            assert await db.get(UserIdentity, x.user, with_for_update=True)
            await _lock_merge_domain_rows(db, survivor_user_id=x.user, source_user_id=x.foreign_user)
        else:
            source = await db.get(AccountClosureRequest, x.request_id)
            await begin_account_close_finalization(db, request_id=x.request_id, now=source.finalize_at)
        await asyncio.wait_for(x.dispatch(), timeout=3)
        row = (await x.snapshot())[1][0]
        assert row.state == "retry" and row.attempts == 1 and x.calls == []
        due = row.safe_payload["_retry_not_before"]
        await db.rollback()
    x.now = datetime.fromtimestamp(due, UTC)
    await x.dispatch()
    assert (await x.snapshot())[1][0].state == "delivered" and len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_account_close_runtime_scope_cannot_read_foreign_source_or_claim_without_context(account_close_case):
    from tests.fakes.auth_contexts import DEVICE_ID
    from twobrain_rec_server.auth.account_closure_notifications import (
        account_close_notice_recipient,
    )
    from twobrain_rec_server.auth.context import TenantScope
    from twobrain_rec_server.db.models import AccountClosureRequest
    from twobrain_rec_server.db.session import create_sessionmaker
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope

    x = account_close_case
    original = (await x.snapshot())[1][0]
    async with create_sessionmaker(x.app)() as db:
        await apply_tenant_scope(db, TenantScope(organization_id=x.foreign_org, workspace_id=x.foreign_workspace,
            user_id=x.foreign_user, device_id=DEVICE_ID))
        assert await db.get(AccountClosureRequest, x.request_id) is None
        assert await db.get(BillingNotificationDelivery, x.notice_id) is None
    async with x.sessions() as db:
        assert await account_close_notice_recipient(db, original) is None
    await x.dispatch()
    assert (await x.snapshot())[1][0].state == "delivered" and len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("due", [True, -1])
async def test_account_close_invalid_retry_is_suppressed_even_when_source_read_fails(account_close_case, monkeypatch, due):
    from sqlalchemy import text

    x = account_close_case
    async with x.owner() as db:
        notice = await db.get(BillingNotificationDelivery, x.notice_id)
        notice.safe_payload = {**notice.safe_payload, "_retry_not_before": due}
        await db.commit()
    original = worker.account_close_notice_recipient

    async def unavailable(db, row):
        await original(db, row)
        await db.execute(text("SELECT 1/0"))

    monkeypatch.setattr(worker, "account_close_notice_recipient", unavailable)
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts, row.last_error_code) == ("suppressed", 0, "account_close_snapshot_invalid")
    assert x.calls == []


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("claimed_first", [False, True])
async def test_account_close_real_finalization_stops_new_claim_but_cannot_revoke_saved_claim(account_close_case, monkeypatch, claimed_first):
    from twobrain_rec_server.auth.account_closure import begin_account_close_finalization
    from twobrain_rec_server.db.models import AccountClosureRequest
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    x = account_close_case

    async def finalize():
        async with x.sessions() as db:
            await apply_tenant_context(db, MaintenanceTenantContext(operation_name="billing_reconciliation",
                actor_id="test-account-close", reason_category="account_close_finalization", feature_area="account"))
            source = await db.get(AccountClosureRequest, x.request_id)
            result, _ = await begin_account_close_finalization(db, request_id=x.request_id, now=source.finalize_at)
            assert result.state == "finalizing"
            await db.commit()

    if claimed_first:
        original = worker.send_billing_notification

        async def late(**kwargs):
            row = (await x.snapshot())[1][0]
            assert (row.state, row.attempts, row.last_error_code) == ("failed", 1, "postal_outcome_unknown")
            await finalize()
            await original(**kwargs)
        monkeypatch.setattr(worker, "send_billing_notification", late)
    else:
        await finalize()
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts) == (("delivered", 1) if claimed_first else ("suppressed", 0))
    assert len(x.calls) == int(claimed_first)
    await x.dispatch()
    assert len(x.calls) == int(claimed_first)


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_account_close_pre_finalization_blocked_request_remains_historical(account_close_case):
    from twobrain_rec_server.db.models import AccountClosureRequest

    x = account_close_case
    async with x.owner() as db:
        (await db.get(AccountClosureRequest, x.request_id)).state = "blocked"
        await db.commit()
    await x.dispatch()
    assert (await x.snapshot())[1][0].state == "delivered" and len(x.calls) == 1


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_account_close_known_transport_refusal_recovers_at_saved_due_once(account_close_case):
    from datetime import UTC, datetime

    from twobrain_rec_server.auth.email_delivery import EmailLoginDeliveryError

    x = account_close_case
    x.failure = EmailLoginDeliveryError("synthetic", retryable=True, outcome_unknown=False)
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts) == ("retry", 1)
    due = row.safe_payload["_retry_not_before"]
    assert due >= x.now.timestamp() + 60
    x.failure = None
    await x.dispatch()
    assert len(x.calls) == 1
    x.now = datetime.fromtimestamp(due, UTC)
    await x.dispatch()
    row = (await x.snapshot())[1][0]
    assert (row.state, row.attempts, row.last_error_code) == ("delivered", 2, None)
    assert len(x.calls) == 2
    await x.dispatch()
    assert len(x.calls) == 2
