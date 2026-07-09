from __future__ import annotations

from typing import Any

from fastapi import Request
from jinja2 import Environment
from starlette.responses import HTMLResponse

from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.csrf import CSRF_FORM_FIELD_NAME, issue_csrf_token
from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.browser_context import build_browser_provider_context
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.public.templates import public_static_asset_url
from twobrain_rec_server.templates import (
    html_response,
    package_path,
    render_template_from,
    template_environment,
)

ADMIN_STATIC_URL = "/static/admin"


def admin_template_dir() -> str:
    return package_path("twobrain_rec_server.admin", "templates")


def admin_static_dir() -> str:
    return package_path("twobrain_rec_server.admin", "static", "admin")


def get_admin_templates() -> Environment:
    return template_environment(admin_template_dir())


def render_template(template_name: str, **context: Any) -> str:
    request = context.get("request")
    principal = context.get("principal")
    context.setdefault("csrf_field_name", CSRF_FORM_FIELD_NAME)
    context.setdefault("csrf_token", _csrf_token_for_principal(request, principal))
    return render_template_from(
        get_admin_templates(),
        template_name,
        admin_static_url=ADMIN_STATIC_URL,
        cabinet_static_url=CABINET_STATIC_URL,
        public_static_asset_url=public_static_asset_url,
        **context,
    )


def admin_template_response(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    settings = getattr(request.app.state, "settings", Settings())
    context.setdefault(
        "product_analytics_provider",
        _admin_product_analytics_provider(settings, principal=context.get("principal")),
    )
    return html_response(
        render_template(template_name, request=request, **context),
        status_code=status_code,
    )


def _admin_product_analytics_provider(
    settings: Settings,
    *,
    principal: object,
) -> dict[str, object]:
    provider = build_browser_provider_context(settings, "admin")
    posthog = provider.get("posthog")
    if not isinstance(posthog, dict) or not isinstance(principal, AuthenticatedPrincipal):
        return provider
    identity = build_safe_identity(
        user_source_id=str(principal.user_id),
        workspace_source_id=str(principal.session_workspace_id) if principal.session_workspace_id else None,
        device_class="browser",
    )
    posthog["identity_state"] = "authenticated_pseudonymous"
    posthog["distinct_id"] = identity.posthog_distinct_id
    posthog["workspace_pseudonym"] = identity.workspace_pseudonym
    posthog["device_class"] = identity.device_class
    yandex = provider.get("yandex")
    if isinstance(yandex, dict):
        yandex["user_id"] = identity.stable_pseudonymous_user_id
        yandex["user_id_source"] = "graf_pseudonymous_user"
    return provider


def _csrf_token_for_principal(request: object, principal: object) -> str:
    if not isinstance(request, Request) or not isinstance(principal, AuthenticatedPrincipal):
        return ""
    if not principal.auth_via_session or principal.session_id is None:
        return ""
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        return ""
    return issue_csrf_token(session_id=principal.session_id, secret=str(secret))
