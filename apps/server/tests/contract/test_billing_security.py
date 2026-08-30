import ast
import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.routing import APIRoute
from starlette.requests import Request

from twobrain_rec_server.billing.audit import metadata_only
from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaConfigurationError
from twobrain_rec_server.cabinet.web_routes.billing import (
    _billing_owner_subscription,
    activate_billing_trial,
    billing_checkout_return_url,
    continue_billing_checkout,
    start_billing_checkout,
)
from twobrain_rec_server.cabinet.web_routes.billing import (
    router as billing_web_router,
)
from twobrain_rec_server.product_analytics.page_inventory import get_page_class_policy

FINANCIAL_PAGE_CLASSES = (
    "fair_use",
    "billing_overview",
    "billing_plans",
    "billing_discounts",
    "billing_checkout_status",
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
    Path(__file__).parents[2] / "src/twobrain_rec_server/cabinet/templates/cabinet/base.html"
)


def test_billing_mutations_require_csrf() -> None:
    missing: list[str] = []
    for route in billing_web_router.routes:
        if not isinstance(route, APIRoute) or not route.methods.intersection(
            {"POST", "PUT", "PATCH", "DELETE"}
        ):
            continue
        dependency_names = {
            getattr(dependency.call, "__name__", "") for dependency in route.dependant.dependencies
        }
        if "require_web_csrf" not in dependency_names:
            missing.append(f"{','.join(sorted(route.methods))} {route.path}")

    assert missing == []


def test_personal_checkout_cannot_run_for_corporate_workspace() -> None:
    source = inspect.getsource(start_billing_checkout)

    assert 'workspace.kind != "personal"' in source
    assert "workspace.owner_user_id != principal.user_id" in source


def test_checkout_persists_operation_before_invoice_foreign_key() -> None:
    source = inspect.getsource(start_billing_checkout)
    operation_add = source.index("db.add(operation)")
    operation_flush = source.index("await db.flush()", operation_add)

    assert operation_add < operation_flush
    assert operation_flush < source.index("invoice = BillingInvoice")


def test_checkout_continuation_rejects_a_different_persisted_actor() -> None:
    source = inspect.getsource(continue_billing_checkout)

    actor_guard = source.index("billing_actor_user_id != str(principal.user_id)")
    provider_call = source.index("_create_initial_checkout_payment")

    assert actor_guard < provider_call


def test_trial_serializes_with_checkout_before_checking_payment_operations() -> None:
    source = inspect.getsource(activate_billing_trial)

    assert source.index("select(UserIdentity)") < source.index("lock_storage_workspace")
    identity_guard = source[
        source.index("select(UserIdentity)") : source.index("lock_storage_workspace")
    ]
    assert ".with_for_update()" in identity_guard
    assert source.index("select(Workspace)") < source.index("_blocking_payment_operation_query")
    workspace_guard = source[
        source.index("select(Workspace)") : source.index("_blocking_payment_operation_query")
    ]
    assert ".with_for_update()" in workspace_guard
    assert "workspace.owner_user_id != principal.user_id" in workspace_guard


def test_subscription_mutations_share_personal_owner_gate() -> None:
    source = inspect.getsource(_billing_owner_subscription)

    assert 'workspace.kind != "personal"' in source
    assert "workspace.owner_user_id != principal.user_id" in source


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


def test_billing_audit_writers_filter_financial_metadata() -> None:
    assert metadata_only({"amount_minor": 79000, "currency": "RUB", "cycle": "monthly"}) == {
        "cycle": "monthly"
    }
    source_root = Path(__file__).parents[2] / "src/twobrain_rec_server"
    for path in source_root.rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (
                not isinstance(node, ast.Call)
                or getattr(node.func, "id", None) != "BillingAuditEvent"
            ):
                continue
            metadata = next(
                (item.value for item in node.keywords if item.arg == "metadata_json"), None
            )
            if not isinstance(metadata, ast.Dict):
                continue
            for key in metadata.keys:
                assert isinstance(key, ast.Constant) and isinstance(key.value, str)
                assert metadata_only({key.value: "value"}), (
                    f"unsafe audit metadata key {key.value!r} in {path}"
                )


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
