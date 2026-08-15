import asyncio
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

from twobrain_rec_server.billing import webhook_reconciliation
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
            ),
        )
    )

    assert result == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}
    assert event.state == "reconciliation_gap"
    assert event.metadata_json == {"reconciliation": "workspace_scope_invalid"}
    assert db.commits == 1
