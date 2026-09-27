from uuid import uuid4

import pytest
from pydantic import ValidationError

from twobrain_rec_server.billing.operations import billing_checkout_allowed
from twobrain_rec_server.config import Settings


@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("scope", ["public", "empty", "self", "other"])
def test_checkout_scope_cannot_override_master_switch(enabled, scope):
    workspace = uuid4()
    allowed = {"public": None, "empty": frozenset(), "self": frozenset({workspace}), "other": frozenset({uuid4()})}[scope]
    settings = Settings.model_construct(billing_checkout_enabled=enabled, billing_checkout_workspace_ids=allowed)
    assert billing_checkout_allowed(settings, workspace) is (enabled and scope in {"public", "self"})


def test_invalid_workspace_configuration_is_rejected():
    with pytest.raises(ValidationError):
        Settings(billing_checkout_workspace_ids=["not-a-workspace"])


@pytest.mark.asyncio
async def test_restricted_shop_is_not_advertised_as_open_to_everyone():
    from tests.unit.test_public_landing import _OfferDb, _public_catalog_rows
    from twobrain_rec_server.public.offers import build_public_offer_view

    settings = Settings.model_construct(
        billing_checkout_enabled=True, billing_yookassa_shop_id="synthetic",
        billing_yookassa_environment="production", billing_checkout_workspace_ids=frozenset({uuid4()}),
    )
    offer = await build_public_offer_view(_OfferDb(_public_catalog_rows()), settings)
    assert offer.catalog_ready and not offer.sale_ready


@pytest.mark.asyncio
async def test_prepared_foreign_renewal_cannot_dispatch_in_canary(monkeypatch, tmp_path):
    from tests.unit.test_renewal_charge import (
        OPERATION_ID,
        WORKSPACE_ID,
        FakeDb,
        FakeProvider,
        _attempt_charge_moment,
        _rows,
        _settings,
    )
    from twobrain_rec_server.billing import renewal_charge as renewal

    settings = _settings(tmp_path)
    settings.billing_checkout_workspace_ids = frozenset({uuid4()})
    subscription, operation, invoice, method = _rows(tmp_path, attempt=1)
    provider = FakeProvider({"id": "must-not-send"})
    monkeypatch.setattr(renewal, "YooKassaClient", lambda _settings: provider)
    result = await renewal.charge_renewal_operation(
        FakeDb([subscription, operation, invoice, method]), settings,
        operation_id=OPERATION_ID, workspace_id=WORKSPACE_ID, now=_attempt_charge_moment(1),
    )
    assert result.status == "blocked"
    assert provider.calls == []
    assert subscription.recurring_allowed is True
    assert operation.state == "scheduled"
