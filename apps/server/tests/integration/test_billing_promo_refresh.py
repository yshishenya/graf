"""Short-lived promo choices survive refresh without authorizing a payment."""

import asyncio
import re
import time
from html import unescape
from http.cookies import SimpleCookie

import pytest
from sqlalchemy import select

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
)

DRAFT_COOKIE = "graf_checkout_promo_draft"
SYNTH_CODE = "SYNTH-PRESENTATION"


@pytest.fixture(autouse=True)
def no_financial_side_effects(client):
    yield

    async def inspect():
        async with client.app_state["sessionmaker"]() as db:
            for model in (BillingOperation, BillingInvoice, PromotionRedemption):
                assert await db.scalar(select(model.id)) is None

    asyncio.run(inspect())


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


def assert_no_draft_renewal(response):
    assert not any(DRAFT_COOKIE in header and "Max-Age=0" not in header
                   for header in response.headers.get_list("set-cookie"))


def assert_plain_checkout(response):
    assert_checkout(response, today="1000", renewal="1000", cycle="месяц", promo="")


def promo_input(response):
    assert response.status_code == 200
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
    start_error = client.post("/billing/checkout/start", headers=headers,
                              data={"cycle": "year", "promo_code": SYNTH_CODE},
                              follow_redirects=False)
    assert start_error.status_code == 303
    assert int(draft_cookie(start_error)["max-age"]) <= initial_expiry - clock[0]
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
