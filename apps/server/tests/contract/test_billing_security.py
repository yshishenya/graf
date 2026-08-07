import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from starlette.requests import Request

from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaConfigurationError
from twobrain_rec_server.cabinet.web_routes.billing import (
    billing_checkout_return_url,
)
from twobrain_rec_server.cabinet.web_routes.billing import (
    router as billing_web_router,
)
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy

FINANCIAL_PAGE_CLASSES = (
    "billing_overview",
    "billing_usage",
    "billing_subscription",
    "billing_payment_method",
    "billing_storage_addons",
    "billing_checkout",
    "billing_history",
    "billing_invoice",
    "billing_referrals",
)
BASE_TEMPLATE = (
    Path(__file__).parents[2]
    / "src/twobrain_rec_server/cabinet/templates/cabinet/base.html"
)


def test_billing_mutations_require_csrf() -> None:
    missing: list[str] = []
    for route in billing_web_router.routes:
        if not isinstance(route, APIRoute) or not route.methods.intersection(
            {"POST", "PUT", "PATCH", "DELETE"}
        ):
            continue
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in route.dependant.dependencies
        }
        if "require_web_csrf" not in dependency_names:
            missing.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert missing == []


def test_financial_page_classes_disable_browser_collection() -> None:
    for page_class in FINANCIAL_PAGE_CLASSES:
        policy = get_page_class_policy(page_class)

        assert policy.sensitivity == "financial"
        assert policy.posthog_autocapture_state == "disabled"
        assert policy.posthog_replay_allowed is False
        assert policy.page_view_allowed is False
        assert policy.yandex_state == "blocked"
        assert policy.yandex_webvisor_allowed is False
        assert policy.click_map_allowed is False
        assert policy.scroll_map_allowed is False
        assert policy.form_analytics_allowed is False


def test_cabinet_shell_masks_financial_content_from_browser_providers() -> None:
    template = BASE_TEMPLATE.read_text(encoding="utf-8")

    assert 'data-graf-analytics-private="true"' in template
    assert 'data-ph-mask="true"' in template
    assert 'data-ym-hide-content="true"' in template
    assert 'data-ym-disable-keys="true"' in template


def test_product_has_no_yookassa_refund_mutation() -> None:
    source = inspect.getsource(YooKassaClient)

    assert not hasattr(YooKassaClient, "create_refund")
    assert '"POST", "/v3/refunds' not in source


def test_billing_callback_url_uses_configured_public_origin_not_request_host() -> None:
    app = SimpleNamespace(
        state=SimpleNamespace(settings=SimpleNamespace(public_base_url="https://rec.2brain.pro")),
        url_path_for=lambda _name: "/billing/checkout/return",
    )
    request = Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/billing/checkout/return",
            "headers": [(b"host", b"attacker.example")],
            "query_string": b"",
            "app": app,
        }
    )

    assert billing_checkout_return_url(request) == "https://rec.2brain.pro/billing/checkout/return"

    request.app.state.settings.public_base_url = "https://[invalid"
    with pytest.raises(YooKassaConfigurationError, match="callback URL is invalid"):
        billing_checkout_return_url(request)
