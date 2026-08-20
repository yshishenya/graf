import asyncio
from uuid import UUID

from fastapi.routing import APIRoute

from twobrain_rec_server.api.billing import (
    MAX_BILLING_WEBHOOK_BYTES,
    _is_json_content_type,
)
from twobrain_rec_server.api.billing import (
    router as billing_router,
)
from twobrain_rec_server.billing.launch_gates import provider_environment
from twobrain_rec_server.billing.trial import require_trial_activation, trial_used_by_lineage
from twobrain_rec_server.billing.yookassa import is_allowed_confirmation_url


def test_trial_requires_active_personal_workspace_owner_and_unused_identity() -> None:
    require_trial_activation(
        identity_status="active",
        membership_role="owner",
        workspace_kind="personal",
        already_used=False,
    )


def test_trial_rejects_non_owner_or_corporate_workspace() -> None:
    for role, kind in (
        ("member", "personal"),
        ("owner", "corporate"),
        ("owner", "linked"),
    ):
        try:
            require_trial_activation(
                identity_status="active",
                membership_role=role,
                workspace_kind=kind,
                already_used=False,
            )
        except PermissionError:
            pass
        else:
            raise AssertionError("trial must fail closed for non-personal owner context")


def test_trial_usage_follows_recursive_merged_user_lineage() -> None:
    class FakeDb:
        async def scalar(self, statement):
            compiled = str(statement)
            assert "WITH RECURSIVE" in compiled
            assert "merged_into_user_id" in compiled
            return UUID("aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa")

    assert asyncio.run(
        trial_used_by_lineage(
            FakeDb(), user_id=UUID("bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")
        )
    ) is True


def test_confirmation_url_is_yookassa_allowlisted_https_only() -> None:
    assert is_allowed_confirmation_url("https://yookassa.ru/checkout/abc")
    assert is_allowed_confirmation_url("https://api.yookassa.test/checkout/abc")
    assert not is_allowed_confirmation_url("http://yookassa.ru/checkout/abc")
    assert not is_allowed_confirmation_url("https://evil.example/checkout/abc")


def test_billing_webhook_has_bounded_body_budget() -> None:
    assert MAX_BILLING_WEBHOOK_BYTES == 256 * 1024


def test_billing_webhook_requires_json_content_type() -> None:
    assert _is_json_content_type("application/json")
    assert _is_json_content_type("application/json; charset=utf-8")
    assert not _is_json_content_type("text/plain")
    assert not _is_json_content_type(None)


def test_billing_webhook_has_explicit_provider_environment_route() -> None:
    paths = {
        route.path
        for route in billing_router.routes
        if isinstance(route, APIRoute)
    }
    assert "/api/v1/billing/providers/yookassa/webhook/{environment}" in paths
    assert "/api/v1/billing/webhook" in paths


def test_provider_environment_does_not_infer_from_api_host() -> None:
    assert provider_environment("test") == "test"
    assert provider_environment("production") == "production"
