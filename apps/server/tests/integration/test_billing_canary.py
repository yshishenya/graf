import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from tests.unit.test_billing_money_path_e2e import (
    _approved_month_catalog,
    _configure_billing,
    _prepare_owner_session,
)
from twobrain_rec_server.db.models import BillingInvoice


@pytest.mark.parametrize("scope", ["empty", "other", "self"])
def test_http_checkout_obeys_canary_scope_without_touching_history(client, tmp_path, scope):
    workspace, headers = _prepare_owner_session(client)
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    client.app.state.settings.billing_checkout_workspace_ids = {
        "empty": frozenset(),
        "other": frozenset({uuid4()}),
        "self": frozenset({workspace}),
    }[scope]
    response = client.post(
        "/billing/checkout/preview",
        headers=headers,
        data={"cycle": "month"},
        follow_redirects=False,
    )
    assert response.status_code == 303
    if scope == "self":
        assert "promo_applied" in response.headers["location"]
    if scope != "self":
        assert "unavailable" in response.headers["location"]
        for path, data in [
            ("/billing/checkout/start", {"cycle": "month"}),
            ("/billing/storage/preview", {"package_count": "1"}),
            ("/billing/subscription/early-preview", {}),
            ("/billing/purchases/confirm", {"quote_id": str(uuid4()), "purchase_consent": "true"}),
        ]:
            rejected = client.post(path, headers=headers, data=data, follow_redirects=False)
            assert rejected.status_code in {303, 409}, (path, rejected.status_code)
        assert client.get("/billing/history", headers=headers).status_code == 200

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(BillingInvoice)
                    .where(BillingInvoice.workspace_id == workspace)
                )
                == 0
            )

    asyncio.run(check())


@pytest.mark.parametrize("cycle", ["month", "year"])
def test_quote_created_before_scope_change_cannot_start_payment(client, tmp_path, cycle):
    from tests.integration.test_billing_purchase_journey import quote_id
    from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION

    workspace, headers = _prepare_owner_session(client)
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    client.app.state.settings.billing_checkout_workspace_ids = frozenset({workspace})
    preview = client.get("/billing/checkout", params={"cycle": cycle}, headers=headers)
    bound = quote_id(preview)
    client.app.state.settings.billing_checkout_workspace_ids = frozenset({uuid4()})
    response = client.post(
        "/billing/checkout/start",
        headers=headers,
        follow_redirects=False,
        data={
            "cycle": cycle,
            "quote_id": bound,
            "idempotency_key": str(uuid4()),
            "offer_consent": "true",
            "recurring_consent": "true",
            "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
        },
    )
    assert response.status_code == 303
    assert "unavailable" in response.headers["location"]

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            assert (
                await db.scalar(
                    select(func.count())
                    .select_from(BillingInvoice)
                    .where(BillingInvoice.workspace_id == workspace)
                )
                == 0
            )

    asyncio.run(check())
