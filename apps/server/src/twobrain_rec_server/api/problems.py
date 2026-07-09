from dataclasses import dataclass
from typing import Any
from urllib.parse import urlencode

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse

from twobrain_rec_server.domain.statuses import (
    CustodyMetadataSafety,
    CustodyNormalUserAction,
    CustodyOwner,
    CustodyRetryClass,
)
from twobrain_rec_server.observability.redaction import redact_mapping


@dataclass(slots=True)
class ProblemDetail(Exception):
    status: int
    code: str
    title: str
    detail: str | None = None
    type: str = "about:blank"
    custody_owner: str | None = None
    retry_class: str | None = None
    normal_user_action: str | None = None
    metadata_safety: str | None = None


def problem_response(problem: ProblemDetail, request: Request | None = None) -> JSONResponse:
    defaults = _custody_defaults(problem)
    body: dict[str, Any] = {
        "type": problem.type,
        "title": problem.title,
        "status": problem.status,
        "code": problem.code,
    }
    if problem.detail:
        body["detail"] = problem.detail
    body["custody_owner"] = problem.custody_owner or defaults["custody_owner"]
    body["retry_class"] = problem.retry_class or defaults["retry_class"]
    body["normal_user_action"] = problem.normal_user_action or defaults["normal_user_action"]
    body["metadata_safety"] = problem.metadata_safety or defaults["metadata_safety"]
    body["custody"] = {
        "owner": body["custody_owner"],
        "retry_class": body["retry_class"],
        "normal_user_action": body["normal_user_action"],
        "metadata_safety": body["metadata_safety"],
    }
    if request is not None:
        body["request_id"] = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=problem.status,
        content=redact_mapping(body),
        media_type="application/problem+json",
    )


def _custody_defaults(problem: ProblemDetail) -> dict[str, str]:
    code = problem.code
    if code in {
        "auth_required",
        "session_expired",
        "tenant_context_missing",
        "tenant_scope_denied",
        "meeting_scope_denied",
        "session_scope_denied",
        "device_scope_denied",
    }:
        return _custody_default(
            owner=CustodyOwner.MEETING_OWNER,
            retry_class=CustodyRetryClass.PAUSED_UNTIL_USER_ACTION,
            action=CustodyNormalUserAction.SIGN_IN,
        )
    if code in {
        "recording_duration_exceeded",
        "upload_part_bytes_exceeded",
        "track_bytes_exceeded",
        "package_bytes_exceeded",
    }:
        return _custody_default(
            owner=CustodyOwner.WORKSPACE_ADMIN,
            retry_class=CustodyRetryClass.PAUSED_UNTIL_ADMIN_ACTION,
            action=CustodyNormalUserAction.COPY_SAFE_REPORT,
        )
    if code in {
        "storage_unavailable",
        "persistence_unavailable",
        "processing_store_unavailable",
        "cabinet_store_unavailable",
        "calendar_provider_timeout",
        "calendar_provider_unavailable",
        "calendar_rate_limited",
        "calendar_sync_stale",
    }:
        return _custody_default(
            owner=CustodyOwner.PRODUCT_AUTOMATIC,
            retry_class=CustodyRetryClass.AUTOMATIC,
            action=CustodyNormalUserAction.NONE,
        )
    if code in {
        "checksum_mismatch",
        "checksum_conflict",
        "range_conflict",
        "range_overlap",
        "expected_track_size_exceeded",
        "invalid_expected_track_size",
        "unexpected_track_role",
        "unexpected_expected_track_size_role",
        "invalid_part_number",
        "invalid_byte_offset",
        "idempotency_conflict",
        "active_upload_session_exists",
        "media_revision_conflict",
        "session_terminal",
        "meeting_deletion_active",
    }:
        return _custody_default(
            owner=CustodyOwner.SUPPORT,
            retry_class=CustodyRetryClass.NOT_RETRYABLE,
            action=CustodyNormalUserAction.COPY_SAFE_REPORT,
        )
    if problem.status in {401, 403}:
        return _custody_default(
            owner=CustodyOwner.MEETING_OWNER,
            retry_class=CustodyRetryClass.PAUSED_UNTIL_USER_ACTION,
            action=CustodyNormalUserAction.SIGN_IN,
        )
    if problem.status == 413:
        return _custody_default(
            owner=CustodyOwner.WORKSPACE_ADMIN,
            retry_class=CustodyRetryClass.PAUSED_UNTIL_ADMIN_ACTION,
            action=CustodyNormalUserAction.COPY_SAFE_REPORT,
        )
    if problem.status in {408, 429, 503}:
        return _custody_default(
            owner=CustodyOwner.PRODUCT_AUTOMATIC,
            retry_class=CustodyRetryClass.AUTOMATIC,
            action=CustodyNormalUserAction.NONE,
        )
    return _custody_default(
        owner=CustodyOwner.SUPPORT,
        retry_class=CustodyRetryClass.NOT_RETRYABLE,
        action=CustodyNormalUserAction.COPY_SAFE_REPORT,
    )


def _custody_default(
    *,
    owner: CustodyOwner,
    retry_class: CustodyRetryClass,
    action: CustodyNormalUserAction,
) -> dict[str, str]:
    return {
        "custody_owner": owner.value,
        "retry_class": retry_class.value,
        "normal_user_action": action.value,
        "metadata_safety": CustodyMetadataSafety.METADATA_ONLY.value,
    }


def _is_browser_cabinet_path(path: str) -> bool:
    return (
        path in {"/meetings", "/desktop/meetings"}
        or path.startswith(("/meetings/", "/desktop/meetings/"))
    )


def _is_browser_admin_path(path: str) -> bool:
    return path == "/admin" or path.startswith("/admin/")


def _wants_html(request: Request) -> bool:
    return "text/html" in request.headers.get("accept", "").lower()


async def problem_exception_handler(request: Request, exc: ProblemDetail) -> JSONResponse | RedirectResponse:
    if exc.status == 401 and _is_browser_admin_path(request.url.path):
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(
            "/login?" + urlencode({"next": next_path, "error": exc.code}),
            status_code=303,
        )
    if exc.status in {401, 403} and _is_browser_cabinet_path(request.url.path) and _wants_html(request):
        next_path = request.url.path
        if request.url.query:
            next_path = f"{next_path}?{request.url.query}"
        return RedirectResponse(
            "/login?" + urlencode({"next": next_path, "error": exc.code}),
            status_code=303,
        )
    return problem_response(exc, request)


async def request_validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    _ = exc
    return problem_response(
        ProblemDetail(
            status=422,
            code="request_validation_error",
            title="Request validation failed",
        ),
        request,
    )


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
