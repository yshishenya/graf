"""Explicit acknowledgement for ordinary settings; older clients retain redirects."""
import json

from fastapi import Request
from fastapi.responses import JSONResponse

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.context import TenantScope


def autosave_requested(request: Request) -> bool:
    return request.headers.get("X-Graf-Settings-Autosave") == "true"


def settings_saved(scope: TenantScope, values: dict, *, version: int | None = None) -> JSONResponse:
    return JSONResponse({"saved": True, "actor": str(scope.user_id),
                         "workspace": str(scope.workspace_id), "values": values, "version": version})


def validate_settings_baseline(form: object, current: dict) -> None:
    raw = form.get("expected_values")
    if raw is None:  # Existing form clients do not submit a comparison snapshot.
        return
    try:
        expected = json.loads(str(raw))
        if not isinstance(expected, dict) or set(expected) != set(current):
            raise ValueError()
    except (ValueError, TypeError) as exc:
        raise ProblemDetail(status=422, code="invalid_settings_baseline", title="Обновите настройки") from exc
    if expected != current:
        raise ProblemDetail(status=409, code="settings_conflict", title="Настройка изменена на другом устройстве")
