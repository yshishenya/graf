from __future__ import annotations

import hmac
import secrets
from hashlib import sha256
from uuid import UUID

from twobrain_rec_server.api.problems import ProblemDetail

CSRF_HEADER_NAME = "X-CSRF-Token"
CSRF_FORM_FIELD_NAME = "csrf_token"


def issue_csrf_token(*, session_id: UUID, secret: str) -> str:
    nonce = secrets.token_urlsafe(24)
    return f"{nonce}.{_sign(nonce, session_id=session_id, secret=secret)}"


def verify_csrf_token(token: str | None, *, session_id: UUID, secret: str) -> bool:
    if not token or "." not in token:
        return False
    nonce, signature = token.rsplit(".", 1)
    if not nonce or not signature:
        return False
    expected = _sign(nonce, session_id=session_id, secret=secret)
    return hmac.compare_digest(signature, expected)


def require_csrf_token(token: str | None, *, session_id: UUID | None, secret: str | None) -> None:
    if token is None:
        raise ProblemDetail(
            status=403,
            code="csrf_token_missing",
            title="CSRF token is required",
            detail="Повторите действие из кабинета 2brain Rec.",
        )
    if session_id is None or not secret or not verify_csrf_token(token, session_id=session_id, secret=secret):
        raise ProblemDetail(
            status=403,
            code="csrf_token_invalid",
            title="CSRF token is invalid",
            detail="Сессия действия устарела. Обновите страницу и попробуйте снова.",
        )


def _sign(nonce: str, *, session_id: UUID, secret: str) -> str:
    payload = f"{session_id}:{nonce}".encode()
    return hmac.new(secret.encode(), payload, sha256).hexdigest()
