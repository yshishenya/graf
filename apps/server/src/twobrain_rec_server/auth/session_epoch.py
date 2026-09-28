"""Non-authorizing browser generation marker for cancelling stale async handoffs."""

import secrets

from starlette.responses import Response

SESSION_EPOCH_COOKIE = "__Host-graf_session_epoch"
DEV_SESSION_EPOCH_COOKIE = "graf_dev_session_epoch"


def rotate_browser_session_epoch(response: Response, *, secure: bool, max_age: int = 60) -> None:
    # No identity, bearer token or server permission is encoded in this marker.
    # Logout rotates rather than deletes it, including for pre-marker sessions.
    response.set_cookie(
        key=SESSION_EPOCH_COOKIE if secure else DEV_SESSION_EPOCH_COOKIE,
        value=secrets.token_hex(16),
        max_age=max_age,
        path="/",
        secure=secure,
        httponly=False,
        samesite="lax",
    )
