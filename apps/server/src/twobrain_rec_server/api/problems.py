from dataclasses import dataclass
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

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


async def problem_exception_handler(request: Request, exc: ProblemDetail) -> JSONResponse:
    return problem_response(exc, request)


def bad_request(code: str, title: str, detail: str | None = None) -> ProblemDetail:
    return ProblemDetail(status=400, code=code, title=title, detail=detail)


def forbidden(code: str = "forbidden", title: str = "Forbidden") -> ProblemDetail:
    return ProblemDetail(status=403, code=code, title=title)


def not_found(code: str = "not_found", title: str = "Not found") -> ProblemDetail:
    return ProblemDetail(status=404, code=code, title=title)
