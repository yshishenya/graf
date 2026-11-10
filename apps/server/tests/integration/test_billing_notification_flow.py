import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url

from tests.fixtures.postgres_test_database import prepare_schema
from tests.integration import test_billing_renewal_planner_postgres as planner
from tests.integration.test_billing_renewal_planner_postgres import paid_workspace as paid_workspace
from tests.integration.test_rls_postgres_policies import _create_probe_role, _drop_probe_role
from twobrain_rec_server.billing.events import BillingEvent, notification_kind_for
from twobrain_rec_server.billing.notifications import (
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


@pytest.fixture
async def billing_maintenance_probe_url(postgres_clean_database_url, postgres_advisory_lock):
    # The sender polls the whole queue: isolate it from other modules' pending rows.
    url = postgres_clean_database_url
    await asyncio.to_thread(prepare_schema, url)
    role, password = await _create_probe_role(url, role_name="twobrain_rec_maintenance")
    try:
        yield make_url(url).set(username=role, password=password).render_as_string(hide_password=False)
    finally:
        await _drop_probe_role(url, role)



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
