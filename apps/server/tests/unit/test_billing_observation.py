import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import httpx

from twobrain_rec_server.billing import webhook_reconciliation
from twobrain_rec_server.billing.reconciliation import (
    PaymentObservation,
    ProviderScope,
    extract_payment_observation,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingWebhookEvent,
    Workspace,
)


class _Rows:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


class _Db:
    def __init__(self, operations):
        self.operations = operations
        self.calls = 0
        self.scope = None

    async def scalars(self, _query):
        self.calls += 1
        return _Rows(self.operations)

    async def scalar(self, _query):
        entity = _query.column_descriptions[0].get("entity")
        if entity is BillingOperation and self.operations:
            return self.operations[0]
        return self.scope


def test_default_disables_provider_observation_without_querying_database() -> None:
    db = _Db([])

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(db, Settings())
    )

    assert result == {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    assert db.calls == 0


def test_default_disables_webhook_observation_without_querying_database() -> None:
    db = _Db([])

    result = asyncio.run(webhook_reconciliation.reconcile_pending_webhook_events(db, Settings()))

    assert result == {"processed": 0, "reconciled": 0, "pending": 0, "failed": 0}
    assert db.calls == 0


def test_checkout_keeps_provider_observation_enabled(monkeypatch, tmp_path: Path) -> None:
    provider_secret = tmp_path / "provider-secret"
    webhook_secret = tmp_path / "webhook-secret"
    referral_secret = tmp_path / "referral-secret"
    for path in (provider_secret, webhook_secret, referral_secret):
        path.write_text("test", encoding="utf-8")
    settings = Settings(
        billing_checkout_enabled=True,
        public_base_url="https://rec.example.test",
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-test",
        billing_yookassa_secret_file=provider_secret,
        billing_yookassa_webhook_secret_file=webhook_secret,
        billing_referral_secret_file=referral_secret,
        billing_support_email="billing@2brain.pro",
        billing_receipt_tax_system_code=2,
        billing_receipt_vat_code=1,
    )

    class _Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: _Provider())
    db = _Db([])

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(db, settings)
    )

    assert result == {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    assert db.calls == 1


def test_terminal_initial_observation_is_polled_only_by_explicit_operation_refresh(
    monkeypatch, tmp_path: Path
) -> None:
    secret = tmp_path / "yookassa-secret"
    secret.write_text("test", encoding="utf-8")
    settings = Settings(
        billing_provider_observation_enabled=True,
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-test",
        billing_yookassa_secret_file=secret,
        billing_yookassa_webhook_secret_file=secret,
    )
    calls: list[str] = []

    class _Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, payment_id: str):
            calls.append(payment_id)
            return {}

    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: _Provider())
    monkeypatch.setattr(
        webhook_reconciliation,
        "extract_payment_observation",
        lambda _payload, *, scope: SimpleNamespace(status="pending"),
    )
    operation = SimpleNamespace(
        id=UUID("10000000-0000-4000-8000-000000000001"),
        provider_id="payment-expired",
        workspace_id=UUID("20000000-0000-4000-8000-000000000002"),
        state="observation_expired",
    )
    workspace = Workspace(
        id=operation.workspace_id,
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="personal-owner",
        name="Personal owner",
        kind="personal",
        owner_user_id=UUID("40000000-0000-4000-8000-000000000004"),
    )

    class ExplicitDb(_Db):
        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                return self.operations[0] if self.operations else None
            return workspace

    db = ExplicitDb([])
    assert asyncio.run(webhook_reconciliation.reconcile_pending_initial_checkout_operations(db, settings))["processed"] == 0
    assert calls == []
    db = ExplicitDb([operation])
    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(
            db, settings, operation_id=operation.id
        )
    )
    assert result["processed"] == 1
    assert calls == ["payment-expired"]


def test_observation_only_polls_known_payment_without_enabling_checkout(
    monkeypatch, tmp_path: Path
) -> None:
    secret = tmp_path / "yookassa-secret"
    secret.write_text("test", encoding="utf-8")
    settings = Settings(
        billing_provider_observation_enabled=True,
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-test",
        billing_yookassa_secret_file=secret,
        billing_yookassa_webhook_secret_file=secret,
    )
    calls: list[str] = []

    class _Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, payment_id: str):
            calls.append(payment_id)
            return {}

    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: _Provider())
    monkeypatch.setattr(
        webhook_reconciliation,
        "extract_payment_observation",
        lambda _payload, *, scope: SimpleNamespace(status="pending"),
    )
    db = _Db(
        [
            SimpleNamespace(
                provider_id="payment-1",
                id=UUID("10000000-0000-4000-8000-000000000001"),
                workspace_id=UUID("20000000-0000-4000-8000-000000000002"),
            )
        ]
    )
    db.scope = Workspace(
        id=UUID("20000000-0000-4000-8000-000000000002"),
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="personal-owner",
        name="Personal owner",
        kind="personal",
        owner_user_id=UUID("40000000-0000-4000-8000-000000000004"),
    )

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(db, settings)
    )

    assert settings.billing_checkout_enabled is False
    assert calls == ["payment-1"]
    assert result == {"processed": 1, "succeeded": 0, "canceled": 0, "pending": 1, "failed": 0}


def test_invalid_initial_checkout_scope_is_terminal_without_provider_call(
    monkeypatch,
    tmp_path: Path,
) -> None:
    workspace_id = UUID("20000000-0000-4000-8000-000000000002")
    operation = BillingOperation(
        id=UUID("10000000-0000-4000-8000-000000000001"),
        workspace_id=workspace_id,
        kind="initial_checkout",
        idempotency_key="invalid-initial-scope",
        provider_id="must-not-be-requested",
        state="provider_pending",
        request_snapshot={},
    )
    invoice = BillingInvoice(
        workspace_id=workspace_id,
        operation_id=operation.id,
        safe_number="INV-INVALID-SCOPE",
        amount_minor=79_000,
        currency="RUB",
        status="pending",
    )

    class Db:
        async def scalars(self, _query):
            return [operation]

        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                return operation
            if entity is Workspace:
                return None
            if entity is BillingInvoice:
                return invoice
            raise AssertionError(f"unexpected query entity: {entity}")

    monkeypatch.setattr(
        webhook_reconciliation,
        "YooKassaClient",
        lambda _settings: (_ for _ in ()).throw(
            AssertionError("invalid scope must not initialize provider")
        ),
    )
    provider_secret = tmp_path / "provider-secret"
    provider_secret.write_text("synthetic", encoding="utf-8")

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(
            Db(),
            Settings(
                billing_provider_observation_enabled=True,
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_shop_id="shop-test",
                billing_yookassa_secret_file=provider_secret,
                billing_yookassa_webhook_secret_file=provider_secret,
            ),
        )
    )

    assert result == {"processed": 1, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 1}
    assert operation.state == "manual_resolution"
    assert invoice.status == "manual_resolution"


def test_observation_only_cannot_authorize_provider_payment() -> None:
    source_root = Path(__file__).parents[2] / "src/twobrain_rec_server"
    mutation_sources = (
        source_root / "billing/renewal_charge.py",
        source_root / "cabinet/web_routes/billing.py",
    )

    for source_path in mutation_sources:
        source = source_path.read_text(encoding="utf-8")
        assert "billing_provider_observation_enabled" not in source
        assert "create_payment(" in source


def test_initial_reconciliation_locks_workspace_before_operation(
    monkeypatch, tmp_path: Path
) -> None:
    workspace_id = UUID("20000000-0000-4000-8000-000000000002")
    operation = SimpleNamespace(
        id=UUID("10000000-0000-4000-8000-000000000001"),
        workspace_id=workspace_id,
        kind="initial_checkout",
        provider_id="payment-1",
        state="provider_pending",
    )
    workspace = Workspace(
        id=workspace_id,
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="personal-owner",
        name="Personal owner",
        kind="personal",
        owner_user_id=UUID("40000000-0000-4000-8000-000000000004"),
    )

    class OrderingDb:
        def __init__(self) -> None:
            self.events: list[str] = []

        async def scalars(self, _query):
            self.events.append("candidate_scan")
            return [operation]

        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                self.events.append("operation_lock")
                return operation
            if entity is Workspace:
                self.events.append("workspace_row_lock")
                return workspace
            raise AssertionError(f"unexpected query entity: {entity}")

    async def lock_workspace(_db, _workspace_id) -> None:
        db.events.append("workspace_advisory_lock")

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, _payment_id):
            return {}

    async def grant_payment(*_args, **_kwargs):
        db.events.append("grant")
        return "granted"

    db = OrderingDb()
    monkeypatch.setattr(webhook_reconciliation, "lock_storage_workspace", lock_workspace)
    monkeypatch.setattr(webhook_reconciliation, "grant_confirmed_payment", grant_payment)
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: Provider())
    monkeypatch.setattr(
        webhook_reconciliation,
        "extract_payment_observation",
        lambda _payload, *, scope: SimpleNamespace(
            status="succeeded",
            provider_payment_id="payment-1",
            amount_minor=100_000,
            currency="RUB",
            provider_created_at=datetime(2026, 9, 22, tzinfo=UTC),
            receipt_registration=None,
        ),
    )
    monkeypatch.setattr(webhook_reconciliation, "saved_bank_card_confirmed", lambda _payload: False)
    monkeypatch.setattr(webhook_reconciliation, "extract_saved_bank_card", lambda _payload: None)
    monkeypatch.setattr(webhook_reconciliation, "extract_payment_method_label", lambda _payload: None)
    monkeypatch.setattr(webhook_reconciliation, "read_billing_encryption_key", lambda _path: None)
    secret = tmp_path / "provider-secret"
    secret.write_text("synthetic", encoding="utf-8")

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(
            db,
            Settings(
                billing_provider_observation_enabled=True,
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_shop_id="shop-test",
                billing_yookassa_secret_file=secret,
                billing_yookassa_webhook_secret_file=secret,
            ),
        )
    )

    assert result["succeeded"] == 1
    assert db.events.index("workspace_advisory_lock") < db.events.index("operation_lock")
    assert db.events == [
        "candidate_scan",
        "workspace_advisory_lock",
        "operation_lock",
        "workspace_row_lock",
        "grant",
    ]


def test_background_initial_reconciliation_commits_between_candidates(
    monkeypatch, tmp_path: Path
) -> None:
    workspace_id = UUID("20000000-0000-4000-8000-000000000002")
    operations = [
        SimpleNamespace(
            id=UUID("10000000-0000-4000-8000-000000000001"),
            workspace_id=workspace_id,
            kind="initial_checkout",
            provider_id="payment-1",
            state="provider_pending",
        ),
        SimpleNamespace(
            id=UUID("10000000-0000-4000-8000-000000000002"),
            workspace_id=workspace_id,
            kind="initial_checkout",
            provider_id="payment-2",
            state="provider_pending",
        ),
    ]
    workspace = Workspace(
        id=workspace_id,
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="personal-owner",
        name="Personal owner",
        kind="personal",
        owner_user_id=UUID("40000000-0000-4000-8000-000000000004"),
    )

    class Db:
        def __init__(self) -> None:
            self.events: list[str] = []
            self.locked_operations = iter(operations)

        async def scalars(self, _query):
            self.events.append("candidate_scan")
            return operations

        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                self.events.append("operation_lock")
                return next(self.locked_operations)
            if entity is Workspace:
                self.events.append("workspace_row_lock")
                return workspace
            raise AssertionError(f"unexpected query entity: {entity}")

        async def commit(self):
            self.events.append("commit")

        async def rollback(self):
            self.events.append("rollback")

    async def lock_workspace(_db, _workspace_id) -> None:
        db.events.append("workspace_advisory_lock")

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, payment_id: str):
            db.events.append(f"provider:{payment_id}")
            return {}

    monkeypatch.setattr(webhook_reconciliation, "lock_storage_workspace", lock_workspace)
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: Provider())
    monkeypatch.setattr(
        webhook_reconciliation,
        "extract_payment_observation",
        lambda _payload, *, scope: SimpleNamespace(status="pending"),
    )
    provider_secret = tmp_path / "provider-secret"
    provider_secret.write_text("synthetic", encoding="utf-8")
    db = Db()

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(
            db,
            Settings(
                billing_provider_observation_enabled=True,
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_shop_id="shop-test",
                billing_yookassa_secret_file=provider_secret,
                billing_yookassa_webhook_secret_file=provider_secret,
            ),
            commit_each_operation=True,
        )
    )

    assert result == {"processed": 2, "succeeded": 0, "canceled": 0, "pending": 2, "failed": 0}
    assert db.events == [
        "candidate_scan",
        "workspace_advisory_lock",
        "operation_lock",
        "workspace_row_lock",
        "provider:payment-1",
        "commit",
        "workspace_advisory_lock",
        "operation_lock",
        "workspace_row_lock",
        "provider:payment-2",
        "commit",
    ]


def test_background_initial_reconciliation_keeps_candidate_keys_after_rollback(
    monkeypatch, tmp_path: Path
) -> None:
    workspace_id = UUID("20000000-0000-4000-8000-000000000002")
    operations = [
        SimpleNamespace(
            id=UUID("10000000-0000-4000-8000-000000000001"),
            workspace_id=workspace_id,
            kind="initial_checkout",
            provider_id="payment-1",
            state="provider_pending",
        ),
        SimpleNamespace(
            id=UUID("10000000-0000-4000-8000-000000000002"),
            workspace_id=workspace_id,
            kind="initial_checkout",
            provider_id="payment-2",
            state="provider_pending",
        ),
    ]
    workspace = Workspace(
        id=workspace_id,
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="personal-owner",
        name="Personal owner",
        kind="personal",
        owner_user_id=UUID("40000000-0000-4000-8000-000000000004"),
    )

    class Db:
        def __init__(self) -> None:
            self.events: list[str] = []
            self.locked_operations = iter(operations)

        async def scalars(self, _query):
            self.events.append("candidate_scan")
            return operations

        async def scalar(self, query):
            entity = query.column_descriptions[0].get("entity")
            if entity is BillingOperation:
                self.events.append("operation_lock")
                return next(self.locked_operations)
            if entity is Workspace:
                self.events.append("workspace_row_lock")
                return workspace
            raise AssertionError(f"unexpected query entity: {entity}")

        async def commit(self):
            self.events.append("commit")

        async def rollback(self):
            self.events.append("rollback")

    async def lock_workspace(_db, _workspace_id) -> None:
        db.events.append("workspace_advisory_lock")

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, payment_id: str):
            db.events.append(f"provider:{payment_id}")
            if payment_id == "payment-1":
                raise httpx.HTTPError("temporary provider failure")
            return {}

    monkeypatch.setattr(webhook_reconciliation, "lock_storage_workspace", lock_workspace)
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", lambda _settings: Provider())
    monkeypatch.setattr(
        webhook_reconciliation,
        "extract_payment_observation",
        lambda _payload, *, scope: SimpleNamespace(status="pending"),
    )
    provider_secret = tmp_path / "provider-secret"
    provider_secret.write_text("synthetic", encoding="utf-8")
    db = Db()

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(
            db,
            Settings(
                billing_provider_observation_enabled=True,
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_shop_id="shop-test",
                billing_yookassa_secret_file=provider_secret,
                billing_yookassa_webhook_secret_file=provider_secret,
            ),
            commit_each_operation=True,
        )
    )

    assert result == {"processed": 2, "succeeded": 0, "canceled": 0, "pending": 1, "failed": 1}
    assert db.events == [
        "candidate_scan",
        "workspace_advisory_lock",
        "operation_lock",
        "workspace_row_lock",
        "provider:payment-1",
        "rollback",
        "workspace_advisory_lock",
        "operation_lock",
        "workspace_row_lock",
        "provider:payment-2",
        "commit",
    ]


def test_invalid_historical_webhook_is_terminal_without_provider_call(
    monkeypatch, tmp_path: Path
) -> None:
    event = BillingWebhookEvent(
        id=UUID("10000000-0000-4000-8000-000000000001"),
        workspace_id=UUID("20000000-0000-4000-8000-000000000002"),
        provider_event_id="historical-invalid-scope",
        event_type="payment.succeeded",
        object_id="must-not-be-requested",
        occurred_at=datetime(2026, 8, 1, tzinfo=UTC),
        payload_hash="a" * 64,
        state="accepted",
        metadata_json={},
    )
    workspace = Workspace(
        id=event.workspace_id,
        organization_id=UUID("30000000-0000-4000-8000-000000000003"),
        slug="historical-corporate",
        name="Historical corporate",
        kind="corporate",
    )

    class Db:
        commits = 0

        async def scalars(self, _query):
            return [event.id]

        async def scalar(self, _query):
            return event

        async def get(self, model, _key):
            return workspace if model is Workspace else None

        async def commit(self):
            self.commits += 1

        async def rollback(self):
            raise AssertionError("terminal invalid scope must commit")

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def get_payment(self, _payment_id):
            raise AssertionError("invalid scope must not call provider")

    monkeypatch.setattr(
        webhook_reconciliation,
        "YooKassaClient",
        lambda _settings: Provider(),
    )
    db = Db()
    provider_secret = tmp_path / "provider-secret"
    provider_secret.write_text("synthetic", encoding="utf-8")

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_webhook_events(
            db,
            Settings(
                billing_provider_observation_enabled=True,
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_shop_id="shop-test",
                billing_yookassa_secret_file=provider_secret,
                billing_yookassa_webhook_secret_file=provider_secret,
            ),
        )
    )

    assert result == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}
    assert event.state == "reconciliation_gap"
    assert event.metadata_json == {"reconciliation": "workspace_scope_invalid"}
    assert db.commits == 1


def _payment_observation(*, provider_payment_id: str, operation_id: UUID | None):
    return PaymentObservation(
        scope=ProviderScope(environment="production", shop_id="shop-1"),
        provider_payment_id=provider_payment_id,
        amount_minor=100_000,
        currency="RUB",
        status="succeeded",
        provider_created_at=datetime(2026, 9, 18, tzinfo=UTC),
        operation_id=operation_id,
    )


class _LookupDb:
    """Scripted session: each scalar() call answers one lookup in order."""

    def __init__(self, answers):
        self.answers = list(answers)
        self.queries = 0
        self.flushed = False

    async def scalar(self, _query):
        self.queries += 1
        return self.answers.pop(0)

    async def flush(self):
        self.flushed = True


def test_lost_payment_response_is_bound_to_its_operation_by_metadata() -> None:
    """A payment stored without provider_id must still reach its operation."""
    workspace_id = UUID("30000000-0000-4000-8000-000000000003")
    operation_id = UUID("40000000-0000-4000-8000-000000000004")
    operation = SimpleNamespace(id=operation_id, provider_id=None)
    db = _LookupDb([None, operation])

    found = asyncio.run(
        webhook_reconciliation._locked_operation(
            db,
            workspace_id=workspace_id,
            observation=_payment_observation(
                provider_payment_id="pay-lost-response",
                operation_id=operation_id,
            ),
        )
    )

    assert found is operation
    assert operation.provider_id == "pay-lost-response"
    assert db.queries == 2
    assert db.flushed is True


def test_provider_id_match_stays_authoritative_over_metadata() -> None:
    """A payment already linked to an operation never re-binds through metadata."""
    bound = SimpleNamespace(id=UUID(int=7), provider_id="pay-known")
    db = _LookupDb([bound])

    found = asyncio.run(
        webhook_reconciliation._locked_operation(
            db,
            workspace_id=UUID("30000000-0000-4000-8000-000000000003"),
            observation=_payment_observation(
                provider_payment_id="pay-known",
                operation_id=UUID(int=9),
            ),
        )
    )

    assert found is bound
    assert db.queries == 1
    assert db.flushed is False


def test_payment_without_operation_metadata_is_not_rebound() -> None:
    """Without our operation id in metadata there is nothing to bind to."""
    db = _LookupDb([None])

    found = asyncio.run(
        webhook_reconciliation._locked_operation(
            db,
            workspace_id=UUID("30000000-0000-4000-8000-000000000003"),
            observation=_payment_observation(
                provider_payment_id="pay-foreign",
                operation_id=None,
            ),
        )
    )

    assert found is None
    assert db.queries == 1
    assert db.flushed is False


def test_payment_observation_reads_our_operation_id_from_provider_metadata() -> None:
    operation_id = UUID("40000000-0000-4000-8000-000000000004")
    observation = extract_payment_observation(
        {
            "id": "pay-1",
            "status": "succeeded",
            "created_at": "2026-09-18T00:00:00+00:00",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {"workspace_id": str(UUID(int=3)), "operation_id": str(operation_id)},
        },
        scope=ProviderScope(environment="production", shop_id="shop-1"),
    )

    assert observation.operation_id == operation_id


def test_payment_observation_ignores_malformed_operation_id() -> None:
    observation = extract_payment_observation(
        {
            "id": "pay-1",
            "status": "succeeded",
            "created_at": "2026-09-18T00:00:00+00:00",
            "amount": {"value": "1000.00", "currency": "RUB"},
            "metadata": {"operation_id": "not-a-uuid"},
        },
        scope=ProviderScope(environment="production", shop_id="shop-1"),
    )

    assert observation.operation_id is None
