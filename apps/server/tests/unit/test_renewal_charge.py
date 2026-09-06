from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from cryptography.fernet import Fernet

from twobrain_rec_server.billing.payment_methods import seal_provider_reference
from twobrain_rec_server.billing.renewal_charge import (
    RENEWAL_CANDIDATE_STATES,
    charge_renewal_operation,
    pending_renewal_charge_candidates,
    plan_due_renewals,
    project_renewal_cutoffs,
    renewal_invoice_number,
    renewal_operation_key,
)
from twobrain_rec_server.billing.yookassa import YooKassaProviderError
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

WORKSPACE_ID = UUID("11111111-1111-4111-8111-111111111111")
OWNER_ID = UUID("22222222-2222-4222-8222-222222222222")
OPERATION_ID = UUID("33333333-3333-4333-8333-333333333333")
PAID_THROUGH = datetime(2026, 8, 10, tzinfo=UTC)


class FakeDb:
    def __init__(self, values: list[object]) -> None:
        self._values = iter(values)
        self.commits = 0
        self.rollbacks = 0
        self.added: list[object] = []
        self.workspace = Workspace(
            id=WORKSPACE_ID,
            organization_id=UUID("44444444-4444-4444-8444-444444444444"),
            slug="personal-owner",
            name="Моё пространство",
            kind="personal",
            owner_user_id=OWNER_ID,
        )
        self.membership = WorkspaceMembership(
            workspace_id=WORKSPACE_ID,
            user_id=OWNER_ID,
            role="owner",
            status="active",
        )

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def scalar(self, _query: object) -> object:
        descriptions = getattr(_query, "column_descriptions", ())
        if descriptions and descriptions[0].get("entity") is WorkspaceMembership:
            return self.membership
        return next(self._values)

    async def get(self, model: object, _key: object) -> object | None:
        return self.workspace if model is Workspace else None

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.commits += 1

    def add(self, value: object) -> None:
        self.added.append(value)


class PlanningDb(FakeDb):
    def __init__(self, values: list[object]) -> None:
        super().__init__(values)

    async def scalars(self, _query: object) -> list[WorkspaceSubscription]:
        return [next(self._values)]  # type: ignore[return-value]


class FakeProvider:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[dict[str, object]] = []

    async def __aenter__(self) -> FakeProvider:
        return self

    async def __aexit__(self, *_: object) -> None:
        return None

    async def create_payment(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        if isinstance(self.response, BaseException):
            raise self.response
        return self.response


def _settings(tmp_path: Path) -> Settings:
    key_path = tmp_path / "billing-key"
    key_path.write_bytes(Fernet.generate_key())
    secret_path = tmp_path / "provider-secret"
    secret_path.write_text("synthetic", encoding="utf-8")
    webhook_path = tmp_path / "provider-webhook-secret"
    webhook_path.write_text("synthetic-webhook", encoding="utf-8")
    referral_path = tmp_path / "referral-secret"
    referral_path.write_text("synthetic-referral", encoding="utf-8")
    return Settings(
        billing_checkout_enabled=True,
        public_base_url="https://rec.2brain.pro",
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret_path,
        billing_yookassa_webhook_secret_file=webhook_path,
        billing_referral_secret_file=referral_path,
        billing_support_email="billing@2brain.pro",
        billing_receipt_tax_system_code=2,
        billing_receipt_vat_code=1,
        credential_encryption_key_file=key_path,
        billing_provider_floor_minor=100,
    )


def _rows(
    tmp_path: Path,
) -> tuple[WorkspaceSubscription, BillingOperation, BillingInvoice, BillingPaymentMethod]:
    key_path = tmp_path / "billing-key"
    key = key_path.read_bytes()
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="personal",
        plan_code="personal",
        cycle="month",
        paid_through=PAID_THROUGH,
        recurring_allowed=True,
        recurring_authority_version=4,
    )
    operation = BillingOperation(
        id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key="renewal:period-1",
        state="scheduled",
        provider_key_expires_at=PAID_THROUGH + timedelta(hours=24),
        request_snapshot={
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
            "paid_through_at": PAID_THROUGH.isoformat(),
        },
    )
    invoice = BillingInvoice(
        workspace_id=WORKSPACE_ID,
        operation_id=OPERATION_ID,
        safe_number="INV-RNW-33333333333343338333",
        amount_minor=79_000,
        currency="RUB",
        status="pending",
        receipt_contact_snapshot="billing@example.test",
    )
    method = BillingPaymentMethod(
        workspace_id=WORKSPACE_ID,
        owner_user_id=OWNER_ID,
        encrypted_provider_ref=seal_provider_reference("pm-card-1", key),
        key_version="billing-v1",
        state="active",
        is_default=True,
        verified_at=datetime(2026, 8, 1, tzinfo=UTC),
    )
    return subscription, operation, invoice, method


def test_renewal_key_and_invoice_reference_are_stable_and_bounded() -> None:
    first = renewal_operation_key(workspace_id=WORKSPACE_ID, paid_through=PAID_THROUGH)
    second = renewal_operation_key(
        workspace_id=WORKSPACE_ID,
        paid_through=PAID_THROUGH.astimezone(UTC),
    )
    assert first == second
    assert len(first) < 240
    assert renewal_invoice_number(OPERATION_ID).startswith("INV-RNW-")
    assert frozenset({"scheduled"}) == RENEWAL_CANDIDATE_STATES


@pytest.mark.asyncio
async def test_planner_persists_approved_catalog_and_receipt_snapshot() -> None:
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="personal",
        plan_code="personal",
        cycle="month",
        paid_through=PAID_THROUGH,
        recurring_allowed=True,
        recurring_authority_version=4,
    )
    catalog = BillingPlanVersion(
        plan_code="personal",
        version=7,
        cycle="month",
        amount_minor=79_000,
        currency="RUB",
        storage_bytes=2_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v7"},
    )
    db = PlanningDb([subscription, None, catalog, UUID(int=1), "billing@2brain.pro", None])

    planned = await plan_due_renewals(db, now=datetime(2026, 8, 8, tzinfo=UTC))

    assert len(planned) == 1
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    invoice = next(row for row in db.added if isinstance(row, BillingInvoice))
    assert operation.request_snapshot["catalog_snapshot"] == {
        "plan_code": "personal",
        "catalog_version": 7,
        "cycle": "month",
        "amount_minor": 79_000,
        "currency": "RUB",
        "storage_bytes": 2_000_000_000,
        "processing_mode": "unlimited",
        "offer_version": "personal-v7",
        "policy_snapshot": {"offer_version": "personal-v7"},
    }
    assert invoice.receipt_contact_snapshot == "billing@2brain.pro"


@pytest.mark.asyncio
async def test_planner_skips_renewal_while_initial_checkout_is_unresolved() -> None:
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="personal",
        plan_code="personal",
        cycle="month",
        paid_through=PAID_THROUGH,
        recurring_allowed=True,
    )

    class BlockingPlanningDb(PlanningDb):
        blocker_query = None

        async def scalar(self, query: object) -> object:
            self.blocker_query = query
            return UUID(int=9)

    db = BlockingPlanningDb([subscription])

    assert await plan_due_renewals(db, now=datetime(2026, 8, 8, tzinfo=UTC)) == ()
    query = str(db.blocker_query.compile(compile_kwargs={"literal_binds": True}))
    assert "initial_checkout" in query
    assert not db.added


@pytest.mark.asyncio
async def test_planner_query_requires_active_personal_owner() -> None:
    class EmptyPlanningDb:
        query = None

        async def scalars(self, query):
            self.query = query
            return []

        async def flush(self):
            return None

    db = EmptyPlanningDb()

    assert await plan_due_renewals(db, now=datetime(2026, 8, 8, tzinfo=UTC)) == ()
    query = str(db.query)
    assert "JOIN workspace_memberships" in query
    assert "workspace_memberships.role" in query
    assert "workspace_memberships.status" in query
    assert "workspaces.kind" in query


@pytest.mark.asyncio
async def test_charge_candidate_query_requires_active_personal_owner() -> None:
    class Rows:
        def all(self):
            return []

    class EmptyCandidateDb:
        query = None

        async def execute(self, query):
            self.query = query
            return Rows()

    db = EmptyCandidateDb()

    assert await pending_renewal_charge_candidates(db, now=PAID_THROUGH) == ()
    query = str(db.query)
    assert "JOIN workspace_memberships" in query
    assert "workspace_memberships.role" in query
    assert "workspace_memberships.status" in query
    assert "workspaces.kind" in query


@pytest.mark.asyncio
async def test_cutoff_revokes_invalid_corporate_renewal_authority() -> None:
    subscription = WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="personal",
        plan_code="personal",
        cycle="month",
        paid_through=PAID_THROUGH,
        recurring_allowed=True,
        recurring_authority_version=2,
    )
    db = PlanningDb([subscription, None, None])
    db.workspace.kind = "corporate"

    projected = await project_renewal_cutoffs(db, now=PAID_THROUGH)

    assert projected == 1
    assert subscription.state == "free"
    assert subscription.plan_code == "free"
    assert subscription.recurring_allowed is False
    assert subscription.recurring_authority_version == 3
    assert subscription.renewal_resolution == "workspace_scope_invalid"


@pytest.mark.asyncio
async def test_charge_uses_saved_method_and_authority_snapshot(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    provider = FakeProvider({"id": "pay-renewal-1", "status": "pending"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "sent"
    assert result.provider_id == "pay-renewal-1"
    assert operation.state == "sent"
    assert operation.provider_id == "pay-renewal-1"
    assert provider.calls[0]["payment_method_id"] == "pm-card-1"
    assert provider.calls[0]["idempotence_key"] == "renewal:period-1"


@pytest.mark.asyncio
async def test_charge_rejects_non_personal_workspace_before_provider_call(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, _method = _rows(tmp_path)
    provider = FakeProvider({"id": "must-not-be-called"})
    db = FakeDb([subscription, operation, invoice])
    db.workspace.kind = "corporate"
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        db,
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "manual_resolution"
    assert provider.calls == []
    assert subscription.recurring_allowed is False
    assert subscription.recurring_authority_version == 5
    assert subscription.renewal_resolution == "workspace_scope_invalid"


@pytest.mark.asyncio
async def test_charge_rejects_revoked_owner_before_provider_call(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, _method = _rows(tmp_path)
    provider = FakeProvider({"id": "must-not-be-called"})
    db = FakeDb([subscription, operation, invoice])
    db.membership = None
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        db,
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "manual_resolution"
    assert provider.calls == []
    assert subscription.recurring_allowed is False
    assert subscription.recurring_authority_version == 5
    assert subscription.renewal_resolution == "workspace_scope_invalid"


@pytest.mark.asyncio
async def test_charge_rejects_stale_billing_actor_before_decrypt_or_provider(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    operation.request_snapshot["billing_actor_user_id"] = str(
        UUID("55555555-5555-4555-8555-555555555555")
    )
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.read_billing_encryption_key",
        lambda _path: (_ for _ in ()).throw(AssertionError("must reject before decrypt")),
    )
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "manual_resolution"
    assert operation.state == "manual_resolution"
    assert invoice.status == "manual_resolution"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_charge_rejects_boolean_authority_version_before_decrypt_or_provider(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    subscription.recurring_authority_version = 1
    operation.request_snapshot["recurring_authority_version"] = True
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.read_billing_encryption_key",
        lambda _path: (_ for _ in ()).throw(AssertionError("must reject before decrypt")),
    )
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "manual_resolution"
    assert operation.state == "manual_resolution"
    assert invoice.status == "manual_resolution"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_charge_waits_until_paid_through_boundary(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH - timedelta(hours=1),
    )

    assert result.status == "scheduled"
    assert operation.state == "scheduled"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_transport_unknown_never_retries_without_provider_id(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    provider = FakeProvider(httpx.ReadTimeout("timeout"))
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "unknown"
    assert operation.state == "unknown"
    assert operation.provider_id is None
    assert invoice.status == "unknown"


@pytest.mark.asyncio
async def test_confirmed_provider_decline_turns_authority_off(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    provider = FakeProvider(YooKassaProviderError("declined", status_code=402))
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=PAID_THROUGH,
    )

    assert result.status == "canceled"
    assert operation.state == "canceled"
    assert invoice.status == "canceled"
    assert subscription.recurring_allowed is False


@pytest.mark.asyncio
async def test_schedule_change_cancels_stale_operation_without_provider_call(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    subscription.paid_through = PAID_THROUGH + timedelta(days=3)
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=datetime(2026, 8, 8, tzinfo=UTC),
    )

    assert result.status == "canceled"
    assert operation.state == "canceled"
    assert provider.calls == []
