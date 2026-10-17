import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest

from twobrain_rec_server.billing.reconciliation import (
    ObservationRecords,
    ProviderObservationError,
    ProviderScope,
    extract_receipt_observation,
    extract_refund_observation,
    record_observed_refund,
)
from twobrain_rec_server.db.models import BillingInvoice, BillingOperation

SCOPE = ProviderScope(environment="test", shop_id="shop-1")
NOW = datetime(2026, 8, 7, 12, tzinfo=UTC)


def test_full_and_partial_refund_observations_are_read_only_and_idempotent() -> None:
    records = ObservationRecords()
    for amount, refund_id, source in (
        (79000, "refund-full", "webhook"),
        (1000, "refund-partial", "registry"),
    ):
        observation = extract_refund_observation(
            {
                "id": refund_id,
                "payment_id": "pay-1",
                "status": "succeeded",
                "amount": {"value": f"{amount / 100:.2f}", "currency": "RUB"},
                "created_at": NOW.isoformat(),
            },
            scope=SCOPE,
        )
        assert records.record(observation, source=source, observed_at=NOW) == "inserted"
        assert records.record(observation, source="poll", observed_at=NOW) == "duplicate"


def test_receipt_observation_requires_one_parent_and_unknown_webhook_can_use_poll_backstop() -> (
    None
):
    receipt = extract_receipt_observation(
        {
            "id": "receipt-1",
            "type": "payment",
            "payment_id": "pay-1",
            "status": "succeeded",
            "registered_at": NOW.isoformat(),
        },
        scope=SCOPE,
    )
    records = ObservationRecords()
    assert records.record(receipt, source="poll", observed_at=NOW) == "inserted"
    with pytest.raises(ProviderObservationError):
        extract_receipt_observation(
            {
                "id": "receipt-2",
                "type": "payment",
                "payment_id": "pay-1",
                "refund_id": "refund-1",
                "status": "succeeded",
            },
            scope=SCOPE,
        )


def test_provider_refund_observation_is_idempotently_bound_without_refund_mutation(
    monkeypatch,
) -> None:
    operation = BillingOperation(
        id=UUID("11111111-1111-4111-8111-111111111111"),
        workspace_id=UUID("22222222-2222-4222-8222-222222222222"),
        kind="initial_checkout",
        idempotency_key="checkout-1",
        provider_id="pay-1",
    )
    invoice = BillingInvoice(
        id=UUID("33333333-3333-4333-8333-333333333333"),
        workspace_id=operation.workspace_id,
        operation_id=operation.id,
        safe_number="INV-1",
        amount_minor=79_000,
        currency="RUB",
        plan_snapshot={"billing_actor_user_id": "44444444-4444-4444-8444-444444444444"},
    )
    refund = extract_refund_observation(
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "1.00", "currency": "RUB"},
            "created_at": NOW.isoformat(),
        },
        scope=SCOPE,
    )

    class FakeDb:
        def __init__(self):
            self.values = [operation, invoice, None, 0, None]
            self.added = []

        async def scalar(self, _query):
            return self.values.pop(0)

        def add(self, value):
            self.added.append(value)

        async def flush(self):
            return None

    captured = {}

    async def no_reward(*_args, **kwargs):
        captured.update(kwargs)
        return "none"

    monkeypatch.setattr(
        "twobrain_rec_server.billing.reconciliation.reverse_credit_for_payment", no_reward
    )
    db = FakeDb()
    assert (
        asyncio.run(
            record_observed_refund(db, workspace_id=operation.workspace_id, observation=refund)
        )
        == "inserted"
    )
    assert len(db.added) == 1
    assert db.added[0].amount_minor == 100
    assert captured["invitee_user_id"] == UUID("44444444-4444-4444-8444-444444444444")


# Exercise the actual HTTP inbox and worker against PostgreSQL, including the
# deployed role names. Provider replies remain explicitly synthetic fixtures.
pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("refund_amount", ["1.00", "10.00"])
async def test_metadata_less_refund_receipt_http_rls_and_financial_invariants(
    rls_engine,
    migrated_postgres_urls,
    tmp_path,
    monkeypatch,
    refund_amount,
):
    from copy import deepcopy
    from datetime import timedelta
    from uuid import uuid4

    import httpx
    from fastapi import FastAPI
    from sqlalchemy import select, text, update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.integration.test_rls_postgres_policies import (
        _exact_app_role_engine,
        _seed_probe_rows,
    )
    from twobrain_rec_server.api.billing import router
    from twobrain_rec_server.billing import provider_scope
    from twobrain_rec_server.billing.webhook_reconciliation import reconcile_pending_webhook_events
    from twobrain_rec_server.billing.yookassa import YooKassaClient
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db.models import (
        BillingAcceptanceBudget,
        BillingEntitlementGrant,
        BillingStorageEntitlementGrant,
        BillingStoragePriceVersion,
        BillingWebhookEvent,
        ObservedProviderRefund,
        Workspace,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.db.tenant_context import (
        MaintenanceTenantContext,
        WorkspaceAuthContext,
        apply_tenant_context,
    )

    ids = await _seed_probe_rows(rls_engine)
    workspace_id, user_id = ids["workspace_a"], ids["user_a"]
    operation_id, invoice_id = uuid4(), uuid4()
    payment_id = f"payment-{uuid4().hex}"
    refund_id = f"refund-{uuid4().hex}"
    receipt_id = f"receipt-{uuid4().hex}"
    secret = tmp_path / "synthetic-secret"
    secret.write_text("synthetic-secret")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_environment="test",
        billing_yookassa_secret_file=secret,
        billing_yookassa_webhook_secret_file=secret,
        billing_checkout_enabled=False,
        billing_provider_observation_enabled=True,
    )
    payment = {
        "id": payment_id,
        "status": "succeeded",
        "paid": True,
        "test": True,
        "recipient": {"account_id": "shop-1"},
        "amount": {"value": "10.00", "currency": "RUB"},
        "created_at": NOW.isoformat(),
        "metadata": {"workspace_id": str(workspace_id), "operation_id": str(operation_id)},
    }
    refund = {
        "id": refund_id,
        "payment_id": payment_id,
        "status": "succeeded",
        "amount": {"value": refund_amount, "currency": "RUB"},
        "created_at": NOW.isoformat(),
    }
    receipt = {
        "id": receipt_id,
        "refund_id": refund_id,
        "payment_id": payment_id,
        "type": "refund",
        "status": "succeeded",
    }
    state = {"payment": payment, "refund": refund, "receipt": receipt, "status": 200, "delay": 0}
    calls = []

    async def handle(request):
        calls.append((request.method, request.url.path))
        assert request.method == "GET", "observation must never initiate a financial mutation"
        if state["delay"]:
            await asyncio.sleep(state["delay"])
        assert request.url.path != "/v3/refunds", "worker must use the exact refund endpoint"
        kind = request.url.path.split("/")[-2][:-1]
        return httpx.Response(state["status"], json=deepcopy(state[kind]))

    original = YooKassaClient.__init__
    monkeypatch.setattr(
        YooKassaClient,
        "__init__",
        lambda self, settings: original(self, settings, transport=httpx.MockTransport(handle)),
    )
    maintenance_sessions = async_sessionmaker(rls_engine, expire_on_commit=False)
    maintenance = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="test_provider_refund_observation",
        reason_category="refund_probe",
        feature_area="billing",
    )
    async with maintenance_sessions() as db:
        await apply_tenant_context(db, maintenance)
        assert await db.scalar(text("select current_user")) == "twobrain_rec_maintenance"
        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(kind="personal", owner_user_id=user_id)
        )
        await db.execute(
            update(Workspace)
            .where(Workspace.id == ids["workspace_b"])
            .values(kind="personal", owner_user_id=ids["user_b"])
        )
        db.add(
            BillingOperation(
                id=operation_id,
                workspace_id=workspace_id,
                kind="initial_checkout",
                idempotency_key=f"checkout-{uuid4()}",
                provider_id=payment_id,
                state="succeeded",
            )
        )
        await db.flush()
        db.add(
            BillingInvoice(
                id=invoice_id,
                workspace_id=workspace_id,
                operation_id=operation_id,
                safe_number=f"INV-{uuid4()}",
                amount_minor=1000,
                currency="RUB",
                status="paid",
                plan_snapshot={},
            )
        )
        await db.flush()
        grant_id = uuid4()
        db.add(
            BillingEntitlementGrant(
                id=grant_id,
                workspace_id=workspace_id,
                invoice_id=invoice_id,
                provider_payment_id=payment_id,
                plan_code="pro",
                cycle="month",
                starts_at=NOW,
                ends_at=NOW + timedelta(days=31),
                amount_minor=1000,
                currency="RUB",
            )
        )
        await db.flush()
        storage_price = await db.scalar(
            select(BillingStoragePriceVersion).where(
                BillingStoragePriceVersion.capacity_bytes == 5_000_000_000,
                BillingStoragePriceVersion.cycle == "month",
            )
        )
        assert storage_price is not None
        db.add(
            BillingStorageEntitlementGrant(
                workspace_id=workspace_id,
                invoice_id=invoice_id,
                base_grant_id=grant_id,
                capacity_bytes=5_000_000_000,
                starts_at=NOW,
                ends_at=NOW + timedelta(days=31),
                catalog_version_id=storage_price.id,
                full_period_amount_minor=29000,
            )
        )
        db.add(
            WorkspaceSubscription(
                workspace_id=workspace_id,
                billing_owner_id=user_id,
                state="active",
                plan_code="pro",
                cycle="month",
                paid_through=NOW + timedelta(days=31),
                recurring_allowed=False,
            )
        )
        db.add(
            BillingAcceptanceBudget(
                workspace_id=workspace_id,
                limit_minor=20000,
                spent_minor=16245,
                reserved_minor=0,
                enabled=False,
                expires_at=NOW + timedelta(days=31),
            )
        )
        await db.commit()

    async def inspect_rows(model):
        async with maintenance_sessions() as db:
            await apply_tenant_context(db, maintenance)
            rows = (await db.scalars(select(model).where(model.workspace_id == workspace_id))).all()
            return [{c.name: getattr(row, c.name) for c in model.__table__.columns} for row in rows]

    financial_models = (
        BillingOperation,
        BillingInvoice,
        BillingEntitlementGrant,
        BillingStorageEntitlementGrant,
        WorkspaceSubscription,
        BillingAcceptanceBudget,
    )
    before = {model: await inspect_rows(model) for model in financial_models}

    async def reconcile():
        async with maintenance_sessions() as db:
            await apply_tenant_context(db, maintenance)
            return await reconcile_pending_webhook_events(db, settings)

    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as app_engine:
        app = FastAPI()
        app.state.settings = settings
        app.state.db_sessionmaker = async_sessionmaker(app_engine, expire_on_commit=False)
        app.include_router(router)
        async with app.state.db_sessionmaker() as db:
            assert await db.scalar(text("select current_user")) == "twobrain_rec_app"
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="https://test"
        ) as client:

            async def post(kind, obj, *, secret_value="synthetic-secret", env="test"):
                return await client.post(
                    f"/api/v1/billing/providers/yookassa/webhook/{env}",
                    headers={"X-Billing-Webhook-Secret": secret_value},
                    json={"type": "notification", "event": f"{kind}.succeeded", "object": obj},
                )

            # Authentication/environment precede the provider chain.
            for options in ({"secret_value": "wrong"}, {"env": "production"}):
                calls.clear()
                assert (await post("refund", refund, **options)).status_code == 401
                assert calls == []
            # Metadata-bearing callbacks retain the zero-GET inbox fast path.
            fast = deepcopy(refund)
            fast["metadata"] = deepcopy(payment["metadata"])
            fast["id"] = f"fast-{uuid4().hex}"
            calls.clear()
            assert (await post("refund", fast)).status_code == 200
            assert calls == []
            async with maintenance_sessions() as db:
                await apply_tenant_context(db, maintenance)
                # The fixture fast-path signal has no corresponding provider
                # refund; exclude it from this separate ordering scenario.
                await db.execute(
                    update(BillingWebhookEvent)
                    .where(BillingWebhookEvent.object_id == fast["id"])
                    .values(state="reconciled")
                )
                await db.commit()
            # Temporary provider/configuration failures never acknowledge or persist.
            for status in (401, 403, 404, 429, 500, 503):
                state["status"] = status
                calls.clear()
                assert (await post("refund", refund)).status_code == 503
                assert len(calls) == 1
            state["status"] = 200
            incoming_receipt = deepcopy(receipt)
            for kind, field in (("receipt", "type"), ("receipt", "status"), ("payment", "status")):
                old = state[kind][field]
                state[kind][field] = []
                assert (await post("receipt", incoming_receipt)).status_code == 503
                state[kind][field] = old
            old_shop = settings.billing_yookassa_shop_id
            settings.billing_yookassa_shop_id = ""
            assert (await post("refund", refund)).status_code == 503
            settings.billing_yookassa_shop_id = old_shop
            monkeypatch.setattr(provider_scope, "SCOPE_RESOLUTION_TIMEOUT_SECONDS", 0.03)
            state["delay"] = 0.02
            assert (await post("receipt", receipt)).status_code == 503
            state["delay"] = 0
            monkeypatch.setattr(provider_scope, "SCOPE_RESOLUTION_TIMEOUT_SECONDS", 8)
            # Wrong existing tenant, missing tenant, and missing local operation
            # cannot put an event into either tenant's inbox.
            for bad_workspace in (ids["workspace_b"], uuid4()):
                payment["metadata"]["workspace_id"] = str(bad_workspace)
                response = await post("refund", refund)
                assert response.status_code == 503
            payment["metadata"]["workspace_id"] = str(workspace_id)
            payment["metadata"]["operation_id"] = str(uuid4())
            assert (await post("refund", refund)).status_code == 503
            payment["metadata"]["operation_id"] = str(operation_id)
            payment["amount"]["value"] = "11.00"
            assert (await post("refund", refund)).status_code == 401
            payment["amount"]["value"] = "10.00"
            assert len(await inspect_rows(BillingWebhookEvent)) == 1
            receipt["payment_id"] = "conflicting-payment"
            assert (await post("receipt", receipt)).status_code == 401
            receipt["payment_id"] = payment_id
            # A previously personal workspace can become linked after account
            # merge. Keep real provider retries alive without moving any money.
            async with maintenance_sessions() as db:
                await apply_tenant_context(db, maintenance)
                await db.execute(
                    update(Workspace)
                    .where(Workspace.id == workspace_id)
                    .values(kind="linked", owner_user_id=None)
                )
                await db.commit()
            for kind, source in (("refund", refund), ("receipt", receipt)):
                linked_response = await post(kind, source)
                assert linked_response.status_code == 503
                assert linked_response.json()["status"] == "deferred_parent_unavailable"
            assert len(await inspect_rows(BillingWebhookEvent)) == 1
            for model in financial_models:
                assert await inspect_rows(model) == before[model]
            async with maintenance_sessions() as db:
                await apply_tenant_context(db, maintenance)
                await db.execute(
                    update(Workspace)
                    .where(Workspace.id == workspace_id)
                    .values(kind="personal", owner_user_id=user_id)
                )
                await db.commit()
            # Refund receipt arrives first: retain it pending until the actual
            # provider refund notification is reconciled by the normal worker.
            calls.clear()
            response = await post("receipt", receipt)
            assert response.status_code == 200, response.text
            assert len(calls) == 3
            result = await reconcile()
            assert result["pending"] == 1
            assert await inspect_rows(ObservedProviderRefund) == []
            assert (await post("refund", refund)).status_code == 200
            assert (await post("refund", refund)).json()["status"] == "duplicate"
            description_only = {**refund, "description": "private text is not fingerprinted"}
            assert (await post("refund", description_only)).json()["status"] == "duplicate"
            changed = {**refund, "amount": {"value": "0.50", "currency": "RUB"}}
            assert (await post("refund", changed)).json()["status"] == "replay_conflict"
            # Worker failures must retain the durable signal for retry; no
            # global list fallback and no fabricated observation on an ID clash.
            for response_status in (404, 429, 503):
                state["status"] = response_status
                result = await reconcile()
                assert result["pending"] == 2
                assert await inspect_rows(ObservedProviderRefund) == []
            state["status"] = 200
            original_refund_id = refund["id"]
            refund["id"] = "different-refund"
            assert (await reconcile())["pending"] == 2
            assert await inspect_rows(ObservedProviderRefund) == []
            refund["id"] = original_refund_id
            calls.clear()
            await reconcile()
            assert ("GET", f"/v3/refunds/{refund_id}") in calls
            assert ("GET", "/v3/refunds") not in calls
            # Even metadata-bearing/worker receipt observations cannot use a
            # conflicting optional payment hint to update a refund's invoice.
            receipt["payment_id"] = "foreign-payment"
            assert (await reconcile())["pending"] == 1
            assert (await inspect_rows(BillingInvoice))[0]["plan_snapshot"] == {}
            receipt["payment_id"] = payment_id
            await reconcile()
            observed = await inspect_rows(ObservedProviderRefund)
            assert len(observed) == 1 and observed[0]["amount_minor"] == int(
                float(refund_amount) * 100
            )
            events = await inspect_rows(BillingWebhookEvent)
            assert len(events) == 3 and all(row["state"] == "reconciled" for row in events)
            invoice = (await inspect_rows(BillingInvoice))[0]
            assert invoice["plan_snapshot"]["receipt_observations"]
            # New resolution writes only inbox, worker writes refund/receipt
            # observations; no refund/charge request or paid-service change.
            for model in financial_models:
                after = await inspect_rows(model)
                if model is BillingInvoice:
                    after[0]["plan_snapshot"] = before[model][0]["plan_snapshot"]
                assert after == before[model], model.__name__
            async with app.state.db_sessionmaker() as db:
                await apply_tenant_context(
                    db, WorkspaceAuthContext(workspace_id=ids["workspace_b"])
                )
                assert (
                    await db.scalars(
                        select(BillingWebhookEvent).where(
                            BillingWebhookEvent.workspace_id == workspace_id
                        )
                    )
                ).all() == []
                assert (
                    await db.scalars(
                        select(ObservedProviderRefund).where(
                            ObservedProviderRefund.workspace_id == workspace_id
                        )
                    )
                ).all() == []
