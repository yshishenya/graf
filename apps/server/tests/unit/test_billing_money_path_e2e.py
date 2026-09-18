"""End-to-end proof of the paid money path (FR-025 / SC-006).

The test drives the real cabinet checkout route, the real provider webhook
route, the real PostgreSQL schema built by ``alembic upgrade head``, the price
catalog owned by migration 0093 and the real background reconciliation. Only the
provider's network transport is replaced, so ``YooKassaClient`` still derives
the idempotency key, assembles the fiscal receipt, sends the request and parses
the provider answer.
"""

from __future__ import annotations

import asyncio
import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import httpx
from alembic.migration import MigrationContext
from alembic.operations import Operations
from cryptography.fernet import Fernet
from sqlalchemy import select

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.billing import webhook_reconciliation
from twobrain_rec_server.billing.catalog import CatalogNotApproved, validate_plan_version
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.cabinet.user_time import format_user_datetime
from twobrain_rec_server.cabinet.web_routes import billing as billing_routes
from twobrain_rec_server.db.models import (
    AuthSessionDeviceBinding,
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPlanVersion,
    BillingWebhookEvent,
    ExternalIdentity,
    RegisteredDevice,
    WorkspaceSubscription,
)
from twobrain_rec_server.public.offers import (
    PUBLIC_ANNUAL_AMOUNT_MINOR,
    PUBLIC_APPROVED_OFFER_VERSION,
    PUBLIC_MONTHLY_AMOUNT_MINOR,
)

SERVER_ROOT = Path(__file__).resolve().parents[2]
CATALOG_MIGRATION = (
    SERVER_ROOT / "src/twobrain_rec_server/db/migrations/versions/0093_billing_catalog_seed.py"
)
CHECKOUT_PATH = "/billing/checkout/start"
WEBHOOK_PATH = "/api/v1/billing/providers/yookassa/webhook/test"
WEBHOOK_SECRET = "synthetic-webhook-secret"
RECEIPT_EMAIL = "verified-owner@example.test"
PAID_AT = datetime(2026, 9, 10, 9, 0, tzinfo=UTC)
PAID_THROUGH = datetime(2026, 10, 10, 9, 0, tzinfo=UTC)  # PAID_AT plus one month


class _FakeYooKassa:
    """Provider transport double that records exactly what the real client sent."""

    def __init__(
        self,
        *,
        confirmed_amount: dict[str, str] | None = None,
        saved_card: bool = False,
    ) -> None:
        self.payment_id = f"pay-{uuid4().hex[:16]}"
        self.confirmed_amount = confirmed_amount
        self.saved_card = saved_card
        self.create_payloads: list[dict[str, Any]] = []
        self.idempotence_keys: list[str] = []
        self.read_count = 0

    def handle(self, request: httpx.Request) -> httpx.Response:
        if request.method == "POST":
            payload = json.loads(request.content)
            self.create_payloads.append(payload)
            self.idempotence_keys.append(request.headers["Idempotence-Key"])
            redirect = f"https://yookassa.test/checkout/{self.payment_id}"
            return httpx.Response(200, json=dict(payload, id=self.payment_id, status="pending",
                                                 confirmation={"confirmation_url": redirect}))
        assert request.url.path == f"/v3/payments/{self.payment_id}"
        self.read_count += 1
        created = self.create_payloads[0]
        confirmed = dict(created, id=self.payment_id, status="succeeded",
                         created_at=PAID_AT.isoformat(),
                         amount=self.confirmed_amount or created["amount"])
        if self.saved_card:
            confirmed["payment_method"] = {
                "id": "pm-synthetic-card-1",
                "type": "bank_card",
                "saved": True,
                "card": {"last4": "4242"},
            }
        return httpx.Response(200, json=confirmed)


def _configure_billing(client, tmp_path: Path) -> None:
    """Point the shared application at test-mode provider secrets."""
    settings = client.app.state.settings
    for name, value in (
        ("billing_yookassa_secret_file", "synthetic"),
        ("billing_yookassa_webhook_secret_file", WEBHOOK_SECRET),
        ("billing_referral_secret_file", "synthetic-referral"),
    ):
        path = tmp_path / name
        path.write_text(value, encoding="utf-8")
        setattr(settings, name, path)
    key_file = tmp_path / "billing-key"
    key_file.write_bytes(Fernet.generate_key())
    settings.billing_checkout_enabled = True
    settings.billing_yookassa_environment = "test"
    settings.billing_yookassa_base_url = "https://api.yookassa.test"
    settings.billing_yookassa_shop_id = "shop-money-path"
    settings.credential_encryption_key_file = key_file
    settings.billing_receipt_tax_system_code = 2
    settings.billing_receipt_vat_code = 1
    settings.billing_support_email = "billing@2brain.pro"
    settings.public_base_url = "https://rec.2brain.pro"
    settings.billing_provider_floor_minor = 100


def _prepare_owner_session(client) -> tuple[UUID, dict[str, str]]:
    """Seed a personal owner with a verified receipt email and a CSRF-bound session."""

    async def seed() -> tuple[UUID, UUID, str]:
        async with client.app_state["sessionmaker"]() as db:
            workspace = await ensure_personal_workspace(db, organization_id=ORG_ID, user_id=USER_ID)
            device_id = uuid4()
            db.add(RegisteredDevice(
                id=device_id, workspace_id=workspace.id, user_id=USER_ID, platform="web",
                device_public_id=f"money-path-{device_id}", client_version="test",
                status="active", registration_state="approved", trusted_by=USER_ID,
            ))
            db.add(ExternalIdentity(
                user_id=USER_ID, provider="email", provider_subject=f"money-path-{USER_ID}",
                email=RECEIPT_EMAIL, is_verified=True, is_active=True,
            ))
            await db.commit()
            issued = await issue_auth_session(
                db,
                user_id=USER_ID,
                workspace_id=workspace.id,
                device_id=device_id,
                provider="email",
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=device_id,
                device_state="trusted",
            ))
            await db.commit()
            return workspace.id, issued.id, issued.token

    workspace_id, session_id, token = asyncio.run(seed())
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
    csrf = issue_csrf_token(session_id=session_id, secret=str(client.app.state.web_csrf_secret))
    return workspace_id, {"X-CSRF-Token": csrf}


def _approved_month_catalog(client) -> Any:
    """Return the personal/month price the production migration owns.

    The disposable harness truncates every mapped table before each test, which
    also removes the catalog rows migration 0093 seeds. Re-running that exact
    migration keeps the approved price single-sourced in the migration instead
    of hard-coding a second copy in the test.
    """
    spec = importlib.util.spec_from_file_location("catalog_seed_0093", CATALOG_MIGRATION)
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    def apply(connection: Any) -> None:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()

    async def restore_and_read():
        async with client.app_state["engine"].begin() as connection:
            await connection.run_sync(apply)
        async with client.app_state["sessionmaker"]() as db:
            rows = await db.scalars(
                select(BillingPlanVersion)
                .where(
                    BillingPlanVersion.plan_code == "personal",
                    BillingPlanVersion.cycle == "month",
                )
                .order_by(BillingPlanVersion.version.desc())
            )
            for row in rows:
                try:
                    return validate_plan_version(row)
                except (CatalogNotApproved, ValueError):
                    continue
            return None

    catalog = asyncio.run(restore_and_read())
    assert catalog is not None, (
        "migration 0093 must seed an effective personal/month billing_plan_versions row; "
        "without it the checkout route fails closed with catalog_not_approved"
    )
    assert catalog.amount_minor == PUBLIC_MONTHLY_AMOUNT_MINOR, "public monthly price drifted"
    assert catalog.offer_version == PUBLIC_APPROVED_OFFER_VERSION, "offer revision drifted"
    return catalog


def _money_state(client, workspace_id: UUID, key: str) -> SimpleNamespace:
    """Read the persisted money rows for one checkout idempotency key."""

    async def read() -> SimpleNamespace:
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == workspace_id,
                    BillingOperation.idempotency_key == key,
                )
            )
            return SimpleNamespace(
                operation=operation,
                invoice=await db.scalar(
                    select(BillingInvoice).where(BillingInvoice.operation_id == operation.id)
                ),
                subscription=await db.scalar(
                    select(WorkspaceSubscription).where(
                        WorkspaceSubscription.workspace_id == workspace_id
                    )
                ),
                grants=tuple(await db.scalars(
                    select(BillingEntitlementGrant).where(
                        BillingEntitlementGrant.workspace_id == workspace_id
                    )
                )),
                events=tuple(await db.scalars(
                    select(BillingWebhookEvent).where(
                        BillingWebhookEvent.workspace_id == workspace_id
                    )
                )),
            )

    return asyncio.run(read())


def _reconcile(client) -> dict[str, int]:
    """Run the pending-provider-event pass exactly like the billing worker does."""

    async def run() -> dict[str, int]:
        async with client.app_state["sessionmaker"]() as db:
            counters = await webhook_reconciliation.reconcile_pending_webhook_events(
                db, client.app.state.settings
            )
            await db.commit()
            return counters

    return asyncio.run(run())


def _start_checkout(client, headers: dict[str, str], key: str):
    return client.post(
        CHECKOUT_PATH,
        headers=headers,
        follow_redirects=False,
        data={
            "cycle": "month",
            "idempotency_key": key,
            "offer_consent": "true",
            "recurring_consent": "true",
        },
    )


def _payment_webhook(*, workspace_id: UUID, operation_id: UUID, payment_id: str, value: str) -> dict:
    """Build one provider notification shaped exactly like a YooKassa callback."""
    return {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {
            "id": payment_id,
            "status": "succeeded",
            "created_at": PAID_AT.isoformat(),
            "amount": {"value": value, "currency": "RUB"},
            "metadata": {"workspace_id": str(workspace_id), "operation_id": str(operation_id)},
        },
    }


def _deliver_webhook(client, body: dict):
    return client.post(
        WEBHOOK_PATH,
        content=json.dumps(body).encode(),
        headers={"content-type": "application/json", "X-Billing-Webhook-Secret": WEBHOOK_SECRET},
    )


def _open_checkout(client, monkeypatch, tmp_path: Path, provider: _FakeYooKassa, key: str):
    """Configure test billing, seed the owner session and open one hosted checkout."""
    _configure_billing(client, tmp_path)
    transport = httpx.MockTransport(provider.handle)
    factory = lambda settings: YooKassaClient(settings, transport=transport)  # noqa: E731
    monkeypatch.setattr(billing_routes, "YooKassaClient", factory)
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", factory)
    catalog = _approved_month_catalog(client)
    workspace_id, headers = _prepare_owner_session(client)
    started = _start_checkout(client, headers, key)
    assert started.status_code == 303, started.text
    state = _money_state(client, workspace_id, key)
    assert state.operation is not None and state.invoice is not None, "checkout persisted no money"
    return SimpleNamespace(
        workspace_id=workspace_id, headers=headers, catalog=catalog, started=started, state=state
    )


def test_confirmed_payment_grants_access_and_survives_replays(
    client, monkeypatch, tmp_path: Path
) -> None:
    key = "checkout-money-path-1"
    provider = _FakeYooKassa()
    checkout = _open_checkout(client, monkeypatch, tmp_path, provider, key)
    operation, invoice = checkout.state.operation, checkout.state.invoice

    # Hosted checkout created the money rows and reached the provider.
    assert checkout.started.headers["location"] == (
        f"https://yookassa.test/checkout/{provider.payment_id}"
    )
    assert (operation.kind, operation.state) == ("initial_checkout", "provider_pending")
    assert operation.provider_id == provider.payment_id
    assert (invoice.status, invoice.currency) == ("pending", "RUB")
    assert invoice.receipt_contact_snapshot == RECEIPT_EMAIL
    assert invoice.amount_minor == checkout.catalog.amount_minor == PUBLIC_MONTHLY_AMOUNT_MINOR
    assert checkout.state.grants == () and checkout.state.events == ()

    # The real client signed the request: idempotency, capture, saved method, receipt.
    value = f"{invoice.amount_minor // 100}.{invoice.amount_minor % 100:02d}"
    amount = {"value": value, "currency": "RUB"}
    create = provider.create_payloads[0]
    assert provider.idempotence_keys == [operation.idempotency_key]
    assert create["amount"] == amount
    assert create["capture"] is True
    assert create["save_payment_method"] is True
    assert create["metadata"]["workspace_id"] == str(checkout.workspace_id)
    assert create["receipt"]["tax_system_code"] == 2
    assert create["receipt"]["customer"]["email"] == RECEIPT_EMAIL
    assert create["receipt"]["items"][0]["vat_code"] == 1
    assert create["receipt"]["items"][0]["payment_mode"] == "full_payment"

    # The webhook only records the signal; the background pass reads provider truth.
    webhook = _payment_webhook(
        workspace_id=checkout.workspace_id,
        operation_id=operation.id,
        payment_id=provider.payment_id,
        value=value,
    )
    delivered = _deliver_webhook(client, webhook)
    assert delivered.status_code == 200 and delivered.json() == {"status": "accepted"}
    assert _reconcile(client) == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}
    assert provider.read_count == 1

    # Access landed only after the provider confirmed the exact amount.
    state = _money_state(client, checkout.workspace_id, key)
    assert state.events[0].state == "reconciled"
    assert len(state.grants) == 1
    assert state.grants[0].provider_payment_id == provider.payment_id
    assert state.grants[0].invoice_id == invoice.id
    assert (state.grants[0].starts_at, state.grants[0].ends_at) == (PAID_AT, PAID_THROUGH)
    assert state.grants[0].amount_minor == invoice.amount_minor
    assert (state.subscription.state, state.subscription.plan_code, state.subscription.cycle) == (
        "personal",
        "personal",
        "month",
    )
    assert state.subscription.paid_through == PAID_THROUGH
    assert state.subscription.billing_anchor == PAID_AT
    assert state.invoice.status == "succeeded"
    assert state.operation.state == "succeeded"

    # Replay: a duplicate signal, an idempotent pass and no second provider payment.
    assert _deliver_webhook(client, webhook).json() == {"status": "duplicate"}
    assert _reconcile(client) == {"processed": 0, "reconciled": 0, "pending": 0, "failed": 0}
    retried = _start_checkout(client, checkout.headers, key)
    assert retried.status_code == 303
    assert retried.headers["location"] == checkout.started.headers["location"]
    assert len(provider.create_payloads) == 1
    assert provider.read_count == 1
    assert len(_money_state(client, checkout.workspace_id, key).grants) == 1


def test_amount_mismatch_never_grants_access(client, monkeypatch, tmp_path: Path) -> None:
    key = "checkout-amount-mismatch"
    provider = _FakeYooKassa(confirmed_amount={"value": "1.00", "currency": "RUB"})
    checkout = _open_checkout(client, monkeypatch, tmp_path, provider, key)

    webhook = _payment_webhook(
        workspace_id=checkout.workspace_id,
        operation_id=checkout.state.operation.id,
        payment_id=provider.payment_id,
        value="1.00",
    )
    assert _deliver_webhook(client, webhook).json() == {"status": "accepted"}
    assert _reconcile(client)["processed"] == 1
    assert provider.read_count == 1

    state = _money_state(client, checkout.workspace_id, key)
    assert state.grants == (), "a provider-confirmed mismatched amount must never grant access"
    assert state.operation.state == "reconciliation_gap"
    assert state.events[0].state == "reconciliation_gap"
    assert state.invoice.status != "succeeded"
    assert state.subscription is None or state.subscription.state == "free"


def test_early_payment_extends_the_paid_period_and_keeps_the_remainder(
    client, monkeypatch, tmp_path: Path
) -> None:
    """An active month never blocks a year paid ahead: the remainder survives."""
    month_provider = _FakeYooKassa()
    month = _open_checkout(client, monkeypatch, tmp_path, month_provider, "checkout-early-month")
    month_amount = f"{month.state.invoice.amount_minor // 100}.{month.state.invoice.amount_minor % 100:02d}"
    assert _deliver_webhook(
        client,
        _payment_webhook(
            workspace_id=month.workspace_id,
            operation_id=month.state.operation.id,
            payment_id=month_provider.payment_id,
            value=month_amount,
        ),
    ).json() == {"status": "accepted"}
    assert _reconcile(client) == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}
    paid_month = _money_state(client, month.workspace_id, "checkout-early-month").subscription
    assert paid_month.paid_through == PAID_THROUGH

    year_provider = _FakeYooKassa()
    transport = httpx.MockTransport(year_provider.handle)
    factory = lambda settings: YooKassaClient(settings, transport=transport)  # noqa: E731
    monkeypatch.setattr(billing_routes, "YooKassaClient", factory)
    monkeypatch.setattr(webhook_reconciliation, "YooKassaClient", factory)

    # The paid month is still running, and the yearly checkout is allowed.
    started = client.post(
        CHECKOUT_PATH,
        headers=month.headers,
        follow_redirects=False,
        data={
            "cycle": "year",
            "idempotency_key": "checkout-early-year",
            "offer_consent": "true",
            "recurring_consent": "true",
        },
    )
    assert started.status_code == 303, started.text
    assert started.headers["location"] == f"https://yookassa.test/checkout/{year_provider.payment_id}"
    year = _money_state(client, month.workspace_id, "checkout-early-year")
    assert year.operation is not None and year.invoice is not None
    assert year.invoice.amount_minor == PUBLIC_ANNUAL_AMOUNT_MINOR

    # The same unfinished payment is recovered instead of being charged twice.
    repeated = client.post(
        CHECKOUT_PATH,
        headers=month.headers,
        follow_redirects=False,
        data={
            "cycle": "year",
            "idempotency_key": "checkout-early-year",
            "offer_consent": "true",
            "recurring_consent": "true",
        },
    )
    assert repeated.status_code == 303
    assert repeated.headers["location"] == started.headers["location"]
    assert len(year_provider.create_payloads) == 1

    year_amount = f"{year.invoice.amount_minor // 100}.{year.invoice.amount_minor % 100:02d}"
    assert _deliver_webhook(
        client,
        _payment_webhook(
            workspace_id=month.workspace_id,
            operation_id=year.operation.id,
            payment_id=year_provider.payment_id,
            value=year_amount,
        ),
    ).json() == {"status": "accepted"}
    assert _reconcile(client) == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}

    state = _money_state(client, month.workspace_id, "checkout-early-year")
    assert (state.subscription.plan_code, state.subscription.cycle) == ("personal", "year")
    # One year is added to the month that was already paid for.
    assert state.subscription.paid_through == datetime(2027, 10, 10, 9, 0, tzinfo=UTC)
    year_grant = next(
        grant for grant in state.grants if grant.provider_payment_id == year_provider.payment_id
    )
    assert year_grant.starts_at == PAID_THROUGH
    assert year_grant.ends_at == state.subscription.paid_through


def test_subscription_page_names_the_real_charge_day(client, monkeypatch, tmp_path: Path) -> None:
    """The cabinet must not promise a charge day later than the real attempt.

    The renewal starts three days before the paid period ends, so showing the
    period end as "next charge" would tell the owner the money leaves on a day
    the attempts are already over.
    """
    provider = _FakeYooKassa(saved_card=True)
    opened = _open_checkout(client, monkeypatch, tmp_path, provider, "checkout-charge-day")
    amount = f"{opened.state.invoice.amount_minor // 100}.{opened.state.invoice.amount_minor % 100:02d}"
    assert _deliver_webhook(
        client,
        _payment_webhook(
            workspace_id=opened.workspace_id,
            operation_id=opened.state.operation.id,
            payment_id=provider.payment_id,
            value=amount,
        ),
    ).json() == {"status": "accepted"}
    assert _reconcile(client) == {"processed": 1, "reconciled": 1, "pending": 0, "failed": 0}

    state = _money_state(client, opened.workspace_id, "checkout-charge-day")
    assert state.subscription.paid_through == PAID_THROUGH
    assert state.subscription.recurring_allowed is True

    page = client.get("/billing/subscription", headers=opened.headers)
    assert page.status_code == 200, page.text
    first_attempt = format_user_datetime(PAID_THROUGH - timedelta(hours=72), show_zone=True)
    period_end = format_user_datetime(PAID_THROUGH, show_zone=True)
    assert f"Следующее списание: <strong>{first_attempt}</strong>" in page.text
    assert f"Следующее списание: <strong>{period_end}</strong>" not in page.text
    # Оплаченный период по-прежнему показан его собственной датой.
    assert f"Оплачено до: <strong>{period_end}</strong>" in page.text
