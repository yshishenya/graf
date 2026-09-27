"""Payment review edge cases exercised against PostgreSQL and HTTP."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.integration.test_billing_purchase_journey import seed_catalog_and_budget
from tests.unit.test_billing_money_path_e2e import (
    USER_ID,
    _approved_month_catalog,
    _configure_billing,
    _prepare_owner_session,
)
from twobrain_rec_server.billing.purchases import calculate_storage_purchase
from twobrain_rec_server.db.models import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    PromotionCampaign,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)


def seed_periods(client, workspace, *, bonus=False, mixed=False):
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace)
                db.add(subscription)
            subscription.plan_code = subscription.state = "personal"
            subscription.billing_owner_id = USER_ID
            subscription.cycle = "year" if mixed else "month"
            subscription.capacity_bytes = 5_000_000_000
            subscription.next_capacity_version = 0
            boundary = now + timedelta(days=15)
            next_start = boundary + timedelta(days=7 if bonus else 0)
            subscription.paid_through = next_start + timedelta(days=365 if mixed else 30)
            for cycle, start, end in [
                ("month", now - timedelta(days=15), boundary),
                (subscription.cycle, next_start, subscription.paid_through),
            ]:
                operation = BillingOperation(
                    workspace_id=workspace,
                    kind="renewal",
                    state="succeeded",
                    idempotency_key=str(uuid4()),
                    request_snapshot={},
                )
                db.add(operation)
                await db.flush()
                invoice = BillingInvoice(
                    workspace_id=workspace,
                    operation_id=operation.id,
                    safe_number=f"INV-{uuid4().hex}",
                    amount_minor=100000,
                    currency="RUB",
                    status="succeeded",
                    plan_snapshot={"purchase_schema": 2, "cycle": cycle},
                )
                db.add(invoice)
                await db.flush()
                db.add(
                    BillingEntitlementGrant(
                        workspace_id=workspace,
                        invoice_id=invoice.id,
                        provider_payment_id=str(uuid4()),
                        plan_code="personal",
                        cycle=cycle,
                        starts_at=start,
                        ends_at=end,
                        amount_minor=100000,
                        currency="RUB",
                    )
                )
            if bonus:
                db.add(
                    TimeCreditLedgerEntry(
                        workspace_id=workspace,
                        source_ref=str(uuid4()),
                        days=7,
                        state="applied",
                        maturity_at=now,
                        expires_at=now + timedelta(days=90),
                        applied_start=boundary,
                        applied_end=next_start,
                        capacity_snapshot_bytes=5_000_000_000,
                    )
                )
            await db.commit()

    asyncio.run(run())
    return now


def test_future_bonus_defers_whole_upgrade_without_charging_paid_segments(client, tmp_path):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, _ = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    now = seed_periods(client, workspace, bonus=True)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            quote = await calculate_storage_purchase(
                db, subscription=subscription, target_capacity_bytes=10_000_000_000, now=now
            )
            assert quote.deferred_to_renewal
            assert quote.payable_amount_minor == 0
            assert quote.segments == ()

    asyncio.run(run())


@pytest.mark.parametrize("campaign_cycle", ["year", None])
def test_storage_promo_applies_only_when_all_charged_periods_are_eligible(
    client, tmp_path, campaign_cycle
):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace, mixed=True)

    async def campaign():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(await db.scalars(select(PromotionCampaign)))
            row = next(r for r in rows if r.policy_snapshot["purposes"] == ["storage_upgrade"])
            row.cycle = campaign_cycle
            await db.commit()

    asyncio.run(campaign())
    response = client.post(
        "/billing/storage/preview",
        headers=headers,
        data={"package_count": "1", "promo_code": "SYNTHSTORE"},
    )
    assert response.status_code == (409 if campaign_cycle else 200)
    if campaign_cycle:
        assert "Промокод не подходит ко всем оплачиваемым периодам" in response.text, response.text[
            -4000:
        ]


def test_storage_invoice_explains_capacity_and_each_prorated_period(client, tmp_path):
    _configure_billing(client, tmp_path)
    workspace, headers = _prepare_owner_session(client)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            operation = BillingOperation(
                workspace_id=workspace,
                kind="storage_upgrade",
                state="succeeded",
                idempotency_key=str(uuid4()),
                request_snapshot={},
            )
            db.add(operation)
            await db.flush()
            db.add(
                BillingInvoice(
                    workspace_id=workspace,
                    operation_id=operation.id,
                    safe_number="INV-STORAGE-DETAIL",
                    amount_minor=40000,
                    currency="RUB",
                    status="succeeded",
                    plan_snapshot={
                        "purpose": "storage_upgrade",
                        "cycle": "month",
                        "target_capacity_bytes": 10_000_000_000,
                        "storage_segments": [
                            {
                                "starts_at": "2026-09-27T00:00:00+00:00",
                                "ends_at": "2026-10-12T00:00:00+00:00",
                                "capacity_bytes": 10_000_000_000,
                            },
                            {
                                "starts_at": "2026-10-12T00:00:00+00:00",
                                "ends_at": "2026-11-12T00:00:00+00:00",
                                "capacity_bytes": 10_000_000_000,
                            },
                        ],
                    },
                )
            )
            await db.commit()

    asyncio.run(seed())
    response = client.get("/billing/invoices/INV-STORAGE-DETAIL", headers=headers)
    assert response.status_code == 200
    assert "10 GB" in response.text
    assert "Оплаченные интервалы хранения" in response.text
    assert "27.09.2026" in response.text and "12.11.2026" in response.text


def test_campaign_cycle_change_after_preview_cannot_discount_ineligible_segments(client, tmp_path):
    from tests.integration.test_billing_purchase_journey import quote_id

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace, mixed=True)

    async def set_cycle(value):
        async with client.app_state["sessionmaker"]() as db:
            rows = list(await db.scalars(select(PromotionCampaign)))
            row = next(r for r in rows if r.policy_snapshot["purposes"] == ["storage_upgrade"])
            row.cycle = value
            await db.commit()

    asyncio.run(set_cycle(None))
    preview = client.post(
        "/billing/storage/preview",
        headers=headers,
        data={"package_count": "1", "promo_code": "SYNTHSTORE"},
    )
    bound = quote_id(preview)
    asyncio.run(set_cycle("year"))
    response = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        data={"quote_id": bound, "purchase_consent": "true"},
    )
    assert response.status_code == 409
    assert "Промокод не подходит ко всем оплачиваемым периодам" in response.text, response.text[
        -4000:
    ]

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            invoices = list(
                await db.scalars(
                    select(BillingInvoice).where(BillingInvoice.workspace_id == workspace)
                )
            )
            assert len(invoices) == 2  # Only the previously paid periods, no attempted charge.

    asyncio.run(verify())


def test_explicit_base_only_renewal_projects_five_gb_despite_old_capacity_cache(client, tmp_path):
    from twobrain_rec_server.billing.purchases import effective_paid_storage

    _configure_billing(client, tmp_path)
    workspace, _ = _prepare_owner_session(client)
    now = seed_periods(client, workspace)

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            subscription.capacity_bytes = 20_000_000_000
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=16)
                )
                == 5_000_000_000
            )

    asyncio.run(verify())


@pytest.mark.parametrize("purpose", ["initial_checkout", "storage_upgrade"])
@pytest.mark.parametrize("http_status", [400, 401, 403, 429, 500, "setup", "secret_io"])
def test_rejected_creation_releases_reservations_but_unknown_result_keeps_them(
    client, monkeypatch, tmp_path, purpose, http_status
):
    import httpx

    from tests.integration.test_billing_purchase_journey import quote_id
    from twobrain_rec_server.billing.yookassa import YooKassaClient
    from twobrain_rec_server.cabinet.web_routes import billing as routes
    from twobrain_rec_server.db.models import BillingAcceptanceBudget, PromotionRedemption
    from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    if purpose == "storage_upgrade":
        seed_periods(client, workspace)
    calls = []

    def reject(request):
        calls.append(request.method)
        return httpx.Response(http_status, json={"type": "error", "code": "synthetic"})

    def provider_factory(settings):
        from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError
        if http_status in {"setup", "secret_io"}:
            calls.append("setup")
            if http_status == "secret_io":
                raise PermissionError("synthetic secret unavailable")
            raise YooKassaConfigurationError("synthetic setup failure")
        return YooKassaClient(settings, transport=httpx.MockTransport(reject))

    monkeypatch.setattr(routes, "YooKassaClient", provider_factory)
    if purpose == "initial_checkout":
        preview_path = "/billing/checkout/preview"
        preview_data = {"cycle": "month", "promo_code": "SYNTHFIRST"}
        post_path = "/billing/checkout/start"
        post_data = {
            **preview_data,
            "idempotency_key": str(uuid4()),
            "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
            "offer_consent": "true",
            "recurring_consent": "true",
        }
    else:
        preview_path = "/billing/storage/preview"
        preview_data = {"package_count": "1", "promo_code": "SYNTHSTORE"}
        post_path = "/billing/purchases/confirm"
        post_data = {"purchase_consent": "true"}
    preview = client.post(preview_path, headers=headers, data=preview_data)
    post_data["quote_id"] = quote_id(preview)
    for _ in range(2):
        response = client.post(post_path, headers=headers, data=post_data, follow_redirects=False)
        assert response.status_code == 303
    assert calls == (["setup"] if http_status in {"setup", "secret_io"} else ["POST"])

    async def state():
        async with client.app_state["sessionmaker"]() as db:
            op = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == workspace, BillingOperation.kind == purpose
                )
            )
            invoice = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == op.id)
            )
            budget = await db.scalar(
                select(BillingAcceptanceBudget).where(
                    BillingAcceptanceBudget.workspace_id == workspace
                )
            )
            promo = await db.scalar(
                select(PromotionRedemption).where(PromotionRedemption.invoice_id == invoice.id)
            )
            return op, invoice, budget, promo

    op, invoice, budget, promo = asyncio.run(state())
    assert budget.spent_minor == 0
    if http_status == 500:
        assert op.state == invoice.status == "manual_resolution"
        assert budget.reserved_minor == invoice.amount_minor > 0
        assert promo.state == "reserved"
    else:
        assert op.state == invoice.status == "canceled"
        assert budget.reserved_minor == 0
        assert promo.state == "released"
        # A fresh calculation can use the same one-use promotion again.
        fresh = client.post(preview_path, headers=headers, data=preview_data)
        assert quote_id(fresh) != post_data["quote_id"]


def test_partly_expired_storage_keeps_valid_access_and_one_financial_remedy(client, tmp_path):
    from twobrain_rec_server.billing.purchases import grant_confirmed_storage
    from twobrain_rec_server.db.models import (
        BillingNotificationDelivery,
        BillingStorageEntitlementGrant,
    )

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, _ = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    now = seed_periods(client, workspace)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            calculation = await calculate_storage_purchase(
                db, subscription=sub, target_capacity_bytes=10_000_000_000, now=now
            )
            segments = [item.as_dict() for item in calculation.segments]
            assert len(segments) == 2
            op = BillingOperation(
                workspace_id=workspace,
                kind="storage_upgrade",
                state="unknown",
                idempotency_key=str(uuid4()),
                request_snapshot={
                    "purchase_schema": 2,
                    "storage_segments": segments,
                    "selection_version": 0,
                    "target_capacity_bytes": 10_000_000_000,
                },
            )
            db.add(op)
            await db.flush()
            invoice = BillingInvoice(
                workspace_id=workspace,
                operation_id=op.id,
                safe_number=f"INV-{uuid4().hex}",
                amount_minor=calculation.payable_amount_minor,
                currency="RUB",
                plan_snapshot={"storage_segments": segments},
            )
            db.add(invoice)
            await db.flush()
            late = now + timedelta(days=16)
            for _ in range(2):
                assert (
                    await grant_confirmed_storage(db, operation=op, invoice=invoice, now=late)
                    == "service_expired"
                )
                assert op.state == "reconciliation_gap" and invoice.status == "succeeded"
            grants = list(
                await db.scalars(
                    select(BillingStorageEntitlementGrant).where(
                        BillingStorageEntitlementGrant.invoice_id == invoice.id
                    )
                )
            )
            assert len(grants) == 1
            assert grants[0].base_grant_id == calculation.segments[1].base_grant_id
            assert sub.capacity_bytes == 10_000_000_000
            assert sub.application_version == 1 and sub.next_capacity_version == 1
            assert op.request_snapshot["reconciliation_detail"]["expired_segment_indices"] == [0]
            notices = list(
                await db.scalars(
                    select(BillingNotificationDelivery).where(
                        BillingNotificationDelivery.event_id == f"payment:{invoice.id}:service_gap"
                    )
                )
            )
            assert len(notices) == 1
            await db.commit()

    asyncio.run(run())


@pytest.mark.parametrize("resume_state", ["scope_closed", "exhausted"])
def test_resume_rejects_closed_scope_or_exhausted_attempts(client, tmp_path, resume_state):
    import re

    from twobrain_rec_server.db.models import BillingPaymentMethod

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_periods(client, workspace)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            sub.recurring_allowed = False
            sub.recurring_authority_version = 2
            db.add(
                BillingPaymentMethod(
                    workspace_id=workspace,
                    owner_user_id=USER_ID,
                    encrypted_provider_ref="synthetic",
                    key_version="synthetic",
                    masked_label="Карта •••• 1111",
                    state="active",
                    is_default=True,
                    verified_at=datetime.now(UTC),
                )
            )
            await db.commit()

    asyncio.run(seed())
    page = client.get("/billing/subscription", headers=headers)
    match = re.search(r'name="resume_quote_id" value="([^"]+)"', page.text)
    assert match
    if resume_state == "scope_closed":
        client.app.state.settings.billing_checkout_workspace_ids = frozenset()
    else:

        async def exhaust():
            async with client.app_state["sessionmaker"]() as db:
                sub = await db.scalar(
                    select(WorkspaceSubscription).where(
                        WorkspaceSubscription.workspace_id == workspace
                    )
                )
                for attempt in (1, 2, 3):
                    db.add(
                        BillingOperation(
                            workspace_id=workspace,
                            kind="renewal",
                            state="canceled",
                            idempotency_key=str(uuid4()),
                            request_snapshot={
                                "renewal_attempt": attempt,
                                "paid_through_at": sub.paid_through.isoformat(),
                            },
                        )
                    )
                await db.commit()

        asyncio.run(exhaust())
    new_page = client.get("/billing/subscription", headers=headers)
    assert 'name="resume_quote_id"' not in new_page.text
    response = client.post(
        "/billing/subscription/resume",
        headers=headers,
        follow_redirects=False,
        data={
            "expected_authority_version": "2",
            "resume_consent": "true",
            "resume_quote_id": match.group(1),
        },
    )
    assert response.status_code == 303 and "result=resumed" not in response.headers["location"]

    async def unchanged():
        async with client.app_state["sessionmaker"]() as db:
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            assert sub.recurring_allowed is False

    asyncio.run(unchanged())


@pytest.mark.parametrize("renewal_state", ["scheduled", "sent", "unknown"])
def test_cycle_checkout_cancels_only_unsent_renewals(client, monkeypatch, tmp_path, renewal_state):
    import httpx

    from tests.integration.test_billing_purchase_journey import quote_id
    from tests.unit.test_billing_money_path_e2e import _FakeYooKassa
    from twobrain_rec_server.billing.yookassa import YooKassaClient
    from twobrain_rec_server.cabinet.web_routes import billing as routes
    from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_periods(client, workspace)
    bound = quote_id(client.get("/billing/checkout?cycle=year", headers=headers))
    pending_id = uuid4()

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                BillingOperation(
                    id=pending_id,
                    workspace_id=workspace,
                    kind="renewal",
                    state=renewal_state,
                    idempotency_key=str(uuid4()),
                    request_snapshot={},
                )
            )
            await db.flush()
            db.add(
                BillingInvoice(
                    workspace_id=workspace,
                    operation_id=pending_id,
                    safe_number="INV-PENDINGRENEWAL",
                    amount_minor=100000,
                    currency="RUB",
                    plan_snapshot={},
                )
            )
            await db.commit()

    asyncio.run(seed())
    provider = _FakeYooKassa(saved_card=True)
    monkeypatch.setattr(
        routes,
        "YooKassaClient",
        lambda settings: YooKassaClient(settings, transport=httpx.MockTransport(provider.handle)),
    )
    response = client.post(
        "/billing/checkout/start",
        headers=headers,
        follow_redirects=False,
        data={
            "cycle": "year",
            "quote_id": bound,
            "idempotency_key": str(uuid4()),
            "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
            "offer_consent": "true",
            "recurring_consent": "true",
        },
    )
    assert response.status_code == 303
    assert len(provider.create_payloads) == (1 if renewal_state == "scheduled" else 0)

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            op = await db.get(BillingOperation, pending_id)
            assert op.state == ("canceled" if renewal_state == "scheduled" else renewal_state)

    asyncio.run(check())


def test_checkout_refresh_reuses_quote_and_removes_only_unconsumed_expired_rows(
    client, tmp_path, monkeypatch
):
    from tests.integration.test_billing_purchase_journey import quote_id
    from twobrain_rec_server.db.models import BillingPurchaseQuote

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    first = quote_id(client.get("/billing/checkout", headers=headers))
    assert quote_id(client.get("/billing/checkout", headers=headers)) == first

    from twobrain_rec_server.cabinet.web_routes import billing as routes

    later = datetime.now(UTC) + timedelta(hours=1)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return later if tz else later.replace(tzinfo=None)

    monkeypatch.setattr(routes, "datetime", FixedDateTime)
    assert quote_id(client.get("/billing/checkout", headers=headers)) != first

    async def removed():
        async with client.app_state["sessionmaker"]() as db:
            assert await db.get(BillingPurchaseQuote, __import__("uuid").UUID(first)) is None

    asyncio.run(removed())


@pytest.mark.parametrize("snapshot", [
    {"purpose": "initial_checkout", "catalog_snapshot": {"storage_bytes": 15_000_000_000}},
    {"purpose": "initial_checkout", "storage_price_snapshot": {"capacity_bytes": 15_000_000_000}},
    {"purpose": "renewal", "storage_capacity_bytes": 15_000_000_000},
])
def test_composite_subscription_invoice_displays_purchased_capacity(client, tmp_path, snapshot):
    _configure_billing(client, tmp_path)
    workspace, headers = _prepare_owner_session(client)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            operation = BillingOperation(workspace_id=workspace, kind=snapshot["purpose"],
                state="succeeded", idempotency_key=str(uuid4()), request_snapshot=snapshot)
            db.add(operation)
            await db.flush()
            db.add(BillingInvoice(workspace_id=workspace, operation_id=operation.id,
                safe_number="INV-COMPOSITE-CAPACITY", amount_minor=150000, currency="RUB",
                status="succeeded", plan_snapshot={"cycle": "month", **snapshot}))
            await db.commit()
    asyncio.run(seed())
    response = client.get("/billing/invoices/INV-COMPOSITE-CAPACITY", headers=headers)
    assert response.status_code == 200
    assert "15 GB" in response.text
