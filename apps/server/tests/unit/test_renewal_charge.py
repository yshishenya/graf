from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import httpx
import pytest
from cryptography.fernet import Fernet

from twobrain_rec_server.billing.payment_methods import seal_provider_reference
from twobrain_rec_server.billing.renewal_charge import (
    RENEWAL_ATTEMPT_COUNT,
    RENEWAL_CANDIDATE_STATES,
    RENEWAL_PROVIDER_WINDOW,
    charge_renewal_operation,
    pending_renewal_charge_candidates,
    plan_due_renewals,
    project_renewal_cutoffs,
    record_renewal_decline,
    renewal_attempt_due_at,
    renewal_invoice_number,
    renewal_operation_key,
)
from twobrain_rec_server.billing.yookassa import YooKassaProviderError
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingAcceptanceBudget,
    BillingAuditEvent,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    BillingStorageEntitlementGrant,
    TimeCreditLedgerEntry,
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

    async def scalars(self, query):
        # The dispatch revalidates the current catalog before a first POST.
        return [_planning_catalog()]

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def scalar(self, _query: object) -> object:
        descriptions = getattr(_query, "column_descriptions", ())
        if (
            descriptions
            and descriptions[0].get("entity") is BillingInvoice
            and "JOIN billing_entitlement_grants" in str(_query)
        ):
            return None
        if descriptions and descriptions[0].get("entity") in {
            BillingAcceptanceBudget,
            BillingStorageEntitlementGrant,
            TimeCreditLedgerEntry,
        }:
            return None
        if descriptions and descriptions[0].get("entity") is WorkspaceMembership:
            return self.membership
        return next(self._values)

    async def get(self, model: object, _key: object) -> object | None:
        return self.workspace if model is Workspace else None

    async def refresh(self, _row, **_kwargs) -> None:
        return None

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
        if _query.column_descriptions[0].get("entity") is BillingOperation:
            return []
        self.subscription = next(self._values)
        return [self.subscription]  # type: ignore[return-value]

    async def scalar(self, query):
        if (query.column_descriptions[0].get("entity") is WorkspaceSubscription
                and hasattr(self, "subscription")):
            return self.subscription
        return await super().scalar(query)


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
    *,
    attempt: int = RENEWAL_ATTEMPT_COUNT,
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
        provider_key_expires_at=renewal_attempt_due_at(
            paid_through=PAID_THROUGH,
            attempt=attempt,
        )
        + RENEWAL_PROVIDER_WINDOW,
        request_snapshot={
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
            "paid_through_at": PAID_THROUGH.isoformat(),
            "renewal_attempt": attempt,
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
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price

    catalog = validate_plan_version(_planning_catalog()).as_dict()
    accept_base_price(subscription, catalog)
    operation.request_snapshot = {**operation.request_snapshot, "catalog_snapshot": catalog}
    return subscription, operation, invoice, method


def _attempt_charge_moment(attempt: int) -> datetime:
    """One hour after the attempt starts, still inside its provider window."""
    return renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt) + timedelta(hours=1)


def _planning_subscription() -> WorkspaceSubscription:
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

    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price

    accept_base_price(subscription, validate_plan_version(_planning_catalog()).as_dict())
    return subscription


def _planning_catalog() -> BillingPlanVersion:
    return BillingPlanVersion(
        plan_code="personal",
        version=7,
        cycle="month",
        amount_minor=79_000,
        currency="RUB",
        storage_bytes=5_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v7"},
    )


def _stored_attempt(
    *,
    attempt: int,
    state: str,
    provider_id: str | None = None,
    key_expires_at: datetime | None = None,
) -> BillingOperation:
    return BillingOperation(
        id=UUID(int=100 + attempt),
        workspace_id=WORKSPACE_ID,
        kind="renewal",
        idempotency_key=renewal_operation_key(
            workspace_id=WORKSPACE_ID,
            paid_through=PAID_THROUGH,
            attempt=attempt,
        ),
        state=state,
        provider_id=provider_id,
        provider_key_expires_at=key_expires_at
        or (
            renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt)
            + RENEWAL_PROVIDER_WINDOW
        ),
        request_snapshot={
            "cycle": "month",
            "billing_actor_user_id": str(OWNER_ID),
            "recurring_authority_version": 4,
            "paid_through_at": PAID_THROUGH.isoformat(),
            "renewal_attempt": attempt,
        },
    )


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


def test_renewal_attempts_land_72_48_and_24_hours_before_the_boundary() -> None:
    assert RENEWAL_ATTEMPT_COUNT == 3
    assert [
        renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt) for attempt in (1, 2, 3)
    ] == [
        PAID_THROUGH - timedelta(hours=72),
        PAID_THROUGH - timedelta(hours=48),
        PAID_THROUGH - timedelta(hours=24),
    ]
    # A late-planned attempt is already due instead of waiting for a future
    # moment: nothing inside the reminder window is ever postponed.
    late_attempt = renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=1)
    assert late_attempt < PAID_THROUGH - timedelta(hours=1)
    with pytest.raises(ValueError):
        renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=4)


def test_every_attempt_has_its_own_key_over_the_same_period() -> None:
    keys = [
        renewal_operation_key(
            workspace_id=WORKSPACE_ID,
            paid_through=PAID_THROUGH,
            attempt=attempt,
        )
        for attempt in (1, 2, 3)
    ]
    period = renewal_operation_key(
        workspace_id=WORKSPACE_ID,
        paid_through=PAID_THROUGH,
    ).rsplit(":", 1)[0]

    assert len(set(keys)) == 3
    # The period reference is identical for every attempt and depends only on
    # the workspace and the paid period, so replanning one attempt is
    # idempotent while the three attempts stay three separate payments.
    assert {key.rsplit(":", 1)[0] for key in keys} == {period}
    assert period.startswith("renewal:")
    assert [key.rsplit(":", 1)[1] for key in keys] == ["a1", "a2", "a3"]
    with pytest.raises(ValueError):
        renewal_operation_key(workspace_id=WORKSPACE_ID, paid_through=PAID_THROUGH, attempt=0)


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
        storage_bytes=5_000_000_000,
        processing_mode="unlimited",
        enabled_for_checkout=True,
        policy_snapshot={"offer_version": "personal-v7"},
    )
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price

    accept_base_price(subscription, validate_plan_version(catalog).as_dict())
    db = PlanningDb([subscription, None, catalog, UUID(int=1), "billing@2brain.pro", None, None])

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
        "storage_bytes": 5_000_000_000,
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
async def test_planner_skips_old_windows_and_opens_only_the_current_attempt() -> None:
    late = PAID_THROUGH - timedelta(hours=2)
    db = PlanningDb(
        [
            _planning_subscription(),
            None,
            _planning_catalog(),
            UUID(int=1),
            "billing@2brain.pro",
            None,
            None,
            None,
        ]
    )

    # The subscription enters the reminder window two hours before its period
    # ends: only the third window remains. Earlier windows must never be charged.
    planned = await plan_due_renewals(db, now=late)

    assert len(planned) == 1
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    assert operation.request_snapshot["renewal_attempt"] == 3
    assert operation.idempotency_key.endswith(":a3")
    assert operation.provider_key_expires_at == PAID_THROUGH
    assert operation.provider_key_expires_at > late
    invoice = next(row for row in db.added if isinstance(row, BillingInvoice))
    assert invoice.plan_snapshot["renewal_attempt"] == 3
    assert invoice.operation_id == operation.id


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_id", [None, "pay-attempt-1"])
async def test_planner_waits_for_the_next_attempt_moment(provider_id: str | None) -> None:
    resolved_first = _stored_attempt(attempt=1, state="canceled", provider_id=provider_id)
    subscription = _planning_subscription()
    common = [subscription, None, _planning_catalog(), UUID(int=1), "billing@2brain.pro"]

    too_early = PlanningDb([*common, resolved_first])
    assert (await plan_due_renewals(too_early, now=PAID_THROUGH - timedelta(hours=50))) == ()
    assert not [row for row in too_early.added if isinstance(row, BillingOperation)]

    on_time = PlanningDb([*common, resolved_first, None])
    planned = await plan_due_renewals(on_time, now=PAID_THROUGH - timedelta(hours=48))

    assert len(planned) == 1
    second = next(row for row in on_time.added if isinstance(row, BillingOperation))
    assert second.request_snapshot["renewal_attempt"] == 2
    assert second.idempotency_key.endswith(":a2")
    # An attempt planned exactly on its moment reserves exactly one window.
    assert second.provider_key_expires_at == PAID_THROUGH - timedelta(hours=24)
    repeated = PlanningDb([*common, resolved_first, second])
    assert await plan_due_renewals(repeated, now=PAID_THROUGH - timedelta(hours=47)) == (second.id,)
    assert repeated.added == []

    # The last attempt never reaches past the paid-through boundary.
    last = PlanningDb(
        [
            *common,
            resolved_first,
            _stored_attempt(attempt=2, state="canceled", provider_id=provider_id),
            None,
        ]
    )
    assert len(await plan_due_renewals(last, now=PAID_THROUGH - timedelta(hours=24))) == 1
    third = next(row for row in last.added if isinstance(row, BillingOperation))
    assert third.request_snapshot["renewal_attempt"] == 3
    assert third.provider_key_expires_at == PAID_THROUGH
    exhausted = PlanningDb(
        [
            *common,
            resolved_first,
            _stored_attempt(attempt=2, state="canceled", provider_id=provider_id),
            _stored_attempt(attempt=3, state="canceled", provider_id=provider_id),
        ]
    )
    assert await plan_due_renewals(exhausted, now=PAID_THROUGH - timedelta(hours=1)) == ()
    assert exhausted.added == []


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "provider_id"),
    [
        (state, provider_id)
        for state in (
            "unknown",
            "processing",
            "sent",
            "provider_key_expired",
            "manual_resolution",
            "reconciliation_gap",
            "succeeded",
            "succeeded_refused",
        )
        for provider_id in (None, "pay-attempt-1")
    ],
)
async def test_planner_never_starts_a_second_key_while_one_attempt_is_unresolved(
    state: str, provider_id: str | None
) -> None:
    unresolved = _stored_attempt(attempt=1, state=state, provider_id=provider_id)

    for now in (PAID_THROUGH - timedelta(hours=50), PAID_THROUGH - timedelta(hours=24)):
        db = PlanningDb(
            [
                _planning_subscription(),
                None,
                _planning_catalog(),
                UUID(int=1),
                "billing@2brain.pro",
                unresolved,
                None,
            ]
        )

        assert await plan_due_renewals(db, now=now) == ()
        assert not [row for row in db.added if isinstance(row, BillingOperation)]


@pytest.mark.asyncio
async def test_planner_reuses_the_stored_attempt_instead_of_a_second_payment() -> None:
    subscription = _planning_subscription()
    stored = _stored_attempt(attempt=1, state="scheduled")

    db = PlanningDb(
        [subscription, None, _planning_catalog(), UUID(int=1), "billing@2brain.pro", stored]
    )

    planned = await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=70))

    assert planned == (stored.id,)
    assert not [row for row in db.added if isinstance(row, BillingOperation)]


@pytest.mark.asyncio
async def test_planner_does_not_create_a_new_charge_after_expired_unknown_attempt() -> None:
    subscription = _planning_subscription()
    expired = _stored_attempt(
        attempt=1,
        state="provider_key_expired",
        provider_id=None,
        key_expires_at=PAID_THROUGH - timedelta(hours=70),
    )
    db = PlanningDb(
        [
            subscription,
            None,
            _planning_catalog(),
            UUID(int=1),
            "billing@2brain.pro",
            expired,
            None,
        ]
    )

    # The same unresolved idempotency key remains the only safe identity. A
    # later attempt must not silently create a second charge after cutoff.
    assert await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=47)) == ()
    assert not [row for row in db.added if isinstance(row, BillingOperation)]


@pytest.mark.asyncio
async def test_planner_takes_over_after_a_spent_provider_window() -> None:
    subscription = _planning_subscription()
    spent = _stored_attempt(
        attempt=1,
        state="scheduled",
        key_expires_at=PAID_THROUGH - timedelta(hours=70),
    )

    db = PlanningDb(
        [
            subscription,
            None,
            _planning_catalog(),
            UUID(int=1),
            "billing@2brain.pro",
            spent,
            None,
        ]
    )

    planned = await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=47))

    assert len(planned) == 1
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    assert operation.request_snapshot["renewal_attempt"] == 2


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
async def test_candidate_query_uses_the_moment_of_each_attempt() -> None:
    class Rows:
        def __init__(self, values):
            self._values = values

        def all(self):
            return self._values

    class CandidateDb:
        def __init__(self, operation: BillingOperation) -> None:
            self._operation = operation

        async def execute(self, _query):
            return Rows([(self._operation.id, self._operation.workspace_id)])

        async def get(self, _model, _key):
            return self._operation

    for attempt in (1, 2, 3):
        operation = _stored_attempt(attempt=attempt, state="scheduled")
        db = CandidateDb(operation)
        due_at = renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt)

        assert await pending_renewal_charge_candidates(db, now=due_at - timedelta(minutes=1)) == ()
        assert await pending_renewal_charge_candidates(db, now=due_at) == (
            (operation.id, operation.workspace_id),
        )


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
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
    provider = FakeProvider({"id": "pay-renewal-1", "status": "pending"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    # The first attempt is charged as soon as its own moment has passed, even
    # when the subscription entered the reminder window late.
    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(1),
    )

    assert result.status == "sent"
    assert invoice.plan_snapshot["purchase_schema"] == 2
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
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
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
        now=_attempt_charge_moment(1),
    )

    assert result.status == "manual_resolution"
    assert operation.state == "manual_resolution"
    assert invoice.status == "manual_resolution"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_charge_waits_for_its_own_attempt_moment(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    # One hour before the first attempt is due, nothing is charged.
    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=1) - timedelta(hours=1),
    )

    assert result.status == "scheduled"
    assert operation.state == "scheduled"
    assert provider.calls == []


@pytest.mark.asyncio
async def test_missing_saved_method_resolves_attempt_and_allows_next_window(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, _method = _rows(tmp_path, attempt=1)
    provider = FakeProvider({"id": "must-not-be-called"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    db = FakeDb([subscription, operation, invoice, None, None])
    result = await charge_renewal_operation(
        db,
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(1),
    )

    assert result.status == "canceled"
    assert operation.state == invoice.status == "canceled"
    assert subscription.recurring_allowed is True
    assert subscription.renewal_resolution == "attempt_failed"
    delivery = next(row for row in db.added if isinstance(row, BillingNotificationDelivery))
    assert delivery.template_key == "renewal_attempt_failed"
    audit = next(row for row in db.added if isinstance(row, BillingAuditEvent))
    assert audit.reason_code == "saved_method_missing"
    assert provider.calls == []

    planning_db = PlanningDb(
        [
            subscription,
            None,
            _planning_catalog(),
            UUID(int=1),
            "billing@2brain.pro",
            operation,
            None,
        ]
    )
    planned = await plan_due_renewals(
        planning_db,
        now=PAID_THROUGH - timedelta(hours=48),
    )
    assert len(planned) == 1
    next_operation = next(row for row in planning_db.added if isinstance(row, BillingOperation))
    assert next_operation.request_snapshot["renewal_attempt"] == 2


@pytest.mark.asyncio
async def test_transport_unknown_never_retries_without_provider_id(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
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
        now=_attempt_charge_moment(1),
    )

    assert result.status == "unknown"
    assert operation.state == "unknown"
    assert operation.provider_id is None
    assert invoice.status == "unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("attempt", [1, 2, 3])
async def test_rate_limit_retries_same_attempt_and_key_without_decline_notice(
    monkeypatch, tmp_path: Path, attempt: int
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=attempt)
    provider = FakeProvider(YooKassaProviderError("rate limited", status_code=429))
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient", lambda _: provider
    )
    original_key = operation.idempotency_key
    original_deadline = operation.provider_key_expires_at
    for _ in range(2):
        db = FakeDb([subscription, operation, invoice, method, None])
        result = await charge_renewal_operation(
            db,
            settings,
            operation_id=OPERATION_ID,
            workspace_id=WORKSPACE_ID,
            now=_attempt_charge_moment(attempt),
        )
        assert result.status == operation.state == "scheduled"
        assert operation.provider_id is None and invoice.status == "pending"
        assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
        assert subscription.paid_through == PAID_THROUGH
        assert operation.idempotency_key == original_key
        assert operation.provider_key_expires_at == original_deadline
        assert not any(isinstance(row, BillingNotificationDelivery) for row in db.added)
    assert len(provider.calls) == 2
    assert {call["idempotence_key"] for call in provider.calls} == {original_key}
    # The existing provider-key deadline bounds even repeated rate limiting.
    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=original_deadline,
    )
    assert result.status == "canceled"
    assert len(provider.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize("attempt", [1, 2])
async def test_declined_attempt_before_the_last_one_keeps_recurring_authority(
    monkeypatch, tmp_path: Path, attempt: int
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=attempt)
    provider = FakeProvider(_canceled_payment())
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    db = FakeDb([subscription, operation, invoice, method, None])
    result = await charge_renewal_operation(
        db,
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(attempt),
    )

    assert result.status == "canceled"
    assert operation.state == "canceled"
    assert invoice.status == "canceled"
    # Access and the saved card stay armed until the last attempt and the
    # paid-through boundary.
    assert subscription.recurring_allowed is True
    assert subscription.recurring_authority_version == 4
    assert subscription.renewal_resolution == "attempt_failed"
    assert (subscription.plan_code, subscription.state) == ("personal", "personal")
    delivery = next(row for row in db.added if isinstance(row, BillingNotificationDelivery))
    assert delivery.template_key == "renewal_attempt_failed"
    assert delivery.safe_payload["access_until"] == "10.08.2026 03:00"
    assert delivery.safe_payload["invoice"] == invoice.safe_number


@pytest.mark.asyncio
async def test_confirmed_provider_decline_of_the_last_attempt_turns_authority_off(
    monkeypatch, tmp_path: Path
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=3)
    provider = FakeProvider(_canceled_payment())
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: provider,
    )

    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method, None]),
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(3),
    )

    assert result.status == "canceled"
    assert operation.state == "canceled"
    assert invoice.status == "canceled"
    assert subscription.recurring_allowed is False
    assert subscription.recurring_authority_version == 5
    assert subscription.renewal_resolution == "canceled"
    # The paid period is still running, so access continues to its own boundary.
    assert (subscription.plan_code, subscription.state) == ("personal", "personal")


def _canceled_payment() -> dict[str, object]:
    return {
        "id": "pay-renewal-1",
        "status": "canceled",
        "test": False,
        "recipient": {"account_id": "shop-1"},
        "amount": {"value": "790.00", "currency": "RUB"},
        "metadata": {
            "workspace_id": str(WORKSPACE_ID),
            "operation_id": str(OPERATION_ID),
            "invoice_number": "INV-RNW-33333333333343338333",
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_field", ["metadata", "amount"])
async def test_unbound_canceled_response_stays_unknown_without_next_attempt_or_notice(
    monkeypatch, tmp_path: Path, bad_field: str
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
    payment = _canceled_payment()
    payment[bad_field] = {}
    provider = FakeProvider(payment)
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient", lambda _: provider
    )
    db = FakeDb([subscription, operation, invoice, method])
    result = await charge_renewal_operation(
        db,
        settings,
        operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(1),
    )
    assert result.status == operation.state == invoice.status == "unknown"
    assert operation.provider_id == payment["id"]
    assert subscription.recurring_allowed is True
    assert subscription.recurring_authority_version == 4
    assert not any(isinstance(row, BillingNotificationDelivery) for row in db.added)


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


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "drift",
    ["none", "period", "owner", "authority", "succeeded", "succeeded_refused", "invoice_succeeded"],
)
async def test_late_decline_never_changes_new_authority_or_success(
    tmp_path: Path, drift: str
) -> None:
    _settings(tmp_path)
    subscription, operation, invoice, _ = _rows(tmp_path, attempt=3)
    operation.state = "sent"
    operation.provider_id = "pay-renewal-1"
    subscription.renewal_resolution = "previous"
    if drift == "period":
        subscription.paid_through += timedelta(days=30)
    elif drift == "owner":
        subscription.billing_owner_id = UUID(int=9)
    elif drift == "authority":
        subscription.recurring_authority_version += 1
    elif drift in {"succeeded", "succeeded_refused"}:
        operation.state = drift
        invoice.status = "succeeded"
    elif drift == "invoice_succeeded":
        invoice.status = "succeeded"
    original_state = operation.state
    original_invoice = invoice.status
    version = subscription.recurring_authority_version
    paid_through = subscription.paid_through
    db = FakeDb([None])
    for _ in range(2):
        await record_renewal_decline(
            db,
            subscription=subscription,
            operation=operation,
            invoice=invoice,
            now=PAID_THROUGH + timedelta(seconds=1),
        )
    assert subscription.paid_through == paid_through
    notices = [row for row in db.added if isinstance(row, BillingNotificationDelivery)]
    if drift == "none":
        assert operation.state == invoice.status == "canceled"
        assert subscription.recurring_allowed is False
        assert subscription.recurring_authority_version == version + 1
        assert subscription.plan_code == "free"
        assert len(notices) == 1
    else:
        assert subscription.recurring_allowed is True
        assert subscription.recurring_authority_version == version
        assert subscription.renewal_resolution == "previous"
        assert subscription.plan_code == "personal"
        assert notices == []
        if "succeeded" in drift:
            assert (operation.state, invoice.status) == (original_state, original_invoice)
        else:
            assert operation.state == invoice.status == "canceled"


@pytest.mark.asyncio
async def test_base_price_change_requires_fresh_confirmation_before_planning():
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price

    subscription = _planning_subscription()
    catalog = _planning_catalog()
    accept_base_price(subscription, validate_plan_version(catalog).as_dict())
    catalog.amount_minor += 1000
    db = PlanningDb([subscription, None, catalog])
    assert await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=48)) == ()
    assert subscription.renewal_resolution == "price_changed"
    assert db.added == []


@pytest.mark.asyncio
async def test_last_window_resume_after_unsent_cancel_has_one_fresh_authority_operation():
    subscription = _planning_subscription()
    subscription.recurring_authority_version = 6
    canceled = _stored_attempt(attempt=3, state="canceled")
    canceled.request_snapshot = {
        **canceled.request_snapshot,
        "cancel_reason": "authority_cancelled",
    }
    db = PlanningDb(
        [
            subscription,
            None,
            _planning_catalog(),
            UUID(int=1),
            "billing@2brain.pro",
            None,
            None,
            canceled,
            None,
        ]
    )
    # First two windows are missed, the last one was canceled before POST.
    result = await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=12))
    assert len(result) == 1
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    assert operation.request_snapshot["renewal_attempt"] == 3
    assert operation.request_snapshot["recurring_authority_version"] == 6
    assert operation.idempotency_key.endswith(":authority:6")
    assert canceled.state == "canceled" and canceled.provider_id is None


@pytest.mark.asyncio
async def test_changed_base_price_after_planning_never_reaches_provider(monkeypatch, tmp_path):
    from twobrain_rec_server.billing.catalog import validate_plan_version

    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path)
    provider = FakeProvider({"id": "must-not-be-created"})
    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient", lambda settings: provider
    )

    async def changed_catalog(db, *, cycle, now):
        catalog = _planning_catalog()
        catalog.amount_minor += 1000
        return validate_plan_version(catalog, now=now)

    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge._approved_catalog", changed_catalog
    )
    result = await charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]),
        settings,
        operation_id=operation.id,
        workspace_id=WORKSPACE_ID,
        now=_attempt_charge_moment(3),
    )
    assert result.status == "canceled"
    assert subscription.renewal_resolution == "price_changed"
    assert not provider.calls

    from twobrain_rec_server.billing.purchases import accept_base_price
    accepted = await changed_catalog(None, cycle="month", now=_attempt_charge_moment(3))
    accept_base_price(subscription, accepted.as_dict())
    planning = PlanningDb([subscription, None, method, "billing@example.test",
                           None, None, operation, None])
    assert len(await plan_due_renewals(planning, now=_attempt_charge_moment(3))) == 1
    fresh = next(row for row in planning.added if isinstance(row, BillingOperation))
    fresh_invoice = next(row for row in planning.added if isinstance(row, BillingInvoice))
    provider.response = {"id": "payment-after-new-consent", "status": "pending"}
    result = await charge_renewal_operation(FakeDb([subscription, fresh, fresh_invoice, method]),
        settings, operation_id=fresh.id, workspace_id=WORKSPACE_ID, now=_attempt_charge_moment(3))
    assert result.status == "sent" and len(provider.calls) == 1
    assert fresh.id != operation.id and fresh_invoice.amount_minor == accepted.amount_minor
    assert subscription.recurring_authority_version == 4


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["budget", "provider_setup", "secret_io"])
async def test_unsent_renewal_refusal_preserves_method_and_bank_attempt(monkeypatch, tmp_path, cause):
    from twobrain_rec_server.billing import renewal_charge as renewal
    from twobrain_rec_server.billing.purchases import PurchaseError
    from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=3)
    provider = FakeProvider({"id": "must-not-send"})
    settlements = []

    async def reserve(*args, **kwargs):
        if cause == "budget":
            raise PurchaseError("Проверочное окно оплаты закрыто")

    async def settle(*args, **kwargs):
        settlements.append(kwargs["succeeded"])

    def construct(_settings):
        if cause == "provider_setup":
            raise YooKassaConfigurationError("synthetic setup failure")
        if cause == "secret_io":
            raise PermissionError("synthetic secret unavailable")
        return provider

    monkeypatch.setattr(renewal, "reserve_acceptance_budget", reserve)
    monkeypatch.setattr(renewal, "settle_acceptance_budget", settle)
    monkeypatch.setattr(renewal, "YooKassaClient", construct)
    db = FakeDb([subscription, operation, invoice, method])
    result = await charge_renewal_operation(db, settings, operation_id=OPERATION_ID,
        workspace_id=WORKSPACE_ID, now=_attempt_charge_moment(3))
    assert result.status == operation.state == invoice.status == "canceled"
    assert renewal.renewal_canceled_without_payment(operation)
    assert subscription.renewal_resolution == (
        "acceptance_budget" if cause == "budget" else "provider_unavailable")
    assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
    assert provider.calls == []
    assert settlements == [False]
    assert not any(isinstance(row, BillingNotificationDelivery) for row in db.added)


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["budget", "provider_setup", "provider_request"])
async def test_two_local_renewal_failures_recover_in_last_window_without_new_consent(
    monkeypatch, tmp_path, cause
):
    from twobrain_rec_server.billing import renewal_charge as renewal
    from twobrain_rec_server.billing.purchases import PurchaseError
    from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError
    settings = _settings(tmp_path)
    subscription, root_operation, invoice, method = _rows(tmp_path, attempt=3)
    provider = FakeProvider({"id": "payment-after-recovery", "status": "pending"})
    preparation = 0

    async def reserve(*args, **kwargs):
        nonlocal preparation
        preparation += 1
        if cause == "budget" and preparation <= 2:
            raise PurchaseError("Проверочное окно оплаты закрыто")

    async def settle(*args, **kwargs):
        return None

    def construct(_settings):
        if cause == "provider_setup" and preparation <= 2:
            raise YooKassaConfigurationError("synthetic setup unavailable")
        if cause == "provider_request":
            provider.response = (YooKassaProviderError("synthetic authentication failure", status_code=401)
                if preparation <= 2 else {"id": "payment-after-recovery", "status": "pending"})
        return provider

    monkeypatch.setattr(renewal, "reserve_acceptance_budget", reserve)
    monkeypatch.setattr(renewal, "settle_acceptance_budget", settle)
    monkeypatch.setattr(renewal, "YooKassaClient", construct)
    current = PAID_THROUGH - timedelta(hours=12)
    operation = root_operation
    previous = []
    for index in range(3):
        result = await charge_renewal_operation(
            FakeDb([subscription, operation, invoice, method]), settings,
            operation_id=operation.id, workspace_id=WORKSPACE_ID, now=current,
        )
        if index == 2:
            assert result.status == "sent"
            break
        assert result.status == "canceled"
        previous.append(operation)
        planning = PlanningDb([
            subscription, None, _planning_catalog(), method, "billing@example.test",
            None, None, root_operation,
            operation if index else None,
        ])
        planned = await plan_due_renewals(planning, now=current)
        assert len(planned) == 1
        operation = next(row for row in planning.added if isinstance(row, BillingOperation))
        invoice = next(row for row in planning.added if isinstance(row, BillingInvoice))
    assert len(provider.calls) == (3 if cause == "provider_request" else 1)
    assert len({row.id for row in [*previous, operation]}) == 3
    assert all(row.state == "canceled" and row.provider_id is None for row in previous)
    assert subscription.recurring_authority_version == 4 and subscription.recurring_allowed


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["unknown", "sent", "processing", "succeeded"])
@pytest.mark.parametrize("reason", ["provider_unavailable", "price_changed", "provider_request_rejected"])
async def test_local_retry_never_ignores_a_later_dispatched_successor(state, reason):
    root = _stored_attempt(attempt=3, state="canceled")
    root.request_snapshot = {**root.request_snapshot, "cancel_reason": reason}
    latest = _stored_attempt(attempt=3, state=state)
    db = PlanningDb([
        _planning_subscription(), None, _planning_catalog(), UUID(int=1), "billing@example.test",
        None, None, root, latest,
    ])
    assert await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=12)) == ()
    assert not any(isinstance(row, BillingOperation) for row in db.added)


@pytest.mark.asyncio
@pytest.mark.parametrize("state", ["unknown", "sent", "processing", "succeeded"])
@pytest.mark.parametrize("reason", ["provider_unavailable", "price_changed", "provider_request_rejected"])
async def test_local_retry_from_previous_window_blocks_next_bank_attempt(state, reason):
    root = _stored_attempt(attempt=1, state="canceled")
    root.request_snapshot = {**root.request_snapshot, "cancel_reason": reason}
    latest = _stored_attempt(attempt=1, state=state)
    class WindowDb(PlanningDb):
        async def scalar(self, query):
            descriptions = getattr(query, "column_descriptions", ())
            params = query.compile().params
            if (descriptions and descriptions[0].get("entity") is BillingOperation
                    and "idempotency_key_1" in params):
                if "LIKE" in str(query):
                    return latest
                key = params["idempotency_key_1"]
                return root if key.endswith(":a1") else None
            return await super().scalar(query)

    db = WindowDb([
        _planning_subscription(), None, _planning_catalog(), UUID(int=1), "billing@example.test",
    ])
    assert await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=40)) == ()
    assert not any(isinstance(row, BillingOperation) for row in db.added)


@pytest.mark.asyncio
async def test_planner_pages_past_unaccepted_prices_without_consuming_action_limit():
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price

    subscriptions = [_planning_subscription() for _ in range(3)]
    for number, subscription in enumerate(subscriptions, 1):
        subscription.workspace_id = UUID(int=number)
    for subscription in subscriptions[:2]:
        subscription.storage_price_consents = {}

    class PagedDb(FakeDb):
        def __init__(self):
            super().__init__([])
            self.pages = 0

        async def scalars(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                return []
            if entity is BillingPlanVersion:
                return [_planning_catalog()]
            assert entity is WorkspaceSubscription
            params = query.compile().params
            assert 1 in params.values()  # bounded fetch page
            if self.pages:
                assert "(workspace_subscriptions.paid_through, workspace_subscriptions.workspace_id) >" in str(query)
                assert UUID(int=self.pages) in params.values()
            result = subscriptions[self.pages:self.pages + 1]
            self.pages += 1
            return result

        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingPlanVersion:
                return _planning_catalog()
            if entity is BillingPaymentMethod:
                return UUID(int=10)
            if entity is BillingInvoice:
                return None if "JOIN billing_entitlement_grants" in str(query) else "billing@example.test"
            return None

    db = PagedDb()
    result = await plan_due_renewals(db, now=PAID_THROUGH - timedelta(hours=70), limit=1)
    assert len(result) == 1 and db.pages == 3
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    assert operation.workspace_id == subscriptions[2].workspace_id
    assert all(row.renewal_resolution == "price_changed" for row in subscriptions[:2])

    # A later explicit acceptance makes a previously skipped row eligible again.
    accept_base_price(subscriptions[0], validate_plan_version(_planning_catalog()).as_dict())
    resumed = PagedDb()
    assert len(await plan_due_renewals(resumed, now=PAID_THROUGH - timedelta(hours=70), limit=1)) == 1
    assert resumed.pages == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("attempt", [1, 3])
@pytest.mark.parametrize("status", [400, 401, 403, 404, 405, 415])
async def test_rejected_merchant_request_never_spends_card_attempt_or_revokes_mandate(
    monkeypatch, tmp_path, attempt, status
):
    from twobrain_rec_server.billing import renewal_charge as renewal
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=attempt)
    provider = FakeProvider(YooKassaProviderError("synthetic merchant request failure", status_code=status))
    settlements = []

    async def settle(*args, **kwargs):
        settlements.append(kwargs["succeeded"])

    monkeypatch.setattr(renewal, "YooKassaClient", lambda _: provider)
    monkeypatch.setattr(renewal, "settle_acceptance_budget", settle)
    db = FakeDb([subscription, operation, invoice, method])
    result = await charge_renewal_operation(db, settings, operation_id=operation.id,
        workspace_id=WORKSPACE_ID, now=_attempt_charge_moment(attempt))
    assert result.status == invoice.status == operation.state == "canceled"
    assert operation.request_snapshot["cancel_reason"] == "provider_request_rejected"
    assert renewal.renewal_canceled_without_payment(operation)
    assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
    assert method.state == "active" and method.is_default
    assert settlements == [False]
    assert not any(isinstance(row, BillingNotificationDelivery) for row in db.added)


@pytest.mark.asyncio
async def test_last_window_price_change_requires_new_consent_then_uses_new_operation():
    from twobrain_rec_server.billing.catalog import validate_plan_version
    from twobrain_rec_server.billing.purchases import accept_base_price
    subscription = _planning_subscription()
    canceled = _stored_attempt(attempt=3, state="canceled")
    canceled.request_snapshot = {**canceled.request_snapshot, "cancel_reason": "price_changed"}
    subscription.storage_price_consents = {}
    now = PAID_THROUGH - timedelta(hours=12)
    assert await plan_due_renewals(PlanningDb([subscription, None, _planning_catalog()]), now=now) == ()
    accept_base_price(subscription, validate_plan_version(_planning_catalog()).as_dict())
    db = PlanningDb([subscription, None, _planning_catalog(), UUID(int=1),
        "billing@example.test", None, None, canceled, None])
    assert len(await plan_due_renewals(db, now=now)) == 1
    fresh = next(row for row in db.added if isinstance(row, BillingOperation))
    assert fresh.id != canceled.id and fresh.idempotency_key.endswith(f":retry:{canceled.id}")
    assert fresh.request_snapshot["renewal_attempt"] == 3
    assert canceled.state == "canceled" and subscription.recurring_allowed


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [402, 408, 409, 422, 500])
async def test_ambiguous_request_status_keeps_unknown_payment_reserved(monkeypatch, tmp_path, status):
    from twobrain_rec_server.billing import renewal_charge as renewal
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=3)
    provider = FakeProvider(YooKassaProviderError("synthetic ambiguous response", status_code=status))
    settlements = []

    async def settle(*args, **kwargs):
        settlements.append(kwargs)

    monkeypatch.setattr(renewal, "YooKassaClient", lambda _: provider)
    monkeypatch.setattr(renewal, "settle_acceptance_budget", settle)
    db = FakeDb([subscription, operation, invoice, method])
    result = await charge_renewal_operation(db, settings, operation_id=operation.id,
        workspace_id=WORKSPACE_ID, now=_attempt_charge_moment(3))
    assert result.status == operation.state == invoice.status == "unknown"
    assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
    assert settlements == []
    assert not any(isinstance(row, BillingNotificationDelivery) for row in db.added)
