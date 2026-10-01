"""A verified email returns to a fresh purchase without replaying a payment."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urlencode, urlsplit
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select, update

from tests.fakes.auth_contexts import ORG_ID, USER_ID
from tests.integration.test_billing_clarity import (
    payment_counts,
    seed_payment,
    set_subscription,
    unverify_email,
)
from tests.integration.test_billing_purchase_journey import seed_catalog_and_budget
from tests.integration.test_billing_review_regressions import seed_periods
from tests.integration.test_web_owner_session_context import _bind_email_auth_attempt_cookie
from tests.unit.test_billing_money_path_e2e import (
    _approved_month_catalog,
    _configure_billing,
    _FakeYooKassa,
    _prepare_owner_session,
)
from twobrain_rec_server.auth import redirects
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.billing.entitlements import grant_confirmed_renewal
from twobrain_rec_server.billing.payment_methods import (
    read_billing_encryption_key,
    seal_provider_reference,
)
from twobrain_rec_server.billing.promotions import promo_code_hash
from twobrain_rec_server.billing.renewal_charge import next_renewal_attempt, project_renewal_cutoffs
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.cabinet.web_routes import billing
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPurchaseQuote,
    ExternalIdentity,
    PromotionCampaign,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)


@pytest.fixture
def owner(client, tmp_path, monkeypatch):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    unverify_email(client)

    def no_provider(*_args, **_kwargs):
        pytest.fail("Email navigation must never contact a payment provider")

    monkeypatch.setattr(billing, "YooKassaClient", no_provider)
    return workspace, headers


def form(html, suffix):
    for match in re.finditer(r'<form\b[^>]*action="([^"]+)"[^>]*>(.*?)</form>', html, re.S):
        action = unescape(match[1])
        if urlsplit(action).path.endswith(suffix):
            values = {
                item[1]: unescape(item[2])
                for item in re.finditer(r'<input\b[^>]*name="([^"]+)"[^>]*value="([^"]*)"', match[2])
            }
            return action, values
    pytest.fail(f"Missing form: {suffix}")


def return_link(html):
    match = re.search(r'<a\b[^>]*href="([^"]+)"[^>]*>\s*Вернуться к оплате\s*</a>', html)
    assert match is not None
    return unescape(match[1])


def code(html):
    match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", html)
    assert match is not None
    return match[1]


@pytest.mark.parametrize("target", [
    "/billing/checkout?cycle=month", "/billing/checkout?cycle=year",
    "/billing/storage?package_count=0", "/billing/storage?package_count=99",
    "/billing/subscription",
])
def test_billing_return_allows_only_fresh_get_choices(target):
    assert redirects.safe_billing_return_path(target) == target


@pytest.mark.parametrize("target", [
    None, "", " /billing/subscription", "//evil.test/billing/subscription",
    "https://evil.test/billing/subscription", "/billing\\subscription",
    "/billing/%73ubscription", "/billing/subscription#details", "/billing/subscription?",
    "/billing/subscription?quote_id=1", "/billing/purchases/confirm",
    "/billing/checkout/start", "/billing/storage/preview", "/billing/subscription/early-preview",
    "/billing/checkout?cycle=month&cycle=year", "/billing/checkout?cycle=year&promo=SECRET",
    "/billing/checkout?cycle=year#anything", "/billing/checkout?cycle=year\\",
    "/billing/storage?package_count=-1", "/billing/storage?package_count=100",
    "/billing/storage?package_count=01", "/billing/storage?package_count=1&package_count=2",
    "/billing/storage?package_count=1&consent=1", "/billing/subscription\n",
])
def test_billing_return_rejects_authority_or_purchase_state(target):
    assert redirects.safe_billing_return_path(target) is None


@pytest.mark.parametrize("base", ["/settings/account", "/desktop/settings/account", "/account", "/desktop/account"])
def test_account_alias_opens_email_and_keeps_one_safe_return(client, owner, base):
    _, headers = owner
    target = "/billing/checkout?cycle=year"
    page = client.get(base, params={"next": target}, headers=headers)
    assert page.status_code == 200
    assert return_link(page.text) == target
    assert re.search(r'<details[^>]*\bopen[^>]*>\s*<summary>Добавить способ входа', page.text)
    action, fields = form(page.text, "/email-link/start")
    assert fields["next"] == target
    assert parse_qs(urlsplit(action).query)["next"] == [target]
    duplicate = client.get(base, params=[("next", target), ("next", "/billing/subscription")], headers=headers)
    assert "Вернуться к оплате" not in duplicate.text
    assert payment_counts(client) == (0, 0)


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("target", ["/billing/checkout?cycle=year", "/billing/storage?package_count=1", "/billing/subscription"])
def test_email_error_resend_change_and_success_keep_fresh_purchase(client, owner, embedded, target):
    workspace, headers = owner
    if target.startswith("/billing/storage") or target == "/billing/subscription":
        seed_periods(client, workspace)
    before = payment_counts(client)
    base = ("/desktop" if embedded else "") + "/settings/account"
    account = client.get(base, params={"next": target}, headers=headers)
    action, fields = form(account.text, "/email-link/start")
    email = "receipt-recovery@example.test"
    started = client.post(action, data={**fields, "email": email}, headers=headers)
    assert started.status_code == 200
    assert return_link(started.text) == target
    change = re.search(r'href="([^"]+)">Изменить почту</a>', started.text)
    assert change is not None
    changed = client.get(unescape(change[1]), headers=headers)
    assert return_link(changed.text) == target
    action, fields = form(started.text, "/email-link/verify")
    wrong_code = "000000" if code(started.text) != "000000" else "111111"
    rejected = client.post(action, data={**fields, "code": wrong_code}, headers=headers)
    assert rejected.status_code == 400
    assert return_link(rejected.text) == target
    action, fields = form(rejected.text, "/email-link/start")
    resent = client.post(action, data=fields, headers=headers)
    assert resent.status_code == 200
    assert return_link(resent.text) == target
    action, fields = form(resent.text, "/email-link/verify")
    verified = client.post(action, data={**fields, "code": code(resent.text)}, headers=headers, follow_redirects=False)
    assert verified.status_code == 303
    location = urlsplit(verified.headers["location"])
    assert location.path == base
    assert parse_qs(location.query)["next"] == [target]
    final_account = client.get(verified.headers["location"], headers=headers)
    returned = client.get(return_link(final_account.text), headers=headers)
    assert returned.status_code == 200
    if target.startswith("/billing/checkout"):
        assert 'name="cycle" value="year"' in returned.text
        offer = re.search(r'<input[^>]*name="offer_consent"[^>]*>', returned.text)
        recurring = re.search(r'<input[^>]*name="recurring_consent"[^>]*>', returned.text)
        assert offer and "required" in offer.group() and "checked" not in offer.group()
        assert recurring and "checked" in recurring.group() and "required" not in recurring.group()
    if target.startswith("/billing/storage"):
        assert re.search(r'<option value="1"[^>]*\sselected[^>]*>', returned.text)
    assert payment_counts(client) == before


@pytest.mark.parametrize("embedded", [False, True])
def test_account_reauth_keeps_outer_account_route_for_native_login(client, owner, embedded):
    _, headers = owner
    target = "/billing/checkout?cycle=year"
    base = ("/desktop" if embedded else "") + "/settings/account"
    page = client.get(base, params={"provider_link": "reauth_required", "next": target}, headers=headers)
    outcome = page.text.split('aria-labelledby="account-outcome-title">', 1)[1].split("</section>", 1)[0]
    _, fields = form(outcome, "/desktop/meetings" if embedded else "/logout")
    login = urlsplit(fields["next"])
    assert login.path == "/login"
    outer_next = parse_qs(login.query)["next"][0]
    assert urlsplit(outer_next).path == base
    assert parse_qs(urlsplit(outer_next).query)["next"] == [target]
    login_page = client.get(fields["next"])
    assert return_link(login_page.text) == target


def seed_second_account(client, email):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            user_id, workspace_id = uuid4(), uuid4()
            db.add_all([
                UserIdentity(id=user_id, organization_id=ORG_ID, external_subject=str(user_id)),
                Workspace(id=workspace_id, organization_id=ORG_ID, owner_user_id=user_id,
                          slug=f"billing-return-{workspace_id.hex}", name="Synthetic", kind="personal"),
            ])
            await db.flush()
            db.add_all([
                WorkspaceMembership(workspace_id=workspace_id, user_id=user_id, role="owner", status="active"),
                ExternalIdentity(user_id=user_id, provider="email", provider_subject=email,
                                 email=email, is_verified=True, is_active=True),
            ])
            await db.commit()
            return user_id, workspace_id
    return asyncio.run(run())


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize("decision", ["confirm", "cancel", "stale"])
def test_email_merge_preserves_return_without_changing_confirmation(client, owner, embedded, decision):
    _, headers = owner
    email = "receipt-merge@example.test"
    seed_second_account(client, email)
    target = "/billing/checkout?cycle=year"
    base = ("/desktop" if embedded else "") + "/settings/account"
    started = client.post(f"{base}/email-link/start?{urlencode({'next': target})}",
                          data={"email": email, "next": target}, headers=headers)
    action, fields = form(started.text, "/email-link/verify")
    verified = client.post(action, data={**fields, "code": code(started.text)}, headers=headers, follow_redirects=False)
    assert verified.status_code == 303
    preview_url = verified.headers["location"]
    assert urlsplit(preview_url).path.startswith(base + "/merge/")
    assert parse_qs(urlsplit(preview_url).query)["next"] == [target]
    preview = client.get(preview_url, headers=headers)
    assert return_link(preview.text) == target
    action, fields = form(preview.text, "/confirm" if decision == "stale" else "/" + decision)
    if decision == "stale":
        fields["preview_fingerprint"] = "stale"
    result = client.post(action, data=fields, headers=headers, follow_redirects=False)
    assert result.status_code == 303
    location = result.headers["location"]
    if decision == "stale":
        assert urlsplit(location).path == urlsplit(preview_url).path
        assert parse_qs(urlsplit(location).query)["next"] == [target]
        recovery = client.get(location, headers=headers)
        assert return_link(recovery.text) == target
        action, _ = form(recovery.text, "/email-link/start")
        assert parse_qs(urlsplit(action).query)["next"] == [target]
        assert "/confirm\"" not in recovery.text
        assert payment_counts(client) == (0, 0)
        return
    if decision == "confirm":
        assert urlsplit(location).path == "/login"
        login_page = client.get(location)
        assert return_link(login_page.text) == target
        expected_return = parse_qs(urlsplit(location).query)["next"][0]
        action, fields = form(login_page.text, "/login/email/start")
        login_code = client.post(action, data={**fields, "email": email})
        assert return_link(login_code.text) == target
        action, fields = form(login_code.text, "/login/email/verify")
        _bind_email_auth_attempt_cookie(client, login_code, state_nonce=fields["state"])
        signed_in = client.post(action, data={**fields, "code": code(login_code.text)}, follow_redirects=False)
        assert signed_in.status_code == 303
        location = signed_in.headers["location"]
        assert location == expected_return
        client.cookies.set(AUTH_SESSION_COOKIE_NAME, signed_in.cookies.get(AUTH_SESSION_COOKIE_NAME))
        assert return_link(client.get(location).text) == target
    assert urlsplit(location).path == base
    assert parse_qs(urlsplit(location).query)["next"] == [target]
    assert payment_counts(client) == (0, 0)


@pytest.mark.parametrize("state", ["failed", "canceled"])
def test_storage_terminal_retry_reopens_same_volume_with_fresh_calculation(client, owner, state):
    workspace, headers = owner
    seed_periods(client, workspace)
    seed_payment(client, workspace, state=state, kind="storage_upgrade")

    async def set_capacity():
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.scalar(select(BillingOperation).where(
                BillingOperation.idempotency_key == "clarity-existing",
            ))
            operation.request_snapshot = {**operation.request_snapshot, "target_capacity_bytes": 15_000_000_000}
            await db.commit()

    asyncio.run(set_capacity())
    before = payment_counts(client)
    status = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert 'href="/billing/storage?package_count=2"' in status.text
    payment_card = status.text.split('aria-labelledby="billing-operation-title">', 1)[1].split("</section>", 1)[0]
    assert payment_card.count('role="status"') == 1
    returned = client.get("/billing/storage?package_count=2", headers=headers)
    assert re.search(r'<option value="2"[^>]*\sselected[^>]*>', returned.text)
    assert 'action="/billing/storage/preview"' in returned.text
    assert 'action="/billing/purchases/confirm"' not in returned.text
    assert payment_counts(client) == before


def seed_saved_card(client, workspace, *, verified_email):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(update(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID,
            ).values(is_verified=verified_email))
            db.add(BillingPaymentMethod(
                workspace_id=workspace, owner_user_id=USER_ID,
                encrypted_provider_ref="synthetic", key_version="synthetic",
                masked_label="Карта •••• 1111", state="active", is_default=True,
                verified_at=datetime.now(UTC),
            ))
            await db.commit()
    asyncio.run(run())


def test_early_renewal_checks_receipt_before_promo_even_without_scheduler_blocker(client, owner):
    workspace, headers = owner
    seed_periods(client, workspace)
    seed_saved_card(client, workspace, verified_email=False)
    before = payment_counts(client)
    page = client.get("/billing/subscription", headers=headers)
    assert 'id="early-promo"' not in page.text
    assert 'action="/billing/subscription/early-preview"' not in page.text
    assert "Подтвердите email для чека" in page.text
    assert "next=%2Fbilling%2Fsubscription" in page.text
    assert payment_counts(client) == before


def test_disabling_renewal_does_not_promise_to_cancel_a_sent_payment(client, owner):
    workspace, headers = owner
    seed_periods(client, workspace)
    seed_payment(client, workspace, state="unknown", kind="renewal")

    async def disable():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(update(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace,
            ).values(recurring_allowed=False))
            await db.commit()
    asyncio.run(disable())
    page = client.get("/billing/subscription", headers=headers)
    assert "Новые автоматические списания отключены" in page.text
    assert "еще может завершиться" in page.text
    assert "Автоматического списания не будет" not in page.text
    assert 'href="/billing/checkout/status/INV-CLARITY"' in page.text


@pytest.mark.parametrize("kind, target", [("initial_checkout", "/billing/checkout?cycle=year"),
                                        ("storage_upgrade", "/billing/storage")])
@pytest.mark.parametrize("state", ["failed", "canceled"])
def test_terminal_history_and_invoice_reach_existing_retry(client, owner, kind, target, state):
    workspace, headers = owner
    seed_payment(client, workspace, state=state, kind=kind)
    for path in ("/billing/history", "/billing/invoices/INV-CLARITY"):
        page = client.get(path, headers=headers)
        assert 'href="/billing/checkout/status/INV-CLARITY"' in page.text
    status = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert f'href="{target}"' in status.text
    assert payment_counts(client) == (1, 1)


@pytest.mark.parametrize("purpose", ["storage", "early"])
def test_invalid_promo_returns_editable_origin_form_without_url_or_cookie(client, owner, purpose):
    workspace, headers = owner
    seed_periods(client, workspace, mixed=True)
    seed_saved_card(client, workspace, verified_email=True)
    before = payment_counts(client)
    path = "/billing/storage/preview" if purpose == "storage" else "/billing/subscription/early-preview"
    promo = "INVALID-DEMO"
    result = client.post(path, data={"package_count": "2", "promo_code": promo}, headers=headers)
    assert result.status_code == 409
    assert "Промокод не распознан" in result.text
    assert f'value="{promo}"' in result.text
    assert 'role="alert"' in result.text
    assert re.search(r'<details[^>]*\bopen\b', result.text)
    assert 'action="/billing/purchases/confirm"' not in result.text
    assert "location" not in result.headers
    assert promo not in result.headers.get("set-cookie", "")
    action, fields = form(result.text, path)
    assert action == path
    assert fields["promo_code"] == promo
    if purpose == "storage":
        assert re.search(r'<option value="2"[^>]*\sselected[^>]*>', result.text)
    else:
        assert "Период оплаты</dt><dd>год</dd>" in result.text
    assert payment_counts(client) == before


@pytest.mark.parametrize("purpose", ["storage", "early"])
@pytest.mark.parametrize("change", ["expired", "changed", "foreign_owner", "foreign_workspace"])
def test_invalid_confirmation_returns_only_owned_fresh_purchase_context(client, owner, purpose, change):
    workspace, headers = owner
    seed_periods(client, workspace)
    seed_saved_card(client, workspace, verified_email=True)
    path = "/billing/storage/preview" if purpose == "storage" else "/billing/subscription/early-preview"
    preview = client.post(path, data={"package_count": "2"}, headers=headers)
    assert preview.status_code == 200
    _, fields = form(preview.text, "/billing/purchases/confirm")
    bound_id = UUID(fields["quote_id"])
    foreign_user, foreign_workspace = seed_second_account(client, "foreign-recovery@example.test")

    async def invalidate():
        async with client.app_state["sessionmaker"]() as db:
            bound = await db.get(BillingPurchaseQuote, bound_id)
            if change == "changed":
                subscription = await db.scalar(select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == workspace,
                ))
                subscription.application_version = (subscription.application_version or 0) + 1
                tested_id = bound.id
            else:
                # Quotes are immutable: seed another historical/foreign offer instead
                # of weakening the database trigger to alter an existing offer.
                tested_id = uuid4()
                db.add(BillingPurchaseQuote(
                    id=tested_id,
                    workspace_id=foreign_workspace if change == "foreign_workspace" else workspace,
                    owner_user_id=foreign_user if change == "foreign_owner" else USER_ID,
                    purpose=bound.purpose, snapshot=bound.snapshot,
                    subscription_version=bound.subscription_version,
                    selection_version=bound.selection_version,
                    created_at=bound.created_at - timedelta(minutes=20) if change == "expired" else bound.created_at,
                    expires_at=bound.expires_at - timedelta(minutes=20) if change == "expired" else bound.expires_at,
                ))
            await db.commit()
            return str(tested_id)
    fields["quote_id"] = asyncio.run(invalidate())
    before = payment_counts(client)
    rejected = client.post("/billing/purchases/confirm", data={
        **fields, "purchase_consent": "true",
    }, headers=headers)
    assert rejected.status_code == 409
    expected = "/billing" if change.startswith("foreign") else (
        "/billing/storage?package_count=2" if purpose == "storage" else "/billing/subscription"
    )
    assert f'href="{expected}"' in rejected.text
    assert 'href="/billing/storage"' not in rejected.text
    if change.startswith("foreign"):
        assert 'href="/billing/subscription"' not in rejected.text.split('<main id="cabinet-main"', 1)[1]
        assert 'href="/billing/storage?package_count=2"' not in rejected.text
    assert 'name="quote_id"' not in rejected.text
    assert 'name="purchase_consent"' not in rejected.text
    assert payment_counts(client) == before


@pytest.mark.parametrize("state", ["unknown", "sent"])
def test_expired_pending_renewal_can_be_revoked_without_canceling_payment(client, owner, state):
    workspace, headers = owner
    expired_at = datetime.now(UTC) - timedelta(minutes=5)
    set_subscription(client, workspace, plan_code="personal", state="personal", cycle="month",
                     paid_through=expired_at, recurring_allowed=True, recurring_authority_version=4)
    seed_payment(client, workspace, state=state, kind="renewal", cycle="month")

    async def cutoff():
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.scalar(select(BillingOperation))
            operation.request_snapshot = {**operation.request_snapshot, "purchase_schema": 2,
                "plan_code": "personal", "recurring_authority_version": 4,
                "paid_through_at": expired_at.isoformat()}
            assert await project_renewal_cutoffs(db, now=datetime.now(UTC)) == 1
            subscription = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace))
            assert subscription.plan_code == "free"
            assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
            await db.commit()
    asyncio.run(cutoff())
    before = payment_counts(client)
    page = client.get("/billing/subscription", headers=headers)
    assert page.status_code == 200
    assert "еще может завершиться" in page.text
    assert 'href="/billing/checkout/status/INV-CLARITY"' in page.text
    assert "Выбрать тариф" not in page.text
    action, fields = form(page.text, "/billing/subscription/cancel")
    assert fields["expected_authority_version"] == "4"

    denied = client.post(action, data={"expected_authority_version": "4"}, follow_redirects=False)
    assert denied.status_code == 403
    stale = client.post(action, headers=headers, data={"expected_authority_version": "3"},
                        follow_redirects=False)
    assert stale.headers["location"] == "/billing/subscription?result=conflict"
    canceled = client.post(action, headers=headers, data=fields)
    assert canceled.status_code == 200
    assert "Новые автоматические списания отключены" in canceled.text
    assert "Доступ сохранится до окончания оплаченного периода" not in canceled.text
    assert "еще может завершиться" in canceled.text
    assert 'href="/billing/checkout/status/INV-CLARITY"' in canceled.text
    assert "Выбрать тариф" not in canceled.text

    async def late_success():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace))
            operation = await db.scalar(select(BillingOperation))
            invoice = await db.scalar(select(BillingInvoice))
            assert not subscription.recurring_allowed and subscription.recurring_authority_version == 5
            assert subscription.paid_through == expired_at
            assert operation.state == state and invoice.status == "pending"
            assert await grant_confirmed_renewal(db, workspace_id=workspace,
                provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                currency=invoice.currency, grant_starts_at=datetime.now(UTC)) == "granted"
            assert subscription.paid_through > datetime.now(UTC)
            assert not subscription.recurring_allowed and subscription.recurring_authority_version == 5
            await db.commit()
    asyncio.run(late_success())
    assert payment_counts(client) == before


@pytest.mark.parametrize("denial", ["member", "different_billing_owner"])
def test_expired_renewal_revocation_preserves_owner_boundary(client, owner, denial):
    workspace, headers = owner
    set_subscription(client, workspace, paid_through=datetime.now(UTC) - timedelta(minutes=5),
                     recurring_allowed=True, recurring_authority_version=4)
    foreign_user, _ = seed_second_account(client, "other-payer@example.test")

    async def change_owner():
        async with client.app_state["sessionmaker"]() as db:
            if denial == "member":
                await db.execute(update(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace,
                    WorkspaceMembership.user_id == USER_ID).values(role="member"))
            else:
                await db.execute(update(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == workspace,
                ).values(billing_owner_id=foreign_user))
            await db.commit()
    asyncio.run(change_owner())
    response = client.post("/billing/subscription/cancel", headers=headers,
                           data={"expected_authority_version": "4"}, follow_redirects=False)
    if denial == "member":
        assert response.status_code == 403
    else:
        assert response.status_code == 303
        assert response.headers["location"] == "/billing/subscription?result=unavailable"

    async def unchanged():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace))
            assert subscription.recurring_allowed and subscription.recurring_authority_version == 4
    asyncio.run(unchanged())
    assert payment_counts(client) == (0, 0)


@pytest.mark.parametrize("hours,recurring", [(47, True), (96, True), (47, False)])
def test_storage_price_confirmation_shows_the_next_actual_attempt(client, owner, hours, recurring):
    workspace, headers = owner
    now = datetime.now(UTC)
    paid_through = now + timedelta(hours=hours)
    set_subscription(client, workspace, plan_code="personal", state="personal", cycle="month",
        capacity_bytes=10_000_000_000, paid_through=paid_through,
        recurring_allowed=recurring, renewal_resolution="price_changed")
    preview = client.post("/billing/storage/preview", headers=headers, data={"package_count": "1"})
    assert preview.status_code == 200
    action, fields = form(preview.text, "/billing/purchases/confirm")
    expected_attempt = next_renewal_attempt(paid_through=paid_through, now=now,
                                          resolved_attempts=set(), unresolved=False)
    expected_label = "не запланировано" if not recurring else (
        "после сохранения выбора, в ближайшее время" if expected_attempt <= now
        else billing._billing_datetime_label(expected_attempt)
    )
    if recurring:
        assert expected_label in preview.text
    else:
        assert "Отключено — автоматического списания не будет" in preview.text
    assert "приостановлено: подтвердите новую цену" not in preview.text
    assert "Сохранить выбор без списания" in preview.text

    async def snapshot():
        async with client.app_state["sessionmaker"]() as db:
            bound = await db.get(BillingPurchaseQuote, UUID(fields["quote_id"]))
            assert bound.purpose == "storage_schedule"
            assert bound.snapshot["payable_amount_minor"] == 0
            assert bound.snapshot["next_amount_minor"] == 125000
            assert bound.snapshot["next_attempt_label"] == expected_label
    asyncio.run(snapshot())
    response = client.post(action, headers=headers, data={**fields, "purchase_consent": "true"},
                           follow_redirects=False)
    assert response.headers["location"] == "/billing/storage?result=scheduled"

    async def saved():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace))
            assert subscription.renewal_resolution is None
            assert subscription.recurring_allowed == recurring
            assert subscription.paid_through == paid_through
            assert subscription.next_capacity_bytes == 10_000_000_000
            operations = list(await db.scalars(select(BillingOperation)))
            assert len(operations) == 1 and operations[0].kind == "storage_schedule"
            assert operations[0].state == "succeeded"
    asyncio.run(saved())
    assert payment_counts(client) == (1, 0)


@pytest.mark.parametrize("case", ["malformed", "missing", "expired", "future"])
def test_discounts_error_preserves_exact_input_through_checkout_refresh(client, owner, case):
    _, headers = owner
    async def verified_receipt_email():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(update(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID, ExternalIdentity.provider == "email",
            ).values(is_verified=True))
            await db.commit()
    asyncio.run(verified_receipt_email())
    promo = 'TYPO<"&' if case == "malformed" else "SYNTH-TYPO"
    if case in {"expired", "future"}:
        async def campaign():
            async with client.app_state["sessionmaker"]() as db:
                now = datetime.now(UTC)
                db.add(PromotionCampaign(code_hash=promo_code_hash(promo), campaign_version="synthetic",
                    plan_code="personal", cycle="month", discount_percent=10, max_redemptions=1, enabled=True,
                    starts_at=now + timedelta(days=1) if case == "future" else now - timedelta(days=2),
                    ends_at=now + timedelta(days=2) if case == "future" else now - timedelta(days=1)))
                await db.commit()
        asyncio.run(campaign())
    response = client.post("/billing/discounts/apply", headers=headers, data={"promo_code": promo},
                           follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/billing/checkout?result=promo_invalid"
    assert promo not in response.headers["location"]
    assert promo not in response.headers.get("set-cookie", "")
    for _ in range(2):
        page = client.get(response.headers["location"], headers=headers)
        assert page.status_code == 200
        field = re.search(r'<input[^>]*id="billing-promo"[^>]*>', page.text)
        assert field and unescape(re.search(r'value="([^"]*)"', field.group(0)).group(1)) == promo
        assert 'aria-invalid="true"' in field.group(0)
        assert 'aria-describedby="billing-checkout-error"' in field.group(0)
        assert 'action="/billing/checkout/start"' not in page.text
        if case == "malformed":
            assert promo not in page.text
    fresh = client.get("/billing/discounts", headers=headers)
    assert form(fresh.text, "/billing/discounts/apply")[1]["promo_code"] == ""
    assert payment_counts(client) == (0, 0)


@pytest.mark.parametrize("role", ["owner", "member"])
def test_manual_resolution_created_by_failure_has_owner_only_status_recovery(client, owner, role):
    workspace, headers = owner
    seed_payment(client, workspace, state="processing")

    async def record_failure():
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.scalar(select(BillingOperation))
            invoice = await db.scalar(select(BillingInvoice))
            operation.provider_id = None
            operation.request_snapshot = {**operation.request_snapshot, "purchase_schema": 2}
            billing._record_initial_checkout_failure(operation, invoice, httpx.ReadTimeout("synthetic"))
            assert operation.state == invoice.status == "manual_resolution"
            if role == "member":
                await db.execute(update(WorkspaceMembership).where(
                    WorkspaceMembership.workspace_id == workspace,
                    WorkspaceMembership.user_id == USER_ID).values(role="member"))
            await db.commit()
    asyncio.run(record_failure())
    for path in ("/billing/history", "/billing/invoices/INV-CLARITY"):
        page = client.get(path, headers=headers, follow_redirects=False)
        assert ('href="/billing/checkout/status/INV-CLARITY"' in page.text) == (role == "owner")
    status = client.get("/billing/checkout/status/INV-CLARITY", headers=headers, follow_redirects=False)
    assert ('action="/billing/checkout/status/INV-CLARITY/refresh"' in status.text) == (role == "owner")
    assert 'action="/billing/checkout/start"' not in status.text
    assert payment_counts(client) == (1, 1)


@pytest.mark.parametrize("state,provider_known", [("scheduled", False), ("scheduled", True),
                                                ("sent", False), ("unknown", False)])
def test_prepared_renewal_allows_early_payment_but_sent_or_unknown_still_block(
    client, owner, monkeypatch, state, provider_known
):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    seed_saved_card(client, workspace, verified_email=True)
    set_subscription(client, workspace, recurring_allowed=True)
    seed_payment(client, workspace, state=state, kind="renewal")

    async def prepare():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace))
            operation = await db.scalar(select(BillingOperation).where(
                BillingOperation.idempotency_key == "clarity-existing"))
            operation.provider_id = operation.provider_id if provider_known else None
            operation.request_snapshot = {**operation.request_snapshot,
                "paid_through_at": subscription.paid_through.isoformat(), "renewal_attempt": 1}
            method = await db.scalar(select(BillingPaymentMethod))
            method.key_version = "billing-v1"
            method.encrypted_provider_ref = seal_provider_reference("synthetic-saved-card",
                read_billing_encryption_key(client.app.state.settings.credential_encryption_key_file))
            await db.commit()
            return operation.id
    operation_id = asyncio.run(prepare())
    safe_prepared = state == "scheduled" and not provider_known
    page = client.get("/billing/subscription", headers=headers)
    assert page.status_code == 200
    assert ('action="/billing/subscription/early-preview"' in page.text) == safe_prepared
    assert ("Подготовлено автоматическое списание" in page.text) == safe_prepared
    assert ("Уже отправленный платеж" in page.text) != safe_prepared
    before = payment_counts(client)
    preview = client.post("/billing/subscription/early-preview", headers=headers,
                          data={"promo_code": "SYNTHEARLY"})
    action, fields = form(preview.text, "/billing/purchases/confirm")
    provider = _FakeYooKassa()
    monkeypatch.setattr(billing, "YooKassaClient", lambda settings: YooKassaClient(
        settings, transport=httpx.MockTransport(provider.handle)))
    confirmed = client.post(action, headers=headers, data={**fields, "purchase_consent": "true"},
                            follow_redirects=False)
    assert confirmed.status_code == 303
    assert len(provider.create_payloads) == int(safe_prepared)
    assert payment_counts(client) == tuple(value + int(safe_prepared) for value in before)
    if not safe_prepared:
        assert confirmed.headers["location"] == "/billing/checkout/status/INV-CLARITY"

    async def existing_payment():
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.get(BillingOperation, operation_id)
            invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.operation_id == operation_id))
            assert operation.state == ("canceled" if safe_prepared else state)
            assert invoice.status == ("canceled" if safe_prepared else "pending")
    asyncio.run(existing_payment())
