import pytest

from twobrain_rec_server.billing.events import BillingEvent, notification_kind_for
from twobrain_rec_server.billing.notifications import (
    REFERRAL_NOTICE_KINDS,
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
    assert event.safe_payload.get("action_path") == ("/referrals" if kind in REFERRAL_NOTICE_KINDS else "/billing")


def test_refund_and_unknown_provider_events_are_not_customer_notifications() -> None:
    assert BillingNotification.RECEIPT_AVAILABLE in {
        notification_kind_for(BillingEvent.RECEIPT_AVAILABLE)
    }
    with pytest.raises(ValueError):
        notification_kind_for("refund.succeeded")
    with pytest.raises(ValueError):
        notification_kind_for("provider.unknown")


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
