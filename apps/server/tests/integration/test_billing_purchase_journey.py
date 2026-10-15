"""Real HTTP/routes/PostgreSQL; only the provider transport is synthetic."""

import asyncio
import importlib.util
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, select

from tests.unit.test_billing_money_path_e2e import (
    _approved_month_catalog,
    _configure_billing,
    _deliver_webhook,
    _FakeYooKassa,
    _payment_webhook,
    _prepare_owner_session,
)
from twobrain_rec_server.billing import webhook_reconciliation
from twobrain_rec_server.billing.promotions import promo_code_hash
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import (
    BillingAcceptanceBudget,
    BillingAuditEvent,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingStorageEntitlementGrant,
    PromotionCampaign,
    PromotionRedemption,
    WorkspaceSubscription,
)
from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION


def quote_id(response):
    assert response.status_code == 200
    match = re.search(r'name="quote_id" value="([^"]+)"', response.text)
    assert match, "confirmation did not contain a bound quote"
    return match.group(1)


def seed_catalog_and_budget(client, workspace):
    path = (
        Path(__file__).parents[2]
        / "src/twobrain_rec_server/db/migrations/versions/0100_billing_purchases.py"
    )
    spec = importlib.util.spec_from_file_location("purchase_seed", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    def apply(connection):
        with Operations.context(MigrationContext.configure(connection)):
            module._seed_catalog()

    async def run():
        async with client.app_state["engine"].begin() as connection:
            await connection.run_sync(apply)
        async with client.app_state["sessionmaker"]() as db:
            now = datetime.now(UTC)
            db.add(
                BillingAcceptanceBudget(
                    workspace_id=workspace,
                    limit_minor=20000,
                    enabled=True,
                    expires_at=now + timedelta(days=1),
                )
            )
            for code, purpose in [
                ("SYNTHFIRST", "initial_checkout"),
                ("SYNTHSTORE", "storage_upgrade"),
                ("SYNTHEARLY", "early_renewal"),
            ]:
                db.add(
                    PromotionCampaign(
                        code_hash=promo_code_hash(code),
                        campaign_version="synthetic-v1",
                        plan_code="personal",
                        cycle="month",
                        discount_percent=99,
                        max_redemptions=1,
                        enabled=True,
                        starts_at=now - timedelta(days=1),
                        ends_at=now + timedelta(days=1),
                        policy_snapshot={"purposes": [purpose], "workspace_id": str(workspace)},
                    )
                )
            await db.commit()

    asyncio.run(run())


@pytest.mark.parametrize(
    "cancel_during_dispatch,concurrent_storage", [(False, False), (True, False), (False, True)]
)
def test_initial_storage_early_renewal_and_scheduled_downgrade_are_one_coherent_journey(
    client, monkeypatch, tmp_path, cancel_during_dispatch, concurrent_storage
):
    from tests.unit import test_billing_money_path_e2e as fixtures

    monkeypatch.setattr(fixtures, "PAID_AT", datetime.now(UTC))
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)

    def provider_for_step():
        provider = _FakeYooKassa(saved_card=True)
        transport = httpx.MockTransport(provider.handle)

        def factory(settings):
            return YooKassaClient(settings, transport=transport)

        monkeypatch.setattr(routes, "YooKassaClient", factory)
        monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", factory)
        return provider

    async def observe():
        async with client.app_state["sessionmaker"]() as db:
            result = await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                db, client.app.state.settings
            )
            await db.commit()
            return result

    initial = provider_for_step()
    preview = client.post(
        "/billing/checkout/preview",
        headers=headers,
        data={"cycle": "month", "promo_code": "SYNTHFIRST"},
    )
    response = client.post(
        "/billing/checkout/start",
        headers=headers,
        follow_redirects=False,
        data={
            "quote_id": quote_id(preview),
            "cycle": "month",
            "idempotency_key": "journey-initial",
            "promo_code": "SYNTHFIRST",
            "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
            "offer_consent": "true",
            "recurring_consent": "true",
        },
    )
    assert response.status_code == 303
    assert len(initial.create_payloads) == 1
    assert initial.create_payloads[0]["amount"]["value"] == "10.00"
    assert asyncio.run(observe())["succeeded"] == 1

    storage = provider_for_step()
    preview = client.post(
        "/billing/storage/preview",
        headers=headers,
        data={"package_count": "1", "promo_code": "SYNTHSTORE"},
    )
    storage_quote = quote_id(preview)

    def confirm_storage(bound_id):
        return client.post(
            "/billing/purchases/confirm",
            headers=headers,
            follow_redirects=False,
            data={"quote_id": bound_id, "purchase_consent": "true"},
        )

    if concurrent_storage:
        second_quote = quote_id(
            client.post(
                "/billing/storage/preview",
                headers=headers,
                data={"package_count": "1", "promo_code": "SYNTHSTORE"},
            )
        )

        async def both_tabs():
            return await asyncio.wait_for(
                asyncio.gather(
                    asyncio.to_thread(confirm_storage, storage_quote),
                    asyncio.to_thread(confirm_storage, second_quote),
                ),
                timeout=15,
            )

        responses = asyncio.run(both_tabs())
        assert all(result.status_code in {303, 409} for result in responses)
        status_urls = [result.headers["location"] for result in responses if result.status_code == 303]
        assert status_urls

        async def dispatched_quote():
            async with client.app_state["sessionmaker"]() as db:
                operations = list(await db.scalars(select(BillingOperation).where(
                    BillingOperation.workspace_id == workspace,
                    BillingOperation.kind == "storage_upgrade",
                )))
                assert len(operations) == 1
                invoice = await db.scalar(select(BillingInvoice).where(
                    BillingInvoice.operation_id == operations[0].id,
                ))
                return operations[0].request_snapshot["quote_id"], {
                    f"https://yookassa.test/checkout/{storage.payment_id}",
                    f"/billing/checkout/status/{invoice.safe_number}",
                }

        storage_quote, same_payment_urls = asyncio.run(dispatched_quote())
        assert set(status_urls) <= same_payment_urls
        assert storage_quote in {quote_id(preview), second_quote}
    else:
        assert confirm_storage(storage_quote).status_code == 303
    assert len(storage.create_payloads) == 1
    assert storage.create_payloads[0].get("save_payment_method") is not True
    if concurrent_storage:
        from types import SimpleNamespace
        from uuid import uuid4

        from twobrain_rec_server.normalization import service as normalization

        real_grant = webhook_reconciliation.grant_confirmed_storage
        real_lock = normalization.lock_storage_workspace

        async def grant_and_admit_upload():
            grant_locked, upload_waiting = asyncio.Event(), asyncio.Event()

            async def synchronized_grant(*args, **kwargs):
                grant_locked.set()
                await asyncio.wait_for(upload_waiting.wait(), timeout=10)
                return await real_grant(*args, **kwargs)

            async def upload_lock(db, workspace_id):
                upload_waiting.set()
                await real_lock(db, workspace_id)

            async def archive_enabled(*args, **kwargs):
                return True

            async def upload():
                await grant_locked.wait()
                async with client.app_state["sessionmaker"]() as db:
                    reservation = await normalization._reserve_playback_storage(
                        db,
                        job=SimpleNamespace(
                            workspace_id=workspace, meeting_id=uuid4(), media_revision_id=uuid4()
                        ),
                        attempt=SimpleNamespace(id=uuid4()),
                        declared_bytes=3_000_000_000,
                        now=datetime.now(UTC),
                    )
                    await db.commit()
                    assert (
                        reservation.declared_bytes == 3_000_000_000
                        and reservation.state == "active"
                    )

            with monkeypatch.context() as scoped:
                scoped.setattr(
                    webhook_reconciliation, "grant_confirmed_storage", synchronized_grant
                )
                scoped.setattr(normalization, "lock_storage_workspace", upload_lock)
                scoped.setattr(normalization, "archive_audio_for_revision", archive_enabled)
                observed, _ = await asyncio.wait_for(
                    asyncio.gather(observe(), upload()), timeout=15
                )
                assert observed["succeeded"] == 1

        asyncio.run(grant_and_admit_upload())
    else:
        assert asyncio.run(observe())["succeeded"] == 1
    # Back/refresh/double click of the confirmation is observation only.
    repeated = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        follow_redirects=False,
        data={"quote_id": storage_quote, "purchase_consent": "true"},
    )
    assert repeated.status_code == 303 and len(storage.create_payloads) == 1

    async def state():
        async with client.app_state["sessionmaker"]() as db:
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            budget = await db.scalar(
                select(BillingAcceptanceBudget).where(
                    BillingAcceptanceBudget.workspace_id == workspace
                )
            )
            return sub, budget

    before, storage_budget = asyncio.run(state())
    assert before.capacity_bytes == 10_000_000_000
    if concurrent_storage:
        # The dedicated race variant ends after admission; the other variants
        # exercise renewal separately without exceeding the real rate limit.
        assert storage_budget.reserved_minor == 0 and 1000 < storage_budget.spent_minor <= 1290
        return
    cancel = client.post(
        "/billing/subscription/cancel",
        headers=headers,
        follow_redirects=False,
        data={"expected_authority_version": before.recurring_authority_version},
    )
    assert cancel.status_code == 303
    resume_page = client.get("/billing/subscription", headers=headers)
    resume_quote = re.search(r'name="resume_quote_id" value="([^"]+)"', resume_page.text)
    assert resume_quote
    denied_resume = client.post(
        "/billing/subscription/resume",
        headers=headers,
        follow_redirects=False,
        data={
            "expected_authority_version": before.recurring_authority_version + 1,
            "resume_consent": "true",
        },
    )
    assert denied_resume.headers["location"].endswith("result=conflict")
    assert asyncio.run(state())[0].recurring_allowed is False
    enabled = client.post(
        "/billing/subscription/resume",
        headers=headers,
        follow_redirects=False,
        data={
            "expected_authority_version": before.recurring_authority_version + 1,
            "resume_consent": "true",
            "resume_quote_id": resume_quote.group(1),
        },
    )
    assert enabled.headers["location"].endswith("result=resumed")
    enabled_sub = asyncio.run(state())[0]
    assert enabled_sub.recurring_allowed is True
    assert len(storage.create_payloads) == 1  # Consent alone never sends money.
    disabled = client.post(
        "/billing/subscription/cancel",
        headers=headers,
        follow_redirects=False,
        data={"expected_authority_version": enabled_sub.recurring_authority_version},
    )
    assert disabled.headers["location"].endswith("result=cancelled")
    stale_resume = client.post(
        "/billing/subscription/resume",
        headers=headers,
        follow_redirects=False,
        data={
            "expected_authority_version": enabled_sub.recurring_authority_version + 1,
            "resume_consent": "true",
            "resume_quote_id": resume_quote.group(1),
        },
    )
    assert stale_resume.headers["location"].endswith("result=conflict")
    assert asyncio.run(state())[0].recurring_allowed is False
    early = provider_for_step()
    if cancel_during_dispatch:
        page = client.get("/billing/subscription", headers=headers)
        fresh_quote = re.search(r'name="resume_quote_id" value="([^"]+)"', page.text).group(1)
        off_sub = asyncio.run(state())[0]
        enabled = client.post(
            "/billing/subscription/resume",
            headers=headers,
            follow_redirects=False,
            data={
                "expected_authority_version": off_sub.recurring_authority_version,
                "resume_consent": "true",
                "resume_quote_id": fresh_quote,
            },
        )
        assert enabled.headers["location"].endswith("result=resumed")
        on_sub = asyncio.run(state())[0]

        async def bank_with_concurrent_cancellation(request):
            result = early.handle(request)
            if request.method == "POST":
                cancel_response = await asyncio.wait_for(
                    asyncio.to_thread(
                        client.post,
                        "/billing/subscription/cancel",
                        headers=headers,
                        follow_redirects=False,
                        data={"expected_authority_version": on_sub.recurring_authority_version},
                    ),
                    timeout=10,
                )
                assert cancel_response.headers["location"].endswith("result=cancelled")
            return result

        def factory(settings):
            return YooKassaClient(
                settings, transport=httpx.MockTransport(bank_with_concurrent_cancellation)
            )

        monkeypatch.setattr(routes, "YooKassaClient", factory)
        monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", factory)
    preview = client.post(
        "/billing/subscription/early-preview", headers=headers, data={"promo_code": "SYNTHEARLY"}
    )
    assert "1 250 ₽" in preview.text
    assert ("Включено" if cancel_during_dispatch else "Отключено") in preview.text
    response = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        follow_redirects=False,
        data={"quote_id": quote_id(preview), "purchase_consent": "true"},
    )
    assert response.status_code == 303 and len(early.create_payloads) == 1
    assert early.create_payloads[0]["amount"]["value"] == "12.50"
    assert "payment_method_id" in early.create_payloads[0]
    assert asyncio.run(observe())["succeeded"] == 1
    after, budget = asyncio.run(state())
    assert after.paid_through > before.paid_through
    assert after.capacity_bytes == 10_000_000_000 and after.recurring_allowed is False
    assert budget.reserved_minor == 0 and 2290 < budget.spent_minor <= 2580

    preview = client.post(
        "/billing/storage/preview", headers=headers, data={"package_count": "0"}
    )
    response = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        follow_redirects=False,
        data={"quote_id": quote_id(preview), "purchase_consent": "true"},
    )
    assert response.status_code == 303
    scheduled, _ = asyncio.run(state())
    assert scheduled.next_capacity_bytes == 5_000_000_000
    assert scheduled.capacity_bytes == 10_000_000_000
    stale_cancel = client.post(
        "/billing/storage/cancel-selection",
        headers=headers,
        follow_redirects=False,
        data={"selection_version": scheduled.next_capacity_version - 1},
    )
    assert stale_cancel.status_code == 409
    cancel_selection = client.post(
        "/billing/storage/cancel-selection",
        headers=headers,
        follow_redirects=False,
        data={"selection_version": scheduled.next_capacity_version},
    )
    assert cancel_selection.status_code == 303
    assert asyncio.run(state())[0].next_capacity_bytes is None
    assert asyncio.run(state())[0].capacity_bytes == 10_000_000_000
    assert len(early.create_payloads) == 1

    async def counts():
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.scalar(
                    select(func.count(BillingInvoice.id)).where(
                        BillingInvoice.workspace_id == workspace
                    )
                ),
                await db.scalar(
                    select(func.count(BillingStorageEntitlementGrant.id)).where(
                        BillingStorageEntitlementGrant.workspace_id == workspace
                    )
                ),
            )

    assert asyncio.run(counts()) == (3, 2)

    async def finalized():
        async with client.app_state["sessionmaker"]() as db:
            redemptions = list(
                await db.scalars(
                    select(PromotionRedemption.state).where(
                        PromotionRedemption.workspace_id == workspace
                    )
                )
            )
            notices = list(
                await db.scalars(
                    select(BillingNotificationDelivery.event_id).where(
                        BillingNotificationDelivery.workspace_id == workspace,
                        BillingNotificationDelivery.template_key == "payment_succeeded",
                    )
                )
            )
            return redemptions, notices

    redeemed, notices = asyncio.run(finalized())
    assert redeemed == ["redeemed"] * 3
    assert len(notices) == len(set(notices)) == 3

    async def control_notices():
        async with client.app_state["sessionmaker"]() as db:
            return list(
                await db.scalars(
                    select(BillingNotificationDelivery.template_key).where(
                        BillingNotificationDelivery.workspace_id == workspace,
                        BillingNotificationDelivery.template_key.in_(
                            [
                                "autorenewal_disabled",
                                "autorenewal_enabled",
                                "storage_selection_changed",
                            ]
                        ),
                    )
                )
            )

    notifications = asyncio.run(control_notices())
    assert notifications.count("autorenewal_disabled") == (3 if cancel_during_dispatch else 2)
    assert notifications.count("autorenewal_enabled") == (2 if cancel_during_dispatch else 1)
    assert notifications.count("storage_selection_changed") == 2


@pytest.mark.parametrize("recovery_path", ["webhook", "list"])
def test_unknown_initial_payment_cannot_be_sent_again_and_keeps_budget(
    client, monkeypatch, tmp_path, recovery_path
):
    from twobrain_rec_server.db.models import BillingOperation

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    calls = []
    provider = _FakeYooKassa(saved_card=True)

    def lost_response(request):
        calls.append(request.method)
        if request.method == "GET" and request.url.path == "/v3/payments":
            get_request = httpx.Request(
                "GET", f"https://api.yookassa.test/v3/payments/{provider.payment_id}"
            )
            return httpx.Response(
                200, json={"type": "list", "items": [provider.handle(get_request).json()]}
            )
        result = provider.handle(request)
        if request.method == "GET":
            return result
        raise httpx.ReadTimeout("synthetic response lost", request=request)

    def factory(settings):
        return YooKassaClient(settings, transport=httpx.MockTransport(lost_response))

    monkeypatch.setattr(routes, "YooKassaClient", factory)
    preview = client.post(
        "/billing/checkout/preview",
        headers=headers,
        data={"cycle": "month", "promo_code": "SYNTHFIRST"},
    )
    data = {
        "quote_id": quote_id(preview),
        "cycle": "month",
        "idempotency_key": "synthetic-lost-response",
        "promo_code": "SYNTHFIRST",
        "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
        "offer_consent": "true",
        "recurring_consent": "true",
    }
    first = client.post(
        "/billing/checkout/start", headers=headers, data=data, follow_redirects=False
    )
    assert first.status_code == 303 and calls == ["POST"]
    second = client.post(
        "/billing/checkout/start", headers=headers, data=data, follow_redirects=False
    )
    assert second.status_code == 303 and calls == ["POST"]

    async def state():
        async with client.app_state["sessionmaker"]() as db:
            op = await db.scalar(
                select(BillingOperation).where(BillingOperation.workspace_id == workspace)
            )
            invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == op.id)
            )
            budget = await db.scalar(
                select(BillingAcceptanceBudget).where(
                    BillingAcceptanceBudget.workspace_id == workspace
                )
            )
            return op, invoice, budget

    operation, invoice, budget = asyncio.run(state())
    assert operation.state == "manual_resolution"
    assert budget.reserved_minor == 1000 and budget.spent_minor == 0
    result = client.post(
        f"/billing/checkout/status/{invoice.safe_number}/continue",
        headers=headers,
        follow_redirects=False,
    )
    assert result.status_code == 303 and calls == ["POST"]
    assert asyncio.run(state())[2].reserved_minor == 1000

    # Simulate a fresh reconciliation session after a process restart. The
    # accepted callback supplies a candidate id, GET still proves the money.
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", factory)
    if recovery_path == "webhook":
        assert (
            _deliver_webhook(
                client,
                _payment_webhook(
                    workspace_id=workspace,
                    operation_id=operation.id,
                    payment_id=provider.payment_id,
                    value="10.00",
                ),
            ).status_code
            == 200
        )

    async def recover():
        async with client.app_state["sessionmaker"]() as db:
            result = (
                await webhook_reconciliation.reconcile_pending_webhook_events(
                    db, client.app.state.settings
                )
                if recovery_path == "webhook"
                else await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                    db, client.app.state.settings, operation_id=operation.id
                )
            )
            await db.commit()
            return result

    asyncio.run(recover())
    completed, paid_invoice, paid_budget = asyncio.run(state())
    assert completed.state == paid_invoice.status == "succeeded"
    assert paid_budget.spent_minor == 1000 and paid_budget.reserved_minor == 0
    assert calls.count("POST") == 1 and calls.count("GET") >= 1


def test_expired_quote_and_changed_catalog_never_reach_provider(client, monkeypatch, tmp_path):
    from twobrain_rec_server.db.models import BillingPlanVersion

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    calls = []

    def forbidden(_settings):
        calls.append(True)
        raise AssertionError("stale quote must fail before provider construction")

    monkeypatch.setattr(routes, "YooKassaClient", forbidden)
    for change in ("expired", "catalog"):

        class PreviewClock(datetime):
            @classmethod
            def now(cls, tz=None):
                return datetime.now(tz) - timedelta(minutes=20)

        with monkeypatch.context() as clock_patch:
            if change == "expired":
                clock_patch.setattr(routes, "datetime", PreviewClock)
            bound_id = quote_id(client.get("/billing/checkout"))

        async def mutate():
            async with client.app_state["sessionmaker"]() as db:
                row = await db.scalar(
                    select(BillingPlanVersion).where(BillingPlanVersion.cycle == "month")
                )
                row.enabled_for_checkout = False
                await db.commit()

        if change == "catalog":
            asyncio.run(mutate())
        result = client.post(
            "/billing/checkout/start",
            headers=headers,
            follow_redirects=False,
            data={
                "quote_id": bound_id,
                "cycle": "month",
                "idempotency_key": f"invalid-{change}",
                "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
                "offer_consent": "true",
                "recurring_consent": "true",
            },
        )
        assert result.status_code in {303, 409} and not calls

    async def invoice_count():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(func.count(BillingInvoice.id)).where(
                    BillingInvoice.workspace_id == workspace
                )
            )

    assert asyncio.run(invoice_count()) == 0


@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade", "early_renewal", "renewal"])
@pytest.mark.parametrize("mode", ["background", "boundary", "late_manual", "manual_pending", "manual_get_failure", "wrong_scope", "wrong_amount", "wrong_test", "wrong_metadata", "get_failure", "owner_missing"])
def test_completed_purchase_recovers_late_receipt_without_replaying_money(
    client, monkeypatch, tmp_path, kind, mode, operation_state="succeeded"
):
    """Real DB and owner routes; receipt-only GET never replays financial projection."""
    from uuid import uuid4

    from tests.conftest import USER_ID
    from twobrain_rec_server.db.models import BillingEntitlementGrant

    _configure_billing(client, tmp_path)
    workspace, headers = _prepare_owner_session(client)
    now = datetime.now(UTC)
    manual = mode in {"late_manual", "manual_pending", "manual_get_failure", "owner_changed_late"}
    class ReceiptClock(datetime):
        @classmethod
        def now(cls, tz=None):
            return now.astimezone(tz)

    monkeypatch.setattr(webhook_reconciliation, "datetime", ReceiptClock)
    op_id, inv_id = uuid4(), uuid4()
    number = f"INV-RECEIPT-{uuid4().hex}"
    snapshot = {"cycle": "year", "receipt_registration": "pending"}
    refused = operation_state == "succeeded_refused"
    owner_changed = mode == "owner_changed_late"
    resolution = "workspace_scope_invalid"
    if owner_changed:
        snapshot.update({"payment_method_label": "•••• 4321",
                         "receipt_url": "https://yookassa.ru/private-demo"})
    if refused:
        snapshot["service_resolution"] = resolution
    operation_snapshot = {"purchase_schema": 2, "provider_environment": "test",
                          "provider_shop_id": "shop-money-path"} if operation_state != "succeeded_projected" else {}
    if refused:
        operation_snapshot["reconciliation_detail"] = {"code": resolution}

    async def service_gap_history(db):
        records = []
        for model, predicate in (
            (BillingAuditEvent, BillingAuditEvent.target_ref == number),
            (BillingNotificationDelivery,
             BillingNotificationDelivery.event_id == f"payment:{inv_id}:service_gap"),
        ):
            rows = list(await db.scalars(select(model).where(predicate).order_by(model.id)))
            assert len(rows) == 1
            records.append([{column.key: getattr(row, column.key) for column in model.__table__.columns}
                            for row in rows])
        return records

    produced_history = None
    async def seed():
        nonlocal operation_snapshot, snapshot, produced_history
        async with client.app_state["sessionmaker"]() as db:
            db.add(BillingOperation(
                id=op_id, workspace_id=workspace, kind=kind, state=operation_state,
                idempotency_key=f"receipt-{op_id}", provider_id="pay-synthetic-receipt",
                created_at=now - timedelta(hours=25 if manual else 24 if mode == "boundary" else 1),
                request_snapshot=operation_snapshot,
            ))
            await db.flush()
            db.add(BillingInvoice(id=inv_id, operation_id=op_id, workspace_id=workspace,
                                  safe_number=number, amount_minor=12500, currency="RUB",
                                  status="succeeded", plan_snapshot=snapshot,
                                  receipt_contact_snapshot="prior-payer@prior-payer.example" if owner_changed else None))
            subscription = await db.get(WorkspaceSubscription, workspace)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace)
                db.add(subscription)
            subscription.billing_owner_id = USER_ID
            if owner_changed:
                from twobrain_rec_server.db.models import UserIdentity, Workspace
                previous = uuid4()
                space = await db.get(Workspace, workspace)
                db.add(UserIdentity(id=previous, organization_id=space.organization_id,
                                    external_subject=f"synthetic-{previous}"))
                await db.flush()
                subscription.billing_owner_id = previous
            subscription.plan_code, subscription.cycle = "personal", "year"
            subscription.capacity_bytes, subscription.recurring_allowed = 10_000_000_000, False
            if refused:
                subscription.renewal_resolution = resolution
            subscription.paid_through = now + timedelta(days=365)
            db.add(BillingAcceptanceBudget(workspace_id=workspace, limit_minor=20000,
                                          spent_minor=12500, reserved_minor=0,
                                          enabled=False, expires_at=now - timedelta(hours=1)))
            await db.flush()
            if not refused:
                db.add(BillingEntitlementGrant(workspace_id=workspace, invoice_id=inv_id,
                       provider_payment_id="pay-synthetic-receipt", plan_code="personal",
                       cycle="year", starts_at=now, ends_at=now + timedelta(days=365),
                       amount_minor=12500, currency="RUB"))
            if owner_changed:
                from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal
                operation = await db.get(BillingOperation, op_id)
                invoice = await db.get(BillingInvoice, inv_id)
                operation.state, invoice.status = "unknown", "pending"
                operation.request_snapshot = {**operation_snapshot, "cycle": "year", "plan_code": "personal"}
                invoice.plan_snapshot = {key: value for key, value in snapshot.items()
                                         if key != "service_resolution"}
                assert await grant_confirmed_renewal(db, workspace_id=workspace,
                    provider_payment_id=operation.provider_id, amount_minor=12500,
                    currency="RUB", grant_starts_at=now) == "refused"
                assert operation.state == "succeeded_refused"
                assert invoice.plan_snapshot["service_resolution"] == "workspace_scope_invalid"
                operation_snapshot, snapshot = dict(operation.request_snapshot), dict(invoice.plan_snapshot)
                produced_history = await service_gap_history(db)
            await db.commit()

    asyncio.run(seed())
    calls = []
    receipt_status = "pending"

    def handle(request):
        calls.append(request.method)
        assert request.method == "GET"
        assert request.url.path == "/v3/payments/pay-synthetic-receipt"
        if mode in {"get_failure", "manual_get_failure"}:
            raise httpx.ConnectError("synthetic outage", request=request)
        return httpx.Response(200, json={
            "id": "pay-synthetic-receipt", "status": "succeeded", "test": mode != "wrong_test",
            "created_at": now.isoformat(), "paid": True,
            "recipient": {"account_id": "wrong" if mode == "wrong_scope" else "shop-money-path"},
            "amount": {"value": "250.00" if mode == "wrong_amount" else "125.00", "currency": "RUB"},
            "metadata": {"workspace_id": str(workspace), "operation_id": str(uuid4()) if mode == "wrong_metadata" else str(op_id),
                         "invoice_number": number},
            "receipt_registration": receipt_status,
        })

    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient",
                        lambda settings: YooKassaClient(settings, transport=httpx.MockTransport(handle)))
    client.app.state.settings.billing_checkout_enabled = False
    client.app.state.settings.billing_provider_observation_enabled = True

    async def observe():
        async with client.app_state["sessionmaker"]() as db:
            result = await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                db, client.app.state.settings, commit_each_operation=True
            )
            await db.commit()
            return result

    detail = client.get(f"/billing/invoices/{number}")
    assert detail.status_code == 200 and "Проверить чек" in detail.text
    if owner_changed:
        for value in ("4321", "prior-payer.example", "private-demo"):
            assert value not in detail.text
        path = f"/billing/checkout/status/{number}/refresh?return_to=invoice"
        assert client.post(path, follow_redirects=False).status_code == 403
        for denied_path in (f"/billing/checkout/status/{number}/refresh",
                            "/billing/checkout/status/INV-FOREIGN/refresh?return_to=invoice"):
            denied = client.post(denied_path, headers=headers, follow_redirects=False)
            assert denied.status_code == 303 and denied.headers["location"] == "/billing?result=owner_only"
        from twobrain_rec_server.db.models import WorkspaceMembership
        async def change_access(*, role="owner", state="succeeded_refused"):
            async with client.app_state["sessionmaker"]() as db:
                membership = await db.scalar(select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace,
                    WorkspaceMembership.user_id == USER_ID))
                membership.role = role
                operation = await db.get(BillingOperation, op_id)
                operation.state = state
                await db.commit()
        asyncio.run(change_access(state="unknown"))
        denied = client.post(path, headers=headers, follow_redirects=False)
        assert denied.status_code == 303 and denied.headers["location"] == "/billing?result=owner_only"
        async def no_financial_fallback():
            async with client.app_state["sessionmaker"]() as db:
                counters = await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                    db, client.app.state.settings, operation_id=op_id, receipt_only=True)
                assert counters["processed"] == 0
                await db.rollback()
        asyncio.run(no_financial_fallback())
        assert calls == []
        asyncio.run(change_access())
        async def actor_mismatch_is_not_receipt_only():
            from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal
            async with client.app_state["sessionmaker"]() as db:
                operation = await db.get(BillingOperation, op_id)
                subscription = await db.get(WorkspaceSubscription, workspace)
                subscription.billing_owner_id = USER_ID
                operation.state = "unknown"
                operation.request_snapshot = {**operation_snapshot, "billing_actor_user_id": str(uuid4())}
                assert await grant_confirmed_renewal(db, workspace_id=workspace,
                    provider_payment_id=operation.provider_id, amount_minor=12500,
                    currency="RUB", grant_starts_at=now) == "owner_changed"
                invoice = await db.get(BillingInvoice, inv_id)
                assert operation.state == "reconciliation_gap"
                assert invoice.plan_snapshot["service_resolution"] == "owner_changed"
                assert not await routes._is_paid_refused_receipt(db, invoice)
                counters = await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                    db, client.app.state.settings, operation_id=op_id, receipt_only=True)
                assert counters["processed"] == 0
                await db.rollback()
        asyncio.run(actor_mismatch_is_not_receipt_only())
        assert calls == []
    if mode == "owner_missing":
        from twobrain_rec_server.db.models import WorkspaceMembership
        async def revoke_owner():
            async with client.app_state["sessionmaker"]() as db:
                membership = await db.scalar(select(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace,
                    WorkspaceMembership.user_id == USER_ID,
                ))
                membership.status = "revoked"
                await db.commit()
        asyncio.run(revoke_owner())
    result = asyncio.run(observe())
    if mode == "owner_missing":
        assert result["failed"] == 1 and calls == []
    elif manual:
        assert result["processed"] == 0 and calls == []
    else:
        assert result["processed"] == 1 and calls == ["GET"]
    receipt_status = "pending" if mode == "manual_pending" else "succeeded"
    if manual:
        response = client.post(f"/billing/checkout/status/{number}/refresh?return_to=invoice", headers=headers,
                               follow_redirects=False)
        assert response.status_code == 303
        assert response.headers["location"].startswith(f"/billing/invoices/{number}?")
        returned = client.get(response.headers["location"])
        assert returned.status_code == 200 and "Платеж и чек" in returned.text
        if mode == "manual_get_failure":
            assert "Не удалось проверить чек" in returned.text and "Оплачен" in returned.text
        elif mode == "manual_pending":
            assert "Чек формируется" in returned.text and "Оплачен" in returned.text
        else:
            assert "Чек зарегистрирован" in returned.text
    else:
        asyncio.run(observe())
    succeeded = mode in {"background", "boundary", "late_manual", "owner_changed_late"}
    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            invoice, operation = await db.get(BillingInvoice, inv_id), await db.get(BillingOperation, op_id)
            assert operation.state == operation_state and invoice.status == "succeeded"
            assert operation.request_snapshot == operation_snapshot
            assert invoice.amount_minor == 12500
            assert invoice.plan_snapshot == {**snapshot, "receipt_registration": "succeeded" if succeeded else "pending"}
            subscription = await db.get(WorkspaceSubscription, workspace)
            assert not subscription.recurring_allowed and subscription.paid_through == now + timedelta(days=365)
            assert subscription.capacity_bytes == 10_000_000_000
            if refused:
                assert subscription.renewal_resolution == resolution
            if owner_changed:
                assert await service_gap_history(db) == produced_history
            budget = await db.scalar(select(BillingAcceptanceBudget).where(BillingAcceptanceBudget.workspace_id == workspace))
            assert (budget.spent_minor, budget.reserved_minor, budget.enabled) == (12500, 0, False)
            assert await db.scalar(select(func.count()).select_from(BillingEntitlementGrant)) == (0 if refused else 1)
            assert await db.scalar(select(func.count()).select_from(BillingStorageEntitlementGrant)) == 0
            assert await db.scalar(select(func.count()).select_from(BillingNotificationDelivery)) == (1 if succeeded else 0) + (1 if owner_changed else 0)
    asyncio.run(verify())
    before = len(calls)
    asyncio.run(observe())
    if succeeded:
        assert len(calls) == before  # Registered receipts leave the bounded candidate set.
        final_detail = client.get(f"/billing/invoices/{number}").text
        assert "Чек зарегистрирован" in final_detail
        assert "Проверить чек" not in final_detail
        if owner_changed:
            for value in ("4321", "prior-payer.example", "private-demo"):
                assert value not in final_detail
    asyncio.run(verify())

    if owner_changed:
        before = len(calls)
        asyncio.run(change_access(role="member"))
        denied = client.post(path, headers=headers, follow_redirects=False)
        assert denied.status_code == 403 and len(calls) == before
        asyncio.run(verify())


def test_projected_storage_purchase_recovers_receipt_without_replaying_projection(
    client, monkeypatch, tmp_path
):
    test_completed_purchase_recovers_late_receipt_without_replaying_money(
        client, monkeypatch, tmp_path, "storage_upgrade", "background",
        operation_state="succeeded_projected",
    )


@pytest.mark.parametrize("mode", ["background", "late_manual", "owner_missing", "owner_changed_late"])
def test_paid_refused_renewal_recovers_receipt_without_granting_access(
    client, monkeypatch, tmp_path, mode
):
    test_completed_purchase_recovers_late_receipt_without_replaying_money(
        client, monkeypatch, tmp_path, "renewal", mode,
        operation_state="succeeded_refused",
    )


def test_pending_payment_precedes_older_receipt_when_batch_has_one_slot(
    client, monkeypatch, tmp_path
):
    from uuid import uuid4

    _configure_billing(client, tmp_path)
    workspace, _ = _prepare_owner_session(client)
    now = datetime.now(UTC)
    pending_id = uuid4()
    pending_number = "INV-SYNTHETIC-PENDING"

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            for receipt_only in (True, False):
                op_id = uuid4() if receipt_only else pending_id
                db.add(BillingOperation(
                    id=op_id, workspace_id=workspace, kind="initial_checkout",
                    state="succeeded" if receipt_only else "provider_pending",
                    idempotency_key=f"priority-{op_id}",
                    provider_id="pay-old-receipt" if receipt_only else "pay-new-pending",
                    created_at=now - timedelta(hours=2 if receipt_only else 1),
                    updated_at=now - timedelta(hours=2 if receipt_only else 1),
                    request_snapshot={"purchase_schema": 2, "provider_environment": "test",
                                      "provider_shop_id": "shop-money-path"},
                ))
                await db.flush()
                db.add(BillingInvoice(
                    workspace_id=workspace, operation_id=op_id,
                    safe_number="INV-SYNTHETIC-OLD" if receipt_only else pending_number,
                    amount_minor=1000, currency="RUB",
                    status="succeeded" if receipt_only else "pending",
                    plan_snapshot={"receipt_registration": "pending"},
                ))
            await db.commit()
    asyncio.run(seed())
    calls = []
    def handle(request):
        calls.append(request.method)
        assert request.method == "GET" and request.url.path == "/v3/payments/pay-new-pending"
        return httpx.Response(200, json={
            "id": "pay-new-pending", "status": "pending", "test": True,
            "created_at": now.isoformat(), "recipient": {"account_id": "shop-money-path"},
            "amount": {"value": "10.00", "currency": "RUB"},
            "metadata": {"workspace_id": str(workspace), "operation_id": str(pending_id),
                         "invoice_number": pending_number},
        })
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient",
                        lambda settings: YooKassaClient(settings, transport=httpx.MockTransport(handle)))
    async def observe():
        async with client.app_state["sessionmaker"]() as db:
            result = await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                db, client.app.state.settings, limit=1, commit_each_operation=True
            )
            await db.commit()
            return result
    assert asyncio.run(observe()) == {
        "processed": 1, "succeeded": 0, "canceled": 0, "pending": 1, "failed": 0
    }
    assert calls == ["GET"]


@pytest.mark.parametrize("first_result", ["pending", "get_failure", "wrong_scope", "ownerless"])
def test_pending_receipts_rotate_with_one_batch_slot(client, monkeypatch, tmp_path, first_result):
    from uuid import uuid4

    _configure_billing(client, tmp_path)
    workspace, _ = _prepare_owner_session(client)
    now = datetime.now(UTC)
    identities = [(uuid4(), f"INV-ROTATE-{index}", f"pay-rotate-{index}") for index in range(2)]

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            ownerless = workspace
            if first_result == "ownerless":
                from twobrain_rec_server.db.models import Workspace
                space = await db.get(Workspace, workspace)
                ownerless = uuid4()
                db.add(Workspace(id=ownerless, organization_id=space.organization_id,
                                 slug=f"receipt-{ownerless}", name="Synthetic ownerless receipt",
                                 kind="personal", owner_user_id=None))
                await db.flush()
            for index, (operation_id, number, payment_id) in enumerate(identities):
                operation_workspace = ownerless if index == 0 else workspace
                db.add(BillingOperation(id=operation_id, workspace_id=operation_workspace,
                    kind="initial_checkout", state="succeeded", provider_id=payment_id,
                    idempotency_key=str(operation_id), created_at=now - timedelta(hours=2),
                    updated_at=now - timedelta(minutes=2 - index),
                    request_snapshot={"purchase_schema": 2, "provider_environment": "test",
                                      "provider_shop_id": "shop-money-path"}))
                await db.flush()
                db.add(BillingInvoice(workspace_id=operation_workspace, operation_id=operation_id,
                    safe_number=number, amount_minor=1000, currency="RUB", status="succeeded",
                    plan_snapshot={"receipt_registration": "pending"}))
            await db.commit()
    asyncio.run(seed())
    calls = []

    def handle(request):
        assert request.method == "GET"
        payment_id = request.url.path.rsplit("/", 1)[-1]
        calls.append(payment_id)
        operation_id, number, _ = next(item for item in identities if item[2] == payment_id)
        first = payment_id == identities[0][2]
        if first and first_result == "get_failure":
            raise httpx.ConnectError("synthetic outage", request=request)
        return httpx.Response(200, json={"id": payment_id, "status": "succeeded", "paid": True,
            "test": True, "created_at": now.isoformat(), "receipt_registration": "pending",
            "recipient": {"account_id": "wrong" if first and first_result == "wrong_scope" else "shop-money-path"},
            "amount": {"value": "10.00", "currency": "RUB"},
            "metadata": {"workspace_id": str(workspace), "operation_id": str(operation_id),
                         "invoice_number": number}})
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient",
        lambda settings: YooKassaClient(settings, transport=httpx.MockTransport(handle)))

    async def observe():
        async with client.app_state["sessionmaker"]() as db:
            await webhook_reconciliation.reconcile_pending_initial_checkout_operations(
                db, client.app.state.settings, limit=1, commit_each_operation=True)
            await db.commit()
    async def financial_snapshot():
        async with client.app_state["sessionmaker"]() as db:
            result = []
            for model in (BillingOperation, BillingInvoice, WorkspaceSubscription,
                          BillingAcceptanceBudget, BillingEntitlementGrant,
                          BillingStorageEntitlementGrant, BillingAuditEvent,
                          BillingNotificationDelivery):
                rows = list(await db.scalars(select(model).order_by(*model.__table__.primary_key.columns)))
                result.append([{column.key: getattr(row, column.key)
                                for column in model.__table__.columns
                                if not (model is BillingOperation and column.key == "updated_at")}
                               for row in rows])
            return result
    from twobrain_rec_server.db.models import BillingEntitlementGrant
    before = asyncio.run(financial_snapshot())
    asyncio.run(observe())
    assert asyncio.run(financial_snapshot()) == before
    asyncio.run(observe())
    assert asyncio.run(financial_snapshot()) == before
    assert calls == [item[2] for item in (identities[1:] if first_result == "ownerless" else identities)]


def test_invoice_hides_receipt_refresh_for_nonrecoverable_operation(client, monkeypatch, tmp_path):
    from uuid import uuid4

    from tests.conftest import USER_ID
    from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal

    _configure_billing(client, tmp_path)
    workspace, headers = _prepare_owner_session(client)
    op_id, inv_id = uuid4(), uuid4()
    number, now = f"INV-ACTOR-{uuid4().hex}", datetime.now(UTC)
    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.get(WorkspaceSubscription, workspace)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace)
                db.add(subscription)
            subscription.billing_owner_id = USER_ID
            subscription.plan_code, subscription.cycle = "personal", "year"
            subscription.recurring_allowed = False
            db.add(BillingOperation(id=op_id, workspace_id=workspace, kind="renewal",
                state="unknown", provider_id="pay-actor-receipt", idempotency_key=str(op_id),
                request_snapshot={"purchase_schema": 2, "cycle": "year", "plan_code": "personal",
                                  "billing_actor_user_id": str(uuid4())}))
            await db.flush()
            db.add(BillingInvoice(id=inv_id, workspace_id=workspace, operation_id=op_id,
                safe_number=number, amount_minor=12500, currency="RUB", status="pending",
                plan_snapshot={"receipt_registration": "pending"}))
            await db.flush()
            assert await grant_confirmed_renewal(db, workspace_id=workspace,
                provider_payment_id="pay-actor-receipt", amount_minor=12500,
                currency="RUB", grant_starts_at=now) == "owner_changed"
            assert (await db.get(BillingOperation, op_id)).state == "reconciliation_gap"
            await db.commit()
    asyncio.run(seed())
    calls = []
    def handle(request):
        calls.append(request.method)
        raise AssertionError("Excluded receipt must not call provider")
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient",
        lambda settings: YooKassaClient(settings, transport=httpx.MockTransport(handle)))
    page = client.get(f"/billing/invoices/{number}")
    assert page.status_code == 200 and "Чек формируется" in page.text
    assert "Проверить чек" not in page.text
    response = client.post(f"/billing/checkout/status/{number}/refresh?return_to=invoice",
                           headers=headers, follow_redirects=False)
    assert response.status_code == 303 and not calls
    async def operation_shape(state, kind, provider_id):
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.get(BillingOperation, op_id)
            operation.state, operation.kind, operation.provider_id = state, kind, provider_id
            await db.commit()
    for shape in (("sent", "renewal", "pay-actor-receipt"),
                  ("succeeded", "renewal", None),
                  ("succeeded", "unsupported", "pay-actor-receipt")):
        asyncio.run(operation_shape(*shape))
        page = client.get(f"/billing/invoices/{number}")
        assert page.status_code == 200 and "Чек формируется" in page.text
        assert "Проверить чек" not in page.text
    asyncio.run(operation_shape("reconciliation_gap", "renewal", "pay-actor-receipt"))
    assert not calls
    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            assert (await db.get(BillingOperation, op_id)).state == "reconciliation_gap"
            invoice = await db.get(BillingInvoice, inv_id)
            assert invoice.status == "succeeded" and invoice.plan_snapshot["receipt_registration"] == "pending"
            assert invoice.plan_snapshot["service_resolution"] == "owner_changed"
            assert not (await db.get(WorkspaceSubscription, workspace)).recurring_allowed
            assert await db.scalar(select(func.count()).select_from(BillingStorageEntitlementGrant)) == 0
    asyncio.run(verify())
