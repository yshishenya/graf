"""Short-lived promo choices survive refresh without authorizing a payment."""

import asyncio
import re
import time
from datetime import UTC, datetime, timedelta
from html import unescape
from http.cookies import SimpleCookie

import pytest
from sqlalchemy import select

from tests.integration.test_billing_clarity import seed_payment
from tests.integration.test_billing_discount_presentation import (
    assert_checkout,
    seed_campaign,
)
from tests.integration.test_billing_discount_presentation import (
    owner as owner,
)
from tests.unit.test_billing_money_path_e2e import ORG_ID, USER_ID
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.billing.promotions import promo_code_hash
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    BillingInvoice,
    BillingOperation,
    ExternalIdentity,
    PromotionCampaign,
    PromotionRedemption,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

DRAFT_COOKIE = "graf_checkout_promo_draft"
SYNTH_CODE = "SYNTH-PRESENTATION"


@pytest.fixture(autouse=True)
def no_financial_side_effects(client):
    client.promo_expected_financial_rows = {}
    client.promo_expected_financial_contents = {}
    yield

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            for model in (BillingOperation, BillingInvoice, PromotionRedemption):
                expected = getattr(client, "promo_expected_financial_rows", {}).get(model, set())
                rows = (await db.execute(select(model.__table__))).mappings().all()
                assert {row["id"] for row in rows} == expected
                contents = client.promo_expected_financial_contents.get(model)
                if contents is not None:
                    assert {row["id"]: dict(row) for row in rows} == contents

    asyncio.run(inspect())


def capture_financial_baseline(client):
    async def capture():
        async with client.app_state["sessionmaker"]() as db:
            for model in (BillingOperation, BillingInvoice):
                rows = (await db.execute(select(model.__table__))).mappings().all()
                client.promo_expected_financial_contents[model] = {row["id"]: dict(row) for row in rows}
                client.promo_expected_financial_rows[model] = {row["id"] for row in rows}
    asyncio.run(capture())


def submit(client, headers, code=SYNTH_CODE, *, cycle="month", action="apply",
           previous_code=SYNTH_CODE):
    response = client.post("/billing/checkout/preview", headers=headers,
                           data={"cycle": cycle, "promo_code": code, "preview_action": action,
                                 "previous_promo_code": previous_code},
                           follow_redirects=False)
    assert response.status_code == 303
    return response


def draft_cookie(response):
    for header in response.headers.get_list("set-cookie"):
        cookie = SimpleCookie(header)
        if DRAFT_COOKIE in cookie and cookie[DRAFT_COOKIE].value:
            return cookie[DRAFT_COOKIE]
    pytest.fail("Explicit promo application must issue protected draft state")


def keep_cookie_on_controlled_clock(client):
    """The server clock is frozen; do not let httpx's real clock win instead."""
    for cookie in client.cookies.jar:
        if cookie.name == DRAFT_COOKIE:
            cookie.expires = None


def assert_no_draft_renewal(response):
    assert not any(DRAFT_COOKIE in header and "Max-Age=0" not in header
                   for header in response.headers.get_list("set-cookie"))


def assert_plain_checkout(response):
    assert_checkout(response, today="1000", renewal="1000", cycle="месяц", promo="")


def promo_input(response, *, status=200):
    assert response.status_code == status
    field = re.search(r'<input[^>]*id="billing-promo"[^>]*>', response.text)
    assert field, "Checkout must retain the editable promo field"
    return unescape(re.search(r'value="([^"]*)"', field.group(0)).group(1))


def test_applied_discount_survives_two_refreshes(client, owner):
    _, headers = owner
    seed_campaign(client)
    applied = client.post("/billing/discounts/apply", headers=headers,
                          data={"promo_code": "SYNTH-PRESENTATION"}, follow_redirects=False)
    assert applied.status_code == 303
    for _ in range(3):
        assert_checkout(client.get(applied.headers["location"]),
                        today="900", renewal="1000", cycle="месяц",
                        promo="SYNTH-PRESENTATION")


@pytest.mark.parametrize("code", [
    pytest.param("SYNTH-UNKNOWN", id="unknown"),
    pytest.param('<img src=x onerror="alert(1)">', id="escaped-markup"),
    pytest.param("AB", id="too-short"),
    pytest.param("ТЕСТКОД", id="non-ascii"),
    pytest.param("AB\tC\nD\x01", id="control-characters"),
    pytest.param("[" * 48, id="max48-malformed"),
])
@pytest.mark.parametrize("apply_route", ["/billing/checkout/preview", "/billing/discounts/apply"])
def test_invalid_input_stays_editable_and_escaped_after_redirect_and_refresh(client, owner, code, apply_route):
    _, headers = owner
    applied = client.post(apply_route, headers=headers,
                          data={"cycle": "year", "promo_code": code}, follow_redirects=False)
    assert applied.status_code == 303
    for _ in range(3):
        page = client.get(applied.headers["location"])
        assert promo_input(page) == code
        assert 'id="billing-checkout-error"' in page.text
        assert 'action="/billing/checkout/start"' not in page.text
        if code.startswith("<"):
            assert code not in page.text


def test_period_switch_submits_current_input_and_preserves_annual_refresh(client, owner):
    _, headers = owner
    seed_campaign(client)
    page = client.get("/billing/checkout?cycle=year")
    for action, current, today, renewal, label in [
        ("month", "year", "900", "1000", "месяц"),
        ("year", "month", "9000", "10000", "год"),
    ]:
        # The browser submits the newly entered field together with the pressed
        # period button; no previous Apply or stale hidden promo is required.
        changed = submit(client, headers, cycle=current, action=action,
                         previous_code="" if action == "month" else SYNTH_CODE)
        page = client.get(changed.headers["location"])
        assert_checkout(page, today=today, renewal=renewal, cycle=label, promo=SYNTH_CODE)
    for _ in range(2):
        page = client.get("/billing/checkout")
        assert_checkout(page, today="9000", renewal="10000", cycle="год", promo=SYNTH_CODE)
        assert_no_draft_renewal(page)


@pytest.mark.parametrize("remove", ["empty", "explicit"])
def test_clearing_promo_survives_refresh(client, owner, remove):
    _, headers = owner
    seed_campaign(client)
    applied = submit(client, headers)
    assert_checkout(client.get(applied.headers["location"]),
                    today="900", renewal="1000", cycle="месяц", promo=SYNTH_CODE)
    if remove == "empty":
        cleared = submit(client, headers, code="")
    else:
        cleared = client.post("/billing/discounts/remove", headers=headers,
                              follow_redirects=False)
        assert cleared.status_code == 303
    for _ in range(2):
        assert_plain_checkout(client.get("/billing/checkout"))


def test_expiry_is_fixed_and_get_period_changes_and_start_errors_do_not_renew(client, owner, monkeypatch):
    _, headers = owner
    seed_campaign(client)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0], raising=False)
    applied = submit(client, headers)
    assert draft_cookie(applied)["max-age"] == "300"
    initial_expiry = clock[0] + 300
    clock[0] += 299
    page = client.get(applied.headers["location"])
    assert_checkout(page, today="900", renewal="1000", cycle="месяц", promo=SYNTH_CODE)
    assert_no_draft_renewal(page)
    switched = submit(client, headers, cycle="month", action="year")
    assert int(draft_cookie(switched)["max-age"]) <= initial_expiry - clock[0]
    keep_cookie_on_controlled_clock(client)
    start_error = client.post("/billing/checkout/start", headers=headers,
                              data={"cycle": "year", "promo_code": SYNTH_CODE},
                              follow_redirects=False)
    assert start_error.status_code == 303
    assert int(draft_cookie(start_error)["max-age"]) <= initial_expiry - clock[0]
    keep_cookie_on_controlled_clock(client)
    clock[0] = initial_expiry
    assert_plain_checkout(client.get("/billing/checkout"))
    for action in ("month", "year"):
        stale_period = submit(client, headers, cycle="year", action=action)
        assert_no_draft_renewal(stale_period)
        page = client.get(stale_period.headers["location"])
        assert "Промокод больше не сохранен" in page.text
        assert "снова проверить скидку" in page.text
        assert re.search(r'<details class="billing-coupon" open>', page.text)
        assert_plain_checkout(client.get("/billing/checkout"))
    stale_start = client.post("/billing/checkout/start", headers=headers,
                              data={"cycle": "year", "promo_code": SYNTH_CODE},
                              follow_redirects=False)
    assert stale_start.status_code == 303
    assert_no_draft_renewal(stale_start)


@pytest.mark.parametrize("attack", ["legacy", "renamed", "tamper"])
def test_raw_legacy_or_modified_state_is_ignored(client, owner, attack):
    _, headers = owner
    seed_campaign(client)
    if attack == "legacy":
        client.cookies.set("graf_checkout_promo", SYNTH_CODE, path="/billing/checkout")
    else:
        value = draft_cookie(submit(client, headers)).value
        auth_token = client.cookies.get(AUTH_SESSION_COOKIE_NAME)
        client.cookies.clear()
        client.cookies.set(AUTH_SESSION_COOKIE_NAME, auth_token)
        if attack == "renamed":
            client.cookies.set("graf_checkout_promo", value, path="/billing/checkout")
        else:
            value = ("A" if value[0] != "A" else "B") + value[1:]
            client.cookies.set(DRAFT_COOKIE, value, path="/billing/checkout")
    assert_plain_checkout(client.get("/billing/checkout"))


def change_verified_context(client, *, boundary):
    """Change one verified boundary while preserving the other two, in test DB."""
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            session = await db.scalar(select(AuthSession).where(AuthSession.user_id == USER_ID))
            device = await db.get(RegisteredDevice, session.device_id)
            if boundary == "session":
                issued = await issue_auth_session(db, user_id=USER_ID,
                                                 workspace_id=session.workspace_id,
                                                 device_id=device.id, provider="email")
                db.add(AuthSessionDeviceBinding(auth_session_id=issued.id,
                                                registered_device_id=device.id,
                                                device_state="trusted"))
                await db.commit()
                return issued.token
            workspace = await db.get(Workspace, session.workspace_id)
            if boundary == "user":
                user = UserIdentity(organization_id=ORG_ID, external_subject="synthetic-new-owner")
                db.add(user)
                await db.flush()
                db.add(WorkspaceMembership(workspace_id=workspace.id, user_id=user.id,
                                           role="owner", status="active"))
                db.add(ExternalIdentity(user_id=user.id, provider="email",
                                        provider_subject="synthetic-new-owner",
                                        email="synthetic-new-owner@example.test",
                                        is_verified=True, is_active=True))
                workspace.owner_user_id = user.id
                session.user_id = device.user_id = device.trusted_by = user.id
            else:
                workspace.kind = "corporate"
                await db.flush()
                other = Workspace(organization_id=ORG_ID, slug="synthetic-other",
                                  name="Synthetic other", kind="personal", owner_user_id=USER_ID)
                db.add(other)
                await db.flush()
                db.add(WorkspaceMembership(workspace_id=other.id, user_id=USER_ID,
                                           role="owner", status="active"))
                session.workspace_id = device.workspace_id = other.id
            await db.commit()

    token = asyncio.run(run())
    if token:
        client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)


@pytest.mark.parametrize("boundary", ["user", "workspace", "session"])
def test_draft_is_bound_to_verified_user_workspace_and_session(client, owner, boundary):
    _, headers = owner
    seed_campaign(client)
    applied = submit(client, headers)
    assert_checkout(client.get(applied.headers["location"]),
                    today="900", renewal="1000", cycle="месяц", promo=SYNTH_CODE)
    change_verified_context(client, boundary=boundary)
    assert_plain_checkout(client.get("/billing/checkout"))


@pytest.mark.parametrize("change", ["disabled", "exhausted"])
def test_refresh_rechecks_campaign_and_blocks_payment_without_losing_input(client, owner, change):
    _, headers = owner
    campaign_id = seed_campaign(client)
    applied = submit(client, headers)
    assert_checkout(client.get(applied.headers["location"]),
                    today="900", renewal="1000", cycle="месяц", promo=SYNTH_CODE)

    async def mutate():
        async with client.app_state["sessionmaker"]() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            if change == "disabled":
                campaign.enabled = False
            else:
                campaign.redeemed_count = campaign.max_redemptions
            await db.commit()

    asyncio.run(mutate())
    for _ in range(2):
        page = client.get("/billing/checkout")
        assert promo_input(page) == SYNTH_CODE
        assert 'id="billing-checkout-error"' in page.text
        assert 'action="/billing/checkout/start"' not in page.text


def test_protected_state_has_safe_cookie_flags_and_no_raw_code_in_url_headers_or_logs(client, owner, caplog):
    _, headers = owner
    seed_campaign(client)
    applied = client.post("https://testserver/billing/checkout/preview", headers=headers,
                          data={"cycle": "month", "promo_code": SYNTH_CODE},
                          follow_redirects=False)
    assert applied.status_code == 303
    cookie = draft_cookie(applied)
    assert cookie["max-age"] == "300"
    assert cookie["path"] == "/billing/checkout"
    assert cookie["httponly"] and cookie["secure"]
    assert cookie["samesite"].lower() == "lax"
    assert SYNTH_CODE not in str(applied.url)
    assert all(SYNTH_CODE not in value for _, value in applied.headers.multi_items())
    assert all(SYNTH_CODE not in record.getMessage() for record in caplog.records)


def test_missing_verified_session_cannot_reuse_promo_state(client, owner):
    _, headers = owner
    seed_campaign(client)
    submit(client, headers)
    client.cookies.delete(AUTH_SESSION_COOKIE_NAME)
    page = client.get("/billing/checkout", follow_redirects=False)
    assert SYNTH_CODE not in page.text
    assert 'action="/billing/checkout/start"' not in page.text


def test_missing_signing_key_has_no_unsigned_fallback(client, owner, monkeypatch):
    _, headers = owner
    seed_campaign(client)
    applied = submit(client, headers)
    assert draft_cookie(applied).value
    monkeypatch.setattr(client.app.state, "web_csrf_secret", None)
    page = client.get("/billing/checkout")
    assert SYNTH_CODE not in page.text
    assert_no_draft_renewal(page)


def test_max49_input_is_rejected_without_creating_draft(client, owner):
    _, headers = owner
    response = client.post("/billing/checkout/preview", headers=headers,
                           data={"cycle": "month", "promo_code": "X" * 49},
                           follow_redirects=False)
    assert response.status_code == 422
    assert_no_draft_renewal(response)
    assert_plain_checkout(client.get("/billing/checkout"))


@pytest.mark.parametrize("action,replacement", [("apply", False), ("apply", True), ("year", True)])
def test_explicit_apply_or_replacement_starts_its_own_fixed_expiry(client, owner, monkeypatch, action, replacement):
    _, headers = owner
    seed_campaign(client)
    code = SYNTH_CODE
    if replacement:
        code = "SYNTH-SECOND"
        seed_campaign(client, code_hash=promo_code_hash(code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0], raising=False)
    first = submit(client, headers)
    assert draft_cookie(first)["max-age"] == "300"
    clock[0] += 299
    replaced = submit(client, headers, code=code, action=action, previous_code=SYNTH_CODE)
    assert draft_cookie(replaced)["max-age"] == "300"
    new_expiry = clock[0] + 300
    clock[0] += 2
    assert_checkout(client.get("/billing/checkout"),
                    today="7500" if action == "year" else "750" if replacement else "900",
                    renewal="10000" if action == "year" else "1000",
                    cycle="год" if action == "year" else "месяц", promo=code)
    clock[0] = new_expiry
    assert_plain_checkout(client.get("/billing/checkout"))


@pytest.mark.parametrize("subscription_cycle", ["year", "month", "none", "unknown"])
@pytest.mark.parametrize("code", [SYNTH_CODE, "SYNTH-UNKNOWN"])
def test_discounts_apply_keeps_subscription_period_or_month_fallback(
    client, owner, code, subscription_cycle
):
    workspace, headers = owner
    seed_campaign(client)

    async def set_cycle():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.get(WorkspaceSubscription, workspace)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID)
                db.add(subscription)
            subscription.cycle = subscription_cycle
            await db.commit()

    asyncio.run(set_cycle())
    applied = client.post("/billing/discounts/apply", headers=headers,
                          data={"promo_code": code}, follow_redirects=False)
    assert applied.status_code == 303
    cycle = "year" if subscription_cycle == "year" else "month"
    if subscription_cycle in {"month", "year"}:
        assert f"cycle={cycle}" in applied.headers["location"]
    for _ in range(3):
        page = client.get("/billing/checkout")
        assert promo_input(page) == code
        assert f'value="{cycle}"' in page.text
        if code == SYNTH_CODE:
            assert_checkout(page, today="9000" if cycle == "year" else "900",
                            renewal="10000" if cycle == "year" else "1000",
                            cycle="год" if cycle == "year" else "месяц", promo=code)
        else:
            assert 'id="billing-checkout-error"' in page.text
            assert 'action="/billing/checkout/start"' not in page.text


@pytest.mark.parametrize("stale_code", [SYNTH_CODE, ""])
@pytest.mark.parametrize("action", ["month", "year"])
def test_unchanged_stale_tab_period_uses_latest_draft_without_renewal(
    client, owner, monkeypatch, stale_code, action
):
    _, headers = owner
    seed_campaign(client)
    latest_code = "SYNTH-SECOND"
    seed_campaign(client, code_hash=promo_code_hash(latest_code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    if stale_code:
        submit(client, headers)
    latest = submit(client, headers, code=latest_code)
    assert draft_cookie(latest)["max-age"] == "300"
    clock[0] += 299
    switched = submit(client, headers, code=stale_code, action=action,
                      previous_code=stale_code)
    assert draft_cookie(switched)["max-age"] == "1"
    keep_cookie_on_controlled_clock(client)
    for _ in range(2):
        assert_checkout(client.get("/billing/checkout"),
                        today="7500" if action == "year" else "750",
                        renewal="10000" if action == "year" else "1000",
                        cycle="год" if action == "year" else "месяц", promo=latest_code)
    clock[0] += 1
    assert_plain_checkout(client.get("/billing/checkout"))



def test_stale_start_error_preserves_latest_draft_and_actual_receipt_guard(client, owner, monkeypatch):
    _, headers = owner
    seed_campaign(client)
    latest_code = "SYNTH-SECOND"
    seed_campaign(client, code_hash=promo_code_hash(latest_code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers)
    submit(client, headers, code=latest_code, cycle="year")

    async def unverify_email():
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(select(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID, ExternalIdentity.provider == "email"))
            identity.is_verified = False
            await db.commit()

    asyncio.run(unverify_email())
    clock[0] += 299
    rejected = client.post("/billing/checkout/start", headers=headers,
                           data={"cycle": "month", "promo_code": SYNTH_CODE,
                                 "idempotency_key": "synthetic-stale-start",
                                 "offer_consent": "true", "recurring_consent": "true"},
                           follow_redirects=False)
    assert rejected.status_code == 303
    assert "result=receipt_contact_required" in rejected.headers["location"]
    assert draft_cookie(rejected)["max-age"] == "1"
    keep_cookie_on_controlled_clock(client)
    page = client.get(rejected.headers["location"])
    assert promo_input(page) == latest_code
    assert 'name="cycle" value="year"' in page.text
    assert 'action="/billing/checkout/start"' not in page.text
    assert "Подтвердите email" in page.text
    clock[0] += 1
    assert promo_input(client.get("/billing/checkout")) == ""


def test_unverified_receipt_allows_readonly_promo_correction_and_clear(client, owner):
    _, headers = owner
    seed_campaign(client)

    async def unverify_email():
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(select(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID, ExternalIdentity.provider == "email"))
            identity.is_verified = False
            await db.commit()

    asyncio.run(unverify_email())
    rejected = client.post("/billing/discounts/apply", headers=headers,
                           data={"promo_code": "SYNTH-UNKNOWN"}, follow_redirects=False)
    assert rejected.status_code == 303
    assert promo_input(client.get(rejected.headers["location"])) == "SYNTH-UNKNOWN"
    for code in (SYNTH_CODE, ""):
        preview = submit(client, headers, code=code)
        page = client.get(preview.headers["location"])
        assert promo_input(page) == code
        assert 'action="/billing/checkout/start"' not in page.text
        assert "Подтвердите email" in page.text
        assert 'name="preview_action" value="apply"' in page.text


@pytest.mark.parametrize("command", ["replace", "clear", "expired"])
def test_stale_tab_explicit_actions_and_expired_latest_choice(client, owner, monkeypatch, command):
    _, headers = owner
    seed_campaign(client)
    latest_code = "SYNTH-SECOND"
    seed_campaign(client, code_hash=promo_code_hash(latest_code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers)
    submit(client, headers, code=latest_code)
    clock[0] += 300 if command == "expired" else 299
    response = submit(client, headers, code="" if command == "clear" else SYNTH_CODE,
                      action="year" if command == "expired" else "apply",
                      previous_code=SYNTH_CODE)
    if command == "replace":
        assert draft_cookie(response)["max-age"] == "300"
        assert_checkout(client.get("/billing/checkout"), today="900", renewal="1000",
                        cycle="месяц", promo=SYNTH_CODE)
    else:
        assert_no_draft_renewal(response)
        assert_plain_checkout(client.get("/billing/checkout"))
        if command == "expired":
            assert "result=promo_expired" in response.headers["location"]
            assert "Промокод больше не сохранен" in client.get(response.headers["location"]).text


def test_stale_period_rechecks_latest_campaign_instead_of_using_old_valid_code(client, owner, monkeypatch):
    _, headers = owner
    seed_campaign(client)
    latest_code = "SYNTH-SECOND"
    campaign_id = seed_campaign(client, code_hash=promo_code_hash(latest_code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers)
    submit(client, headers, code=latest_code)

    async def disable_latest():
        async with client.app_state["sessionmaker"]() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            campaign.enabled = False
            await db.commit()

    asyncio.run(disable_latest())
    clock[0] += 299
    response = submit(client, headers, action="year", previous_code=SYNTH_CODE)
    assert "result=promo_invalid" in response.headers["location"]
    assert draft_cookie(response)["max-age"] == "1"
    keep_cookie_on_controlled_clock(client)
    page = client.get(response.headers["location"])
    assert promo_input(page) == latest_code
    assert 'action="/billing/checkout/start"' not in page.text
    assert 'id="billing-checkout-error"' in page.text


@pytest.mark.parametrize("stale_code", ["SYNTH-UNKNOWN", "[bad code]"])
@pytest.mark.parametrize("action", ["month", "year"])
def test_expired_latest_draft_explains_loss_for_unchanged_invalid_stale_input(
    client, owner, monkeypatch, stale_code, action
):
    _, headers = owner
    seed_campaign(client)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers, code=stale_code)
    submit(client, headers)
    clock[0] += 300
    response = submit(client, headers, code=stale_code, action=action, previous_code=stale_code)
    assert "result=promo_expired" in response.headers["location"]
    assert_no_draft_renewal(response)
    page = client.get(response.headers["location"])
    assert promo_input(page) == ""
    assert "Промокод больше не сохранен" in page.text
    assert "снова проверить скидку" in page.text
    assert re.search(r'<details class="billing-coupon" open>', page.text)


@pytest.mark.parametrize("guard", ["unavailable", "catalog_not_approved"])
def test_expired_stale_input_does_not_hide_preview_guard(client, owner, monkeypatch, guard):
    _, headers = owner
    seed_campaign(client)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers, code="[bad code]")
    clock[0] += 300
    if guard == "unavailable":
        monkeypatch.setattr(routes, "billing_checkout_allowed", lambda *_args: False)
    else:
        async def no_catalog(*_args, **_kwargs):
            return {}
        monkeypatch.setattr(routes, "_approved_personal_catalog", no_catalog)
    response = submit(client, headers, code="[bad code]", action="year", previous_code="[bad code]")
    assert f"result={guard}" in response.headers["location"]
    assert "promo_expired" not in response.headers["location"]
    assert_no_draft_renewal(response)



def checkout_start_fields(page):
    values = {
        match[1]: unescape(match[2])
        for match in re.finditer(r'<input[^>]*name="([^"]+)"[^>]*value="([^"]*)"', page.text)
    }
    return {name: values[name] for name in ("cycle", "idempotency_key", "quote_id", "offer_version")}


@pytest.mark.parametrize("state", ["succeeded", "failed", "canceled"])
def test_historical_status_get_preserves_other_checkout_draft(client, owner, monkeypatch, state):
    workspace, headers = owner
    seed_campaign(client)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])

    async def historical_invoice():
        async with client.app_state["sessionmaker"]() as db:
            operation = BillingOperation(workspace_id=workspace, kind="initial_checkout", state=state,
                                         idempotency_key="synthetic-old-payment", request_snapshot={})
            db.add(operation)
            await db.flush()
            invoice = BillingInvoice(workspace_id=workspace, operation_id=operation.id,
                                     safe_number="INV-SYNTH-OLDER", amount_minor=100000,
                                     status=state, plan_snapshot={"cycle": "month"},
                                     created_at=datetime.now(UTC) - timedelta(days=60))
            db.add(invoice)
            await db.commit()
            return operation.id, invoice.id

    asyncio.run(historical_invoice())
    capture_financial_baseline(client)
    applied = submit(client, headers, cycle="year")
    before = draft_cookie(applied).value
    clock[0] += 299
    for _ in range(2):
        status = client.get("/billing/checkout/status/INV-SYNTH-OLDER")
        assert status.status_code == 200
        assert_no_draft_renewal(status)
        assert not any(DRAFT_COOKIE in header for header in status.headers.get_list("set-cookie"))
        assert client.cookies.get(DRAFT_COOKIE) == before
        assert_checkout(client.get("/billing/checkout"), today="9000", renewal="10000",
                        cycle="год", promo=SYNTH_CODE)
    clock[0] += 1
    assert_plain_checkout(client.get("/billing/checkout"))
    submit(client, headers, cycle="year")
    recovered = client.post("/billing/checkout/start", headers=headers, data={
        "cycle": "year", "promo_code": SYNTH_CODE,
        "idempotency_key": "synthetic-old-payment",
        "offer_consent": "true", "recurring_consent": "true",
    }, follow_redirects=False)
    assert recovered.status_code == 303
    assert recovered.headers["location"] == "/billing/checkout/status/INV-SYNTH-OLDER"
    assert any(DRAFT_COOKIE in header and "Max-Age=0" in header
               for header in recovered.headers.get_list("set-cookie"))
    assert_plain_checkout(client.get("/billing/checkout"))


@pytest.mark.parametrize("reason", ["offer_changed", "quote_changed"])
@pytest.mark.parametrize("selection", ["latest", "unchanged", "expired", "absent", "tampered", "foreign_session", "disabled"])
def test_direct_stale_start_rejection_uses_verified_draft_only(
    client, owner, monkeypatch, reason, selection
):
    _, headers = owner
    seed_campaign(client)
    latest_code = "SYNTH-SECOND"
    seed_campaign(client, code_hash=promo_code_hash(latest_code), discount_percent=25)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    submit(client, headers)
    first = client.get("/billing/checkout")
    fields = checkout_start_fields(first)
    if selection in {"latest", "expired", "tampered", "foreign_session", "disabled"}:
        submit(client, headers, code=latest_code, cycle="year")
    if selection in {"tampered", "foreign_session"}:
        saved_token = client.cookies.get(DRAFT_COOKIE)
        client.cookies.delete(DRAFT_COOKIE)
        if selection == "tampered":
            saved_token = ("A" if saved_token[0] != "A" else "B") + saved_token[1:]
        else:
            change_verified_context(client, boundary="session")
            session_response = client.get("/billing/checkout")
            csrf = re.search(r'name="csrf_token" value="([^"]+)"', session_response.text)
            headers = {"X-CSRF-Token": unescape(csrf[1])}
        client.cookies.set(DRAFT_COOKIE, saved_token, path="/billing/checkout")
    elif selection == "absent":
        client.cookies.delete(DRAFT_COOKIE)
    elif selection == "disabled":
        async def disable_latest():
            async with client.app_state["sessionmaker"]() as db:
                campaign = await db.scalar(select(PromotionCampaign).where(
                    PromotionCampaign.code_hash == promo_code_hash(latest_code)))
                campaign.enabled = False
                await db.commit()
        asyncio.run(disable_latest())
    clock[0] += 300 if selection == "expired" else 299
    if reason == "offer_changed":
        fields["offer_version"] = "synthetic-outdated-offer"
    else:
        fields["quote_id"] = "00000000-0000-0000-0000-000000000000"
    response = client.post("/billing/checkout/start", headers=headers, data={
        **fields, "promo_code": SYNTH_CODE,
        "offer_consent": "true", "recurring_consent": "true",
    }, follow_redirects=False)
    expected_code = latest_code if selection in {"latest", "disabled"} else SYNTH_CODE if selection == "unchanged" else ""
    assert promo_input(response, status=409) == expected_code
    expected_cycle = "year" if selection in {"latest", "disabled"} else "month"
    assert f'name="cycle" value="{expected_cycle}"' in response.text
    assert "Условия оплаты изменились" in response.text if reason == "offer_changed" else "Расчет изменился или устарел" in response.text
    assert_no_draft_renewal(response)
    for name in ("offer_consent", "recurring_consent"):
        checkbox = re.search(rf'<input[^>]*name="{name}"[^>]*>', response.text)
        if selection == "disabled":
            assert checkbox is None
        else:
            assert checkbox and "checked" not in checkbox.group(0)
    for _ in range(2):
        page = client.get("/billing/checkout")
        if selection == "disabled":
            assert promo_input(page) == latest_code
            assert 'id="billing-checkout-error"' in page.text
            assert 'action="/billing/checkout/start"' not in page.text
            continue
        assert_checkout(page, today="7500" if selection == "latest" else "900" if selection == "unchanged" else "1000",
                        renewal="10000" if selection == "latest" else "1000",
                        cycle="год" if selection == "latest" else "месяц", promo=expected_code)
    if selection in {"latest", "unchanged"}:
        clock[0] += 1
        assert_plain_checkout(client.get("/billing/checkout"))


@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade"])
@pytest.mark.parametrize("access", ["allowed", "disabled", "foreign_actor"])
def test_existing_hosted_continue_clears_only_after_authorized_handoff(client, owner, monkeypatch, kind, access):
    workspace, headers = owner
    seed_campaign(client)
    hosted_url = "https://yookassa.test/checkout/synthetic-existing"
    seed_payment(client, workspace, kind=kind, state="provider_pending", confirmation_url=hosted_url)
    if access == "foreign_actor":
        async def foreign_actor():
            async with client.app_state["sessionmaker"]() as db:
                operation = await db.scalar(select(BillingOperation))
                operation.request_snapshot = {**operation.request_snapshot,
                                              "billing_actor_user_id": "synthetic-other-actor"}
                await db.commit()
        asyncio.run(foreign_actor())
    capture_financial_baseline(client)
    before = draft_cookie(submit(client, headers, cycle="year")).value
    if access == "disabled":
        monkeypatch.setattr(routes, "billing_checkout_allowed", lambda *_args: False)
    response = client.post("/billing/checkout/status/INV-CLARITY/continue", headers=headers,
                           follow_redirects=False)
    assert response.status_code == 303
    if access == "allowed":
        assert response.headers["location"] == hosted_url
        assert any(DRAFT_COOKIE in header and "Max-Age=0" in header
                   for header in response.headers.get_list("set-cookie"))
        assert client.cookies.get(DRAFT_COOKIE) is None
    else:
        assert "result=unavailable" in response.headers["location"]
        assert not any(DRAFT_COOKIE in header for header in response.headers.get_list("set-cookie"))
        assert client.cookies.get(DRAFT_COOKIE) == before


@pytest.mark.parametrize("reason", ["offer_changed", "quote_changed"])
def test_direct_rejection_without_saved_promo_keeps_submitted_year(client, owner, reason):
    _, headers = owner
    preview = submit(client, headers, code="", cycle="year", action="year")
    page = client.get(preview.headers["location"])
    assert_checkout(page, today="10000", renewal="10000", cycle="год", promo="")
    assert client.cookies.get(DRAFT_COOKIE) is None
    fields = checkout_start_fields(page)
    if reason == "offer_changed":
        fields["offer_version"] = "synthetic-outdated-offer"
    else:
        fields["quote_id"] = "00000000-0000-0000-0000-000000000000"
    response = client.post("/billing/checkout/start", headers=headers, data={
        **fields, "promo_code": "", "offer_consent": "true", "recurring_consent": "true",
    }, follow_redirects=False)
    assert promo_input(response, status=409) == ""
    assert 'name="cycle" value="year"' in response.text
    assert "Оплатить 10 000 ₽ в ЮKassa" in response.text
    assert "Условия оплаты изменились" in response.text if reason == "offer_changed" else "Расчет изменился или устарел" in response.text
    assert_no_draft_renewal(response)
    for name in ("offer_consent", "recurring_consent"):
        checkbox = re.search(rf'<input[^>]*name="{name}"[^>]*>', response.text)
        assert checkbox and "checked" not in checkbox.group(0)


@pytest.mark.parametrize("guard", ["disabled", "db_none"])
@pytest.mark.parametrize("intent", ["new", "replace", "clear", "edit", "stale_period"])
def test_unavailable_preview_keeps_explicit_intent(client, owner, monkeypatch, guard, intent):
    _, headers = owner
    seed_campaign(client)
    clock = [int(time.time())]
    monkeypatch.setattr(routes, "_promo_draft_now", lambda: clock[0])
    old_code = "[old synthetic code]"
    if intent != "new":
        submit(client, headers, code=old_code)
        keep_cookie_on_controlled_clock(client)
        clock[0] += 10
    code = "" if intent == "clear" else old_code if intent == "stale_period" else SYNTH_CODE
    action = "year" if intent in {"edit", "stale_period"} else "apply"
    with monkeypatch.context() as unavailable:
        if guard == "disabled":
            unavailable.setattr(routes, "billing_checkout_allowed", lambda *_args: False)
        else:
            async def no_db():
                yield None
            unavailable.setitem(client.app.dependency_overrides, routes.WebDbDependency.dependency, no_db)
        response = submit(client, headers, code=code, cycle="month" if action == "year" else "year",
                          action=action, previous_code=old_code)
    assert "result=unavailable" in response.headers["location"]
    assert "cycle=year" in response.headers["location"]
    if intent == "clear":
        assert client.cookies.get(DRAFT_COOKIE) is None
        assert promo_input(client.get("/billing/checkout?cycle=year")) == ""
    else:
        cookie = draft_cookie(response)
        assert cookie["max-age"] == ("290" if intent == "stale_period" else "300")
        keep_cookie_on_controlled_clock(client)
        for _ in range(2):
            page = client.get("/billing/checkout")
            assert promo_input(page) == code
            assert 'name="cycle" value="year"' in page.text
            if intent == "stale_period":
                assert 'id="billing-checkout-error"' in page.text
            else:
                assert_checkout(page, today="9000", renewal="10000", cycle="год", promo=SYNTH_CODE)
