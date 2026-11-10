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
                request_snapshot={"provider_environment": "test", "provider_shop_id": "shop-1"},
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
                status="succeeded",
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

    async def reconcile(limit=100):
        async with maintenance_sessions() as db:
            await apply_tenant_context(db, maintenance)
            return await reconcile_pending_webhook_events(db, settings, limit=limit)

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
            for invalid_shop_id in ("", " shop-1 ", "x" * 161):
                settings.billing_yookassa_shop_id = invalid_shop_id
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
            await reconcile(limit=1)
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
                    after[0]["plan_snapshot"].pop("receipt_observations", None)
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


@pytest.fixture
async def refund_queue_case(rls_engine, tmp_path, monkeypatch):
    """Isolated synthetic queue rows on the actual maintenance PostgreSQL role."""
    from copy import deepcopy
    from datetime import timedelta
    from types import SimpleNamespace
    from uuid import uuid4

    import httpx
    from sqlalchemy import delete, select, text, update
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing import webhook_reconciliation
    from twobrain_rec_server.billing.yookassa import YooKassaClient
    from twobrain_rec_server.config import Settings
    from twobrain_rec_server.db.models import (
        BillingAcceptanceBudget,
        BillingAcceptanceReservation,
        BillingEntitlementGrant,
        BillingStorageEntitlementGrant,
        BillingStoragePriceVersion,
        BillingWebhookEvent,
        Workspace,
        WorkspaceSubscription,
    )
    from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

    ids = await _seed_probe_rows(rls_engine)
    workspace_id, owner_id = ids["workspace_a"], ids["user_a"]
    operation_id, invoice_id = uuid4(), uuid4()
    payment_id, refund_id = f"payment-{uuid4()}", f"refund-{uuid4()}"
    secret = tmp_path / "synthetic-provider"
    secret.write_text("synthetic")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_environment="test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
        billing_yookassa_webhook_secret_file=secret,
        billing_provider_observation_enabled=True,
    )
    context = MaintenanceTenantContext(
        operation_name="billing_reconciliation",
        actor_id="refund_queue_test",
        reason_category="isolated_test",
        feature_area="billing",
    )
    sessions = async_sessionmaker(rls_engine, expire_on_commit=False)
    calls = []
    receipt_parents = {}
    provider_state = {"malformed_receipts": False}

    async def transport(request):
        calls.append((request.method, request.url.path))
        assert request.method == "GET"
        if request.url.path.startswith("/v3/receipts/"):
            return httpx.Response(
                200,
                json={
                    "id": provider_state.get("receipt_response_id", request.url.path.rsplit("/", 1)[1]),
                    "type": "refund",
                    "status": [] if provider_state["malformed_receipts"] else provider_state.get(
                        "receipt_status", "succeeded"
                    ),
                    "refund_id": receipt_parents[request.url.path.rsplit("/", 1)[1]],
                    "payment_id": payment_id,
                },
            )
        if request.url.path == f"/v3/refunds/{refund_id}":
            return httpx.Response(
                200,
                json={
                    "id": refund_id,
                    "payment_id": payment_id,
                    "status": "succeeded",
                    "amount": {"value": "1.00", "currency": "RUB"},
                    "created_at": NOW.isoformat(),
                },
            )
        return httpx.Response(429, json={"type": "error"})

    original = YooKassaClient.__init__
    monkeypatch.setattr(
        YooKassaClient,
        "__init__",
        lambda self, settings: original(self, settings, transport=httpx.MockTransport(transport)),
    )
    async with sessions() as db:
        await apply_tenant_context(db, context)
        assert await db.scalar(text("select current_user")) == "twobrain_rec_maintenance"
        await db.execute(
            update(Workspace)
            .where(Workspace.id == workspace_id)
            .values(kind="personal", owner_user_id=owner_id)
        )
        db.add(
            BillingOperation(
                id=operation_id,
                workspace_id=workspace_id,
                kind="initial_checkout",
                idempotency_key=f"checkout-{uuid4()}",
                provider_id=payment_id,
                state="succeeded",
                request_snapshot={"provider_environment": "test", "provider_shop_id": "shop-1"},
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
                status="succeeded",
                plan_snapshot={},
            )
        )
        await db.flush()
        grant_id, budget_id = uuid4(), uuid4()
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
        db.add(
            BillingAcceptanceBudget(
                id=budget_id,
                workspace_id=workspace_id,
                limit_minor=20000,
                reserved_minor=0,
                spent_minor=16245,
                enabled=False,
                expires_at=NOW + timedelta(days=31),
            )
        )
        db.add(
            WorkspaceSubscription(
                workspace_id=workspace_id,
                billing_owner_id=owner_id,
                state="active",
                plan_code="pro",
                cycle="month",
                recurring_allowed=False,
                paid_through=NOW + timedelta(days=31),
            )
        )
        await db.flush()
        price_id = await db.scalar(
            select(BillingStoragePriceVersion.id).where(
                BillingStoragePriceVersion.capacity_bytes == 5_000_000_000,
                BillingStoragePriceVersion.cycle == "month",
            )
        )
        db.add(
            BillingStorageEntitlementGrant(
                workspace_id=workspace_id,
                invoice_id=invoice_id,
                base_grant_id=grant_id,
                capacity_bytes=5_000_000_000,
                starts_at=NOW,
                ends_at=NOW + timedelta(days=31),
                catalog_version_id=price_id,
                full_period_amount_minor=29000,
            )
        )
        db.add(
            BillingAcceptanceReservation(
                workspace_id=workspace_id,
                budget_id=budget_id,
                operation_id=operation_id,
                amount_minor=1000,
                state="spent",
            )
        )
        await db.commit()

    async def add_events(kind, count, received_at, *, receipt_id=None):
        async with sessions() as db:
            await apply_tenant_context(db, context)
            event_ids = []
            for index in range(count):
                event_id = uuid4()
                event_ids.append(event_id)
                object_id = refund_id if kind == "parent" else receipt_id or f"{kind}-{event_id}"
                if kind in {"receipt", "malformed-receipt"}:
                    receipt_parents[object_id] = refund_id if index == 0 else f"missing-{event_id}"
                    provider_state["malformed_receipts"] = kind == "malformed-receipt"
                db.add(
                    BillingWebhookEvent(
                        id=event_id,
                        workspace_id=workspace_id,
                        provider_event_id=f"event-{event_id}",
                        event_type=(
                            "receipt.waiting_for_cancellation"
                            if provider_state.get("receipt_status") == "canceled"
                            else "receipt.succeeded"
                        ) if kind in {"receipt", "malformed-receipt"} else "refund.succeeded",
                        object_id=object_id,
                        occurred_at=NOW,
                        received_at=received_at,
                        payload_hash="a" * 64,
                        state="pending_reconciliation",
                        metadata_json={"retained": "safe"},
                    )
                )
            await db.commit()
            return event_ids

    async def rows(model):
        async with sessions() as db:
            await apply_tenant_context(db, context)
            return [
                {
                    column.name: deepcopy(getattr(row, column.name))
                    for column in model.__table__.columns
                }
                for row in (
                    await db.scalars(select(model).where(model.workspace_id == workspace_id))
                ).all()
            ]

    async def process(limit):
        async with sessions() as db:
            await apply_tenant_context(db, context)
            return await webhook_reconciliation.reconcile_pending_webhook_events(
                db, settings, limit=limit
            )

    financial_models = (
        BillingOperation,
        BillingInvoice,
        BillingEntitlementGrant,
        BillingStorageEntitlementGrant,
        WorkspaceSubscription,
        BillingAcceptanceBudget,
        BillingAcceptanceReservation,
    )
    before_financial = {model: await rows(model) for model in financial_models}

    async def assert_financial_unchanged():
        for model in financial_models:
            after = await rows(model)
            if model is BillingInvoice:
                after[0]["plan_snapshot"].pop("receipt_observations", None)
            assert after == before_financial[model], model.__name__

    case = SimpleNamespace(
        sessions=sessions,
        context=context,
        settings=settings,
        workspace_id=workspace_id,
        owner_id=owner_id,
        invoice_id=invoice_id,
        refund_id=refund_id,
        calls=calls,
        provider_state=provider_state,
        add_events=add_events,
        rows=rows,
        process=process,
        assert_financial_unchanged=assert_financial_unchanged,
    )
    try:
        yield case
    finally:
        # Remove only this test's deliberately unresolvable synthetic signals,
        # so later scenarios do not consume their batches on fixture leftovers.
        async with sessions() as db:
            await apply_tenant_context(db, context)
            await db.execute(
                delete(BillingWebhookEvent).where(BillingWebhookEvent.workspace_id == workspace_id)
            )
            await db.commit()


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [1, 100])
@pytest.mark.parametrize("blocked_kind", ["receipt", "bad-refund", "malformed-receipt"])
async def test_refund_queue_failed_batch_cannot_starve_new_parent(
    refund_queue_case, limit, blocked_kind
):
    from datetime import timedelta

    from twobrain_rec_server.db.models import BillingWebhookEvent, ObservedProviderRefund

    case = refund_queue_case
    blocked_ids = await case.add_events(blocked_kind, limit, NOW)
    await case.add_events("parent", 1, NOW + timedelta(seconds=1))
    before = {row["id"]: row for row in await case.rows(BillingWebhookEvent)}
    first = await case.process(limit)
    assert first["processed"] == first["pending"] == limit
    assert await case.rows(ObservedProviderRefund) == []
    second = await case.process(limit)
    assert second["processed"] <= limit
    assert len(await case.rows(ObservedProviderRefund)) == 1
    case.provider_state["malformed_receipts"] = False
    third = await case.process(limit)
    assert third["processed"] <= limit
    after = await case.rows(BillingWebhookEvent)
    for row in after:
        for field in (
            "provider_event_id",
            "object_id",
            "occurred_at",
            "received_at",
            "payload_hash",
        ):
            assert row[field] == before[row["id"]][field]
        assert row["metadata_json"]["retained"] == "safe"
    if blocked_kind in {"receipt", "malformed-receipt"}:
        target = next(row for row in after if row["id"] == blocked_ids[0])
        assert target["state"] == "reconciled"
        assert sum(row["state"] == "pending_reconciliation" for row in after) == limit - 1
    else:
        assert sum(row["state"] == "pending_reconciliation" for row in after) == limit
    for row in after:
        if row["state"] == "pending_reconciliation":
            assert "reconciliation_attempted_at" in row["metadata_json"]
    invoice = (await case.rows(BillingInvoice))[0]
    assert invoice["amount_minor"] == 1000 and invoice["status"] == "succeeded"
    assert (await case.rows(BillingOperation))[0]["state"] == "succeeded"
    await case.assert_financial_unchanged()


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_receipt_get_must_match_requested_receipt(refund_queue_case):
    case = refund_queue_case
    await case.add_events("parent", 1, NOW)
    assert (await case.process(1))["reconciled"] == 1

    await case.add_events("receipt", 1, NOW)
    before = await case.rows(BillingInvoice)
    case.provider_state["receipt_response_id"] = "different-receipt"
    assert (await case.process(1))["pending"] == 1
    assert await case.rows(BillingInvoice) == before

    del case.provider_state["receipt_response_id"]
    assert (await case.process(1))["reconciled"] == 1
    snapshot = (await case.rows(BillingInvoice))[0]["plan_snapshot"]
    assert len(snapshot["receipt_observations"]) == 1
    await case.assert_financial_unchanged()


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("shop", ["shop-1", "other-shop", None])
async def test_canceled_refund_receipt_basis_requires_bound_shop(
    refund_queue_case, shop, monkeypatch
):
    from sqlalchemy import select

    from twobrain_rec_server.billing import webhook_reconciliation
    from twobrain_rec_server.db.models import (
        BillingNotificationDelivery,
        BillingReceiptIdentity,
        BillingWebhookEvent,
    )
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        operation = await db.scalar(
            select(BillingOperation).where(BillingOperation.workspace_id == case.workspace_id)
        )
        operation.request_snapshot = (
            {"provider_environment": "test", "provider_shop_id": shop} if shop else {}
        )
        await db.commit()

    await case.add_events("parent", 1, NOW)
    assert (await case.process(1))["reconciled"] == 1
    case.provider_state["receipt_status"] = "canceled"
    before = (await case.rows(BillingInvoice))[0]
    await case.add_events("receipt", 1, NOW, receipt_id="synthetic-canceled-refund-receipt")
    if shop == "shop-1":
        record = webhook_reconciliation.record_observed_receipt

        async def fail_after_flush(*args, **kwargs):
            assert await record(*args, **kwargs) == ("inserted", False)
            raise ProviderObservationError("synthetic rollback after receipt flush")

        with monkeypatch.context() as scoped:
            scoped.setattr(webhook_reconciliation, "record_observed_receipt", fail_after_flush)
            assert (await case.process(1))["pending"] == 1
        assert (await case.rows(BillingInvoice))[0] == before
        assert not await case.rows(BillingReceiptIdentity)

    started = datetime.now(UTC)
    counters = await case.process(1)
    after = (await case.rows(BillingInvoice))[0]
    if shop != "shop-1":
        assert counters["pending"] == 1
        assert after == before
        return

    assert counters["reconciled"] == 1
    entry = next(iter(after["plan_snapshot"]["receipt_observations"].values()))
    assert entry["status"] == "canceled"
    assert entry["observed_at"] == NOW.isoformat()
    basis = entry["canceled"]
    assert started <= datetime.fromisoformat(basis["detected_at"]) <= datetime.now(UTC)
    assert basis["due_at"] == basis["detected_at"]
    await case.add_events("receipt", 1, NOW, receipt_id="synthetic-canceled-refund-receipt")
    assert (await case.process(1))["reconciled"] == 1
    assert (await case.rows(BillingInvoice))[0] == after
    case.provider_state["receipt_status"] = "pending"
    await case.add_events("receipt", 1, NOW, receipt_id="second-synthetic-refund-receipt")
    assert (await case.process(1))["reconciled"] == 1
    records = (await case.rows(BillingInvoice))[0]["plan_snapshot"]["receipt_observations"]
    assert records["test:shop-1:synthetic-canceled-refund-receipt"] == entry
    second = records["test:shop-1:second-synthetic-refund-receipt"]
    assert second["legacy_pending_unknown"] is False
    assert started <= datetime.fromisoformat(second["first_confirmed_pending_at"]) <= datetime.now(UTC)
    assert "canceled" not in second
    identities = await case.rows(BillingReceiptIdentity)
    assert len(identities) == 2
    assert {identity["provider_parent_id"] for identity in identities} == {case.refund_id}
    assert all(row["state"] == "reconciled" for row in await case.rows(BillingWebhookEvent))
    assert not await case.rows(BillingNotificationDelivery)


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["receipt", "parent"])
async def test_child_accepted_before_account_merge_stays_pending_in_worker(refund_queue_case, kind):
    from sqlalchemy import update

    from twobrain_rec_server.db.models import BillingWebhookEvent, Workspace
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    await case.add_events(kind, 1, NOW)
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        await db.execute(
            update(Workspace)
            .where(Workspace.id == case.workspace_id)
            .values(kind="linked", owner_user_id=None)
        )
        await db.commit()
    result = await case.process(1)
    assert result == {"processed": 1, "reconciled": 0, "pending": 1, "failed": 0}
    assert case.calls == []
    row = (await case.rows(BillingWebhookEvent))[0]
    assert row["state"] == "pending_reconciliation"
    assert "reconciliation" not in row["metadata_json"]
    assert (await case.rows(BillingInvoice))[0]["amount_minor"] == 1000
    await case.assert_financial_unchanged()


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("concurrent_success", [False, True])
async def test_retry_marker_commits_after_financial_rollback_without_overwriting_success(
    refund_queue_case,
    monkeypatch,
    concurrent_success,
):
    from sqlalchemy import select, update

    from twobrain_rec_server.billing import webhook_reconciliation
    from twobrain_rec_server.db.models import BillingWebhookEvent
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    event_ids = await case.add_events("parent", 1, NOW)
    before = (await case.rows(BillingWebhookEvent))[0]

    async def fail_after_flush(db, *_args):
        invoice = await db.scalar(
            select(BillingInvoice).where(BillingInvoice.id == case.invoice_id)
        )
        invoice.amount_minor = 9876
        await db.flush()
        raise ProviderObservationError("synthetic failure after partial work")

    monkeypatch.setattr(webhook_reconciliation, "_reconcile_event", fail_after_flush)
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        rollback = db.rollback

        async def rollback_then_other_worker_completes():
            await rollback()
            if concurrent_success:
                async with case.sessions() as other:
                    await apply_tenant_context(other, case.context)
                    await other.execute(
                        update(BillingWebhookEvent)
                        .where(BillingWebhookEvent.id == event_ids[0])
                        .values(state="reconciled", metadata_json={"completed_elsewhere": True})
                    )
                    await other.commit()

        monkeypatch.setattr(db, "rollback", rollback_then_other_worker_completes)
        result = await webhook_reconciliation.reconcile_pending_webhook_events(
            db, case.settings, limit=1
        )
    assert result["pending"] == 1
    await case.assert_financial_unchanged()
    after = (await case.rows(BillingWebhookEvent))[0]
    for field in ("provider_event_id", "object_id", "occurred_at", "received_at", "payload_hash"):
        assert after[field] == before[field]
    if concurrent_success:
        assert after["state"] == "reconciled"
        assert after["metadata_json"] == {"completed_elsewhere": True}
    else:
        assert after["state"] == "pending_reconciliation"
        assert after["metadata_json"]["retained"] == "safe"
        assert (
            datetime.fromisoformat(after["metadata_json"]["reconciliation_attempted_at"]).tzinfo
            is not None
        )


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_accepted_refund_with_temporarily_missing_parent_retries(refund_queue_case):
    from sqlalchemy import select, update

    from twobrain_rec_server.db.models import BillingWebhookEvent, ObservedProviderRefund
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    await case.add_events("parent", 1, NOW)
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        operation = await db.scalar(
            select(BillingOperation).where(BillingOperation.workspace_id == case.workspace_id)
        )
        original_payment_id = operation.provider_id
        original_updated_at = operation.updated_at
        operation.provider_id = None
        await db.commit()
    result = await case.process(1)
    assert result["pending"] == 1 and result["reconciled"] == 0
    assert await case.rows(ObservedProviderRefund) == []
    assert (await case.rows(BillingWebhookEvent))[0]["state"] == "pending_reconciliation"
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        await db.execute(
            update(BillingOperation)
            .where(BillingOperation.workspace_id == case.workspace_id)
            .values(provider_id=original_payment_id, updated_at=original_updated_at)
        )
        await db.commit()
    assert (await case.process(1))["reconciled"] == 1
    assert len(await case.rows(ObservedProviderRefund)) == 1
    await case.assert_financial_unchanged()


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("workspace_and_scope", ["same", "different-workspace", "different-shop", "different-environment"])
async def test_receipt_id_is_unique_across_concurrent_invoices(
    refund_queue_case, rls_engine, workspace_and_scope,
):
    from dataclasses import replace
    from uuid import uuid4

    from sqlalchemy import select

    from tests.integration.test_rls_postgres_policies import _seed_probe_rows
    from twobrain_rec_server.billing.reconciliation import record_observed_receipt
    from twobrain_rec_server.db.models import BillingReceiptIdentity
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    workspace_ids = (
        case.workspace_id,
        (await _seed_probe_rows(rls_engine))["workspace_a"]
        if workspace_and_scope == "different-workspace" else case.workspace_id,
    )
    scope = ProviderScope(environment="test", shop_id="shop-1")
    alternate = {
        "different-shop": replace(scope, shop_id="shop-2"),
        "different-environment": replace(scope, environment="production"),
    }.get(workspace_and_scope, scope)
    receipt_id = f"receipt-{uuid4()}"
    invoices = []
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        for workspace_id, invoice_scope in zip(workspace_ids, (scope, alternate), strict=True):
            operation = BillingOperation(
                id=uuid4(), workspace_id=workspace_id, kind="initial_checkout",
                idempotency_key=str(uuid4()), provider_id=f"payment-{uuid4()}", state="succeeded",
                request_snapshot={
                    "provider_environment": invoice_scope.environment,
                    "provider_shop_id": invoice_scope.shop_id,
                },
            )
            db.add(operation)
            await db.flush()
            invoice_id = uuid4()
            db.add(BillingInvoice(
                id=invoice_id, workspace_id=workspace_id, operation_id=operation.id,
                safe_number=f"INV-{uuid4()}", amount_minor=1000, currency="RUB",
                status="succeeded", plan_snapshot={},
            ))
            invoices.append((workspace_id, invoice_id, operation.provider_id, invoice_scope))
        await db.commit()

    async def observe(item, status="pending", *, commit=True):
        workspace_id, _, payment_id, invoice_scope = item
        observation = extract_receipt_observation(
            {"id": receipt_id, "type": "payment", "payment_id": payment_id, "status": status},
            scope=invoice_scope,
        )
        async with case.sessions() as db:
            await apply_tenant_context(db, case.context)
            result = await record_observed_receipt(db, workspace_id=workspace_id, observation=observation)
            if commit:
                await db.commit()
            return result

    assert await observe(invoices[0], commit=False) == ("inserted", False)
    outcomes = await asyncio.wait_for(
        asyncio.gather(*(observe(item) for item in invoices)), timeout=10
    )
    if scope != alternate:
        assert outcomes == [("inserted", False), ("inserted", False)]
        return
    assert sorted(outcomes) == [("conflict", False), ("inserted", False)]
    winner = outcomes.index(("inserted", False))
    assert await observe(invoices[winner], "succeeded") == ("updated", True)
    assert await observe(invoices[winner], "succeeded") == ("duplicate", False)
    assert await observe(invoices[1 - winner], "succeeded") == ("conflict", False)

    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        loser = await db.scalar(select(BillingInvoice).where(BillingInvoice.id == invoices[1 - winner][1]))
        assert (loser.status, loser.amount_minor, loser.plan_snapshot) == ("succeeded", 1000, {})


    async with case.sessions() as db:
        await apply_tenant_context(db, replace(case.context, operation_name="operator_diagnostics"))
        assert await db.scalar(
            select(BillingReceiptIdentity.invoice_id).filter_by(provider_receipt_id=receipt_id)
        ) is None


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("first", ["payment", "receipt", "legacy_canceled"])
async def test_payment_receipt_confirmation_clock_survives_id_binding(refund_queue_case, first):
    from sqlalchemy import select

    from twobrain_rec_server.billing.receipts import merge_confirmed_receipt_registration
    from twobrain_rec_server.billing.reconciliation import record_observed_receipt
    from twobrain_rec_server.db.models import BillingNotificationDelivery
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    payment_id = (await case.rows(BillingOperation))[0]["provider_id"]
    receipt_id = f"receipt-{case.invoice_id}"
    timing_key = "receipt_registration_timing"

    async def card():
        return (await case.rows(BillingInvoice))[0]["plan_snapshot"]

    async def confirm(source, status):
        async with case.sessions() as db:
            await apply_tenant_context(db, case.context)
            if source == "receipt":
                observation = extract_receipt_observation(
                    {"id": receipt_id, "type": "payment", "payment_id": payment_id, "status": status},
                    scope=SCOPE,
                )
                outcome = await record_observed_receipt(
                    db, workspace_id=case.workspace_id, observation=observation, observed_at=NOW,
                )
                assert outcome[0] in {"inserted", "updated", "duplicate"}
            else:
                invoice = await db.scalar(
                    select(BillingInvoice).where(BillingInvoice.id == case.invoice_id).with_for_update()
                )
                invoice.plan_snapshot, available = await merge_confirmed_receipt_registration(
                    db, invoice.plan_snapshot, status=status,
                    payment_binding=(SCOPE.environment, SCOPE.shop_id, payment_id),
                )
                assert not available
            await db.commit()

    if first == "legacy_canceled":
        async with case.sessions() as db:
            await apply_tenant_context(db, case.context)
            invoice = await db.get(BillingInvoice, case.invoice_id)
            invoice.plan_snapshot = {"receipt_registration": "canceled"}
            await db.commit()
        assert timing_key not in await card()
        pending_timing = {}
    else:
        started = datetime.now(UTC)
        await confirm(first, "pending")
        pending_timing = (await card())[timing_key]
        assert pending_timing["legacy_pending_unknown"] is False
        assert started <= datetime.fromisoformat(pending_timing["first_confirmed_pending_at"]) <= datetime.now(UTC)
        await confirm("receipt" if first == "payment" else "payment", "pending")
        assert (await card())[timing_key] == pending_timing

    started = datetime.now(UTC)
    await confirm("receipt" if first == "payment" else "payment", "canceled")
    saved = await card()
    basis = saved[timing_key]["canceled"]
    assert basis["freshness"] == "confirmed"
    assert basis["detected_at"] == basis["due_at"]
    assert started <= datetime.fromisoformat(basis["detected_at"]) <= datetime.now(UTC)
    assert saved[timing_key] == {**pending_timing, "canceled": basis}
    await confirm("payment", "canceled")
    await confirm("receipt", "canceled")
    assert (await card())[timing_key] == saved[timing_key]
    assert not await case.rows(BillingNotificationDelivery)


@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("latest_status", ["pending", "succeeded", "canceled"])
async def test_receipt_overdue_reads_locked_invoice_and_survives_retry(refund_queue_case, latest_status):
    from datetime import timedelta

    from sqlalchemy import func, select

    from twobrain_rec_server.billing.reconciliation import record_observed_receipt
    from twobrain_rec_server.db.models import BillingNotificationDelivery, BillingReceiptIdentity
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    payment_id = (await case.rows(BillingOperation))[0]["provider_id"]
    observation = extract_receipt_observation(
        {"id": f"receipt-{case.invoice_id}", "type": "payment",
         "payment_id": payment_id, "status": "pending"},
        scope=SCOPE,
    )
    timing_key = "receipt_registration_timing"
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        now = await db.scalar(select(func.clock_timestamp()))
        first = now - timedelta(hours=73)
        due = first + timedelta(hours=72)
        invoice = await db.get(BillingInvoice, case.invoice_id)
        previous_timing = {"first_confirmed_pending_at": first.isoformat(), "legacy_pending_unknown": True}
        invoice.plan_snapshot = {"receipt_registration": "pending", timing_key: previous_timing}
        await db.commit()

    async def accept(db):
        return await record_observed_receipt(
            db, workspace_id=case.workspace_id, observation=observation, observed_at=NOW,
        )

    async with case.sessions() as stale:
        await apply_tenant_context(stale, case.context)
        invoice = await stale.get(BillingInvoice, case.invoice_id)
        assert invoice.plan_snapshot["receipt_registration"] == "pending"
        if latest_status != "pending":
            async with case.sessions() as writer:
                await apply_tenant_context(writer, case.context)
                current = await writer.get(BillingInvoice, case.invoice_id)
                current.plan_snapshot = {**current.plan_snapshot, "receipt_registration": latest_status}
                await writer.commit()
            assert invoice.plan_snapshot["receipt_registration"] == "pending"
            assert await accept(stale) == ("conflict", False)
            await stale.commit()
        else:
            assert await accept(stale) == ("inserted", False)
            assert "pending_overdue" in invoice.plan_snapshot[timing_key]
            await stale.rollback()

    readback = (await case.rows(BillingInvoice))[0]["plan_snapshot"]
    assert readback["receipt_registration"] == latest_status
    assert readback[timing_key] == previous_timing
    assert not await case.rows(BillingReceiptIdentity)
    if latest_status == "pending":
        async with case.sessions() as db:
            await apply_tenant_context(db, case.context)
            assert await accept(db) == ("inserted", False)
            await db.commit()
        saved = (await case.rows(BillingInvoice))[0]["plan_snapshot"][timing_key]
        overdue = saved["pending_overdue"]
        assert overdue["due_at"] == due.isoformat()
        assert overdue["freshness"] == "confirmed"
        assert now <= datetime.fromisoformat(overdue["detected_at"]) <= datetime.now(UTC)
        async with case.sessions() as db:
            await apply_tenant_context(db, case.context)
            assert await accept(db) == ("duplicate", False)
            await db.commit()
        assert (await case.rows(BillingInvoice))[0]["plan_snapshot"][timing_key] == saved
    assert not await case.rows(BillingNotificationDelivery)



@pytest.mark.strict_rls
@pytest.mark.asyncio
@pytest.mark.parametrize("status", ["canceled", "succeeded"])
async def test_malformed_payment_receipt_timing_preserves_fiscal_atomicity(refund_queue_case, status):
    from twobrain_rec_server.billing.receipts import merge_confirmed_receipt_registration
    from twobrain_rec_server.billing.reconciliation import record_observed_receipt
    from twobrain_rec_server.db.models import BillingReceiptIdentity
    from twobrain_rec_server.db.tenant_context import apply_tenant_context

    case = refund_queue_case
    payment_id = (await case.rows(BillingOperation))[0]["provider_id"]
    previous = {"receipt_registration": "pending", "receipt_registration_timing": "invalid"}
    observation = extract_receipt_observation(
        {"id": f"receipt-{case.invoice_id}", "type": "payment",
         "payment_id": payment_id, "status": status},
        scope=SCOPE,
    )
    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        invoice = await db.get(BillingInvoice, case.invoice_id)
        invoice.plan_snapshot = previous
        await db.commit()

    async with case.sessions() as db:
        await apply_tenant_context(db, case.context)
        args = {"status": status, "payment_binding": (SCOPE.environment, SCOPE.shop_id, payment_id)}
        if status == "canceled":
            with pytest.raises(ValueError, match="receipt timing is invalid"):
                await merge_confirmed_receipt_registration(db, previous, **args)
        else:
            merged, available = await merge_confirmed_receipt_registration(db, previous, **args)
            assert available and merged == {**previous, "receipt_registration": "succeeded"}
        result = await record_observed_receipt(db, workspace_id=case.workspace_id, observation=observation)
        assert result == (("conflict", False) if status == "canceled" else ("inserted", True))
        await db.commit()

    snapshot = (await case.rows(BillingInvoice))[0]["plan_snapshot"]
    assert snapshot["receipt_registration_timing"] == previous["receipt_registration_timing"]
    if status == "canceled":
        assert snapshot == previous
        assert not await case.rows(BillingReceiptIdentity)
    else:
        assert snapshot["receipt_registration"] == "succeeded"
        assert len(await case.rows(BillingReceiptIdentity)) == 1
