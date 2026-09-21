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
    renewal_attempt_due_at,
    renewal_invoice_number,
    renewal_operation_key,
)
from twobrain_rec_server.billing.yookassa import YooKassaProviderError
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingNotificationDelivery,
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
    return subscription, operation, invoice, method


def _attempt_charge_moment(attempt: int) -> datetime:
    """One hour after the attempt starts, still inside its provider window."""
    return renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt) + timedelta(hours=1)


def _planning_subscription() -> WorkspaceSubscription:
    return WorkspaceSubscription(
        workspace_id=WORKSPACE_ID,
        billing_owner_id=OWNER_ID,
        state="personal",
        plan_code="personal",
        cycle="month",
        paid_through=PAID_THROUGH,
        recurring_allowed=True,
        recurring_authority_version=4,
    )


def _planning_catalog() -> BillingPlanVersion:
    return BillingPlanVersion(
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
        renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=attempt)
        for attempt in (1, 2, 3)
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
async def test_planner_opens_the_first_attempt_at_once_for_a_late_window() -> None:
    late = PAID_THROUGH - timedelta(hours=2)
    db = PlanningDb(
        [_planning_subscription(), None, _planning_catalog(), UUID(int=1), "billing@2brain.pro", None]
    )

    # The subscription enters the reminder window two hours before its period
    # ends: the first attempt moment is already in the past and its provider
    # window opens now instead of being over before the first charge.
    planned = await plan_due_renewals(db, now=late)

    assert len(planned) == 1
    operation = next(row for row in db.added if isinstance(row, BillingOperation))
    assert operation.request_snapshot["renewal_attempt"] == 1
    assert operation.idempotency_key.endswith(":a1")
    assert operation.provider_key_expires_at == late + RENEWAL_PROVIDER_WINDOW
    assert operation.provider_key_expires_at > late
    invoice = next(row for row in db.added if isinstance(row, BillingInvoice))
    assert invoice.plan_snapshot["renewal_attempt"] == 1
    assert invoice.operation_id == operation.id


@pytest.mark.asyncio
async def test_planner_waits_for_the_next_attempt_moment() -> None:
    resolved_first = _stored_attempt(attempt=1, state="canceled")
    subscription = _planning_subscription()
    common = [subscription, None, _planning_catalog(), UUID(int=1), "billing@2brain.pro"]

    too_early = PlanningDb([*common, resolved_first])
    assert (
        await plan_due_renewals(too_early, now=PAID_THROUGH - timedelta(hours=50))
    ) == ()
    assert not [row for row in too_early.added if isinstance(row, BillingOperation)]

    on_time = PlanningDb([*common, resolved_first, None])
    planned = await plan_due_renewals(on_time, now=PAID_THROUGH - timedelta(hours=48))

    assert len(planned) == 1
    second = next(row for row in on_time.added if isinstance(row, BillingOperation))
    assert second.request_snapshot["renewal_attempt"] == 2
    assert second.idempotency_key.endswith(":a2")
    # An attempt planned exactly on its moment reserves exactly one window.
    assert second.provider_key_expires_at == PAID_THROUGH - timedelta(hours=24)

    # The last attempt never reaches past the paid-through boundary.
    last = PlanningDb(
        [
            *common,
            _stored_attempt(attempt=1, state="canceled"),
            _stored_attempt(attempt=2, state="canceled"),
            None,
        ]
    )
    assert len(await plan_due_renewals(last, now=PAID_THROUGH - timedelta(hours=24))) == 1
    third = next(row for row in last.added if isinstance(row, BillingOperation))
    assert third.request_snapshot["renewal_attempt"] == 3
    assert third.provider_key_expires_at == PAID_THROUGH


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("state", "provider_id"),
    [("unknown", None), ("processing", None), ("sent", "pay-attempt-1")],
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

        assert await pending_renewal_charge_candidates(
            db, now=due_at - timedelta(minutes=1)
        ) == ()
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
        now=PAID_THROUGH,
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
        now=renewal_attempt_due_at(paid_through=PAID_THROUGH, attempt=1)
        - timedelta(hours=1),
    )

    assert result.status == "scheduled"
    assert operation.state == "scheduled"
    assert provider.calls == []


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
@pytest.mark.asyncio
@pytest.mark.parametrize("attempt", [1, 2])
async def test_declined_attempt_before_the_last_one_keeps_recurring_authority(
    monkeypatch, tmp_path: Path, attempt: int
) -> None:
    settings = _settings(tmp_path)
    subscription, operation, invoice, method = _rows(tmp_path, attempt=attempt)
    provider = FakeProvider(YooKassaProviderError("declined", status_code=402))
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
    provider = FakeProvider(YooKassaProviderError("declined", status_code=402))
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
