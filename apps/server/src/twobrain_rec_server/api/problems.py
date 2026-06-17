from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.responses import JSONResponse, RedirectResponse

from twobrain_rec_server.observability.redaction import redact_mapping


@dataclass(slots=True)
class ProblemDetail(Exception):
    status: int
    code: str
    title: str
    detail: str | None = None
    type: str = "about:blank"


def problem_response(problem: ProblemDetail, request: Request | None = None) -> JSONResponse:
    body: dict[str, Any] = {
        "type": problem.type,
        "title": problem.title,
        "status": problem.status,
        "code": problem.code,
    }
    if problem.detail:
        body["detail"] = problem.detail
    if request is not None:
        body["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=problem.status,
        content=redact_mapping(body),
        media_type="application/problem+json",
    )


def _is_browser_cabinet_path(path: str) -> bool:
    return (
        path == "/meetings"
        or path.startswith("/meetings/")
        or path == "/desktop/meetings"
        or path.startswith("/desktop/meetings/")
    )


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


async def problem_exception_handler(request: Request, exc: ProblemDetail) -> JSONResponse | RedirectResponse:
    if exc.status in {401, 403} and _is_browser_cabinet_path(request.url.path) and _wants_html(request):
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(
            "/login?" + urlencode({"next": next_path, "error": exc.code}),
            status_code=303,
        )
    return problem_response(exc, request)


def bad_request(code: str, title: str, detail: str | None = None) -> ProblemDetail:
    return ProblemDetail(status=400, code=code, title=title, detail=detail)


def forbidden(code: str = "forbidden", title: str = "Forbidden") -> ProblemDetail:
    return ProblemDetail(status=403, code=code, title=title)


def not_found(code: str = "not_found", title: str = "Not found") -> ProblemDetail:
    return ProblemDetail(status=404, code=code, title=title)


def tenant_context_missing(title: str = "Tenant context missing") -> ProblemDetail:
    return ProblemDetail(status=403, code="tenant_context_missing", title=title)


def tenant_scope_denied(title: str = "Tenant scope denied") -> ProblemDetail:
    return ProblemDetail(status=403, code="tenant_scope_denied", title=title)


def tenant_mutation_denied(title: str = "Tenant mutation denied") -> ProblemDetail:
    return ProblemDetail(status=403, code="tenant_mutation_denied", title=title)


def tenant_resource_not_found(title: str = "Not found") -> ProblemDetail:
    return ProblemDetail(status=404, code="tenant_resource_not_found", title=title)
