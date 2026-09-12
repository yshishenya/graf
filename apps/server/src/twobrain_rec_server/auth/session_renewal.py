"""Deliver only committed session deadlines, retaining the existing credential."""

from datetime import UTC, datetime
from http.cookies import SimpleCookie

from sqlalchemy.exc import SQLAlchemyError

from twobrain_rec_server.auth.dependencies import (
    auth_session_cookie_name,
    auth_session_cookie_secure,
    is_web_cookie_session,
)
from twobrain_rec_server.auth.sessions import record_session_activity
from twobrain_rec_server.db.tenant_context import apply_tenant_context


async def session_renewal_middleware(request, call_next):
    response = await call_next(request)
    renewal = getattr(request.state, "auth_session_renewal", None)
    if renewal is None or not (200 <= response.status_code < 300 or response.status_code == 304):
        return response
    cookie_name = auth_session_cookie_name(request)
    for value in response.headers.getlist("set-cookie"):
        cookie = SimpleCookie()
        cookie.load(value)
        if cookie_name in cookie:
            # Login, logout and space changes own their response credential.
            return response
    token, session, device, context = renewal
    try:
        async with request.app.state.db_sessionmaker() as db:
            await apply_tenant_context(db, context)
            expires_at = await record_session_activity(
                db, session, device, ttl_seconds=request.app.state.settings.auth_session_ttl_seconds,
            )
            await db.commit()
    except SQLAlchemyError:
        # The operation may already have committed. Never turn its success into
        # a retryable error or publish an uncommitted renewal; the next request retries.
        return response
    if expires_at is None:
        return response
    max_age = int((expires_at - datetime.now(UTC)).total_seconds())
    if max_age <= 0:
        return response
    response.headers["Cache-Control"] = "no-store"
    if is_web_cookie_session(request):
        response.set_cookie(cookie_name, token, max_age=max_age, path="/",
            secure=auth_session_cookie_secure(request), httponly=True, samesite="lax")
    else:
        response.headers["X-GRAF-Auth-Expires-At"] = str(int(expires_at.timestamp()))
    return response
