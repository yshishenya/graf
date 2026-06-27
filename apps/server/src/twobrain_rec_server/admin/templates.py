from __future__ import annotations

from functools import lru_cache
from importlib.resources import files
from typing import Any

from fastapi import Request
from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from starlette.responses import HTMLResponse

from twobrain_rec_server.auth.context import AuthenticatedPrincipal
from twobrain_rec_server.auth.csrf import CSRF_FORM_FIELD_NAME, issue_csrf_token

ADMIN_STATIC_URL = "/static/admin"


def _admin_package_root() -> Any:
    return files("twobrain_rec_server.admin")


def admin_template_dir() -> str:
    return str(_admin_package_root().joinpath("templates"))


def admin_static_dir() -> str:
    return str(_admin_package_root().joinpath("static", "admin"))


@lru_cache(maxsize=1)
def get_admin_templates() -> Environment:
    return Environment(
        loader=FileSystemLoader(admin_template_dir()),
        autoescape=select_autoescape(("html", "xml"), default_for_string=True),
        undefined=StrictUndefined,
    )


def render_template(template_name: str, **context: Any) -> str:
    template = get_admin_templates().get_template(template_name)
    request = context.get("request")
    principal = context.get("principal")
    context.setdefault("csrf_field_name", CSRF_FORM_FIELD_NAME)
    context.setdefault("csrf_token", _csrf_token_for_principal(request, principal))
    return template.render(admin_static_url=ADMIN_STATIC_URL, **context)


def admin_template_response(
    request: Request,
    template_name: str,
    *,
    status_code: int = 200,
    **context: Any,
) -> HTMLResponse:
    return HTMLResponse(
        render_template(template_name, request=request, **context),
        status_code=status_code,
    )


def _csrf_token_for_principal(request: object, principal: object) -> str:
    if not isinstance(request, Request) or not isinstance(principal, AuthenticatedPrincipal):
        return ""
    if not principal.auth_via_session or principal.session_id is None:
        return ""
    secret = getattr(request.app.state, "web_csrf_secret", None)
    if not secret:
        return ""
    return issue_csrf_token(session_id=principal.session_id, secret=str(secret))
