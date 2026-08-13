import asyncio
from pathlib import Path
from types import SimpleNamespace

from twobrain_rec_server.billing import webhook_reconciliation
from twobrain_rec_server.config import Settings


class _Rows:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


class _Db:
    def __init__(self, operations):
        self.operations = operations
        self.calls = 0

    async def scalars(self, _query):
        self.calls += 1
        return _Rows(self.operations)


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


def test_observation_only_polls_known_payment_without_enabling_checkout(monkeypatch, tmp_path: Path) -> None:
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
    db = _Db([SimpleNamespace(provider_id="payment-1")])

    result = asyncio.run(
        webhook_reconciliation.reconcile_pending_initial_checkout_operations(db, settings)
    )

    assert settings.billing_checkout_enabled is False
    assert calls == ["payment-1"]
    assert result == {"processed": 1, "succeeded": 0, "canceled": 0, "pending": 1, "failed": 0}


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
