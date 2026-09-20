"""Delivery of the installer file: the fact that is counted (FR-019).

The public download page announces the installer and the button on it carries
the click. A click is not a delivery: only the response of the file itself is,
and the two are different numbers on purpose. This module is therefore the
single place that knows which public address is an installer artifact, and the
static file handler asks it after every successful delivery.

Counting happens after the file was handed to the browser, never before: the
visitor must never wait for analytics, and a refused counter write leaves a
measurement gap instead of a broken download (FR-058).
"""

from __future__ import annotations

import logging
from typing import Any

from starlette.requests import Request
from starlette.responses import Response

from twobrain_rec_server.public.analytics import record_public_installer_delivery
from twobrain_rec_server.public.templates import VersionedPublicStaticFiles

logger = logging.getLogger(__name__)

# The installer artifacts live in one directory of the public static tree and are
# recognised by their extension, so an unrelated asset never counts as a
# download and a renamed artifact still does not.
INSTALLER_ARTIFACT_DIRECTORY = "downloads"
INSTALLER_ARTIFACT_EXTENSIONS = (".pkg", ".dmg")
# A delivery is a complete file in one response: a conditional request answered
# with 304 delivered nothing, and a partial answer (206) is a resumed transfer
# whose full delivery was already counted.
DELIVERED_STATUS_CODE = 200


def is_installer_artifact(path: str | None) -> bool:
    """Return whether a public static path is an installer file (FR-019)."""
    normalized = str(path or "").strip().lower().lstrip("/")
    return normalized.startswith(f"{INSTALLER_ARTIFACT_DIRECTORY}/") and normalized.endswith(
        INSTALLER_ARTIFACT_EXTENSIONS
    )


async def count_installer_delivery(path: str, scope: dict[str, Any], response: Response) -> None:
    """Count a served installer file; every other delivery is left alone.

    The session comes from the application state, because a static file handler
    has no request dependency to inject. Nothing here can raise or delay: the
    response is already built, and a missing session, an unreachable database or
    a refused statement only means that one delivery was not counted.
    """
    if not is_installer_artifact(path):
        return
    if scope.get("method") != "GET" or response.status_code != DELIVERED_STATUS_CODE:
        return
    sessionmaker = getattr(getattr(scope.get("app"), "state", None), "db_sessionmaker", None)
    if sessionmaker is None:
        return
    try:
        async with sessionmaker() as session:
            await record_public_installer_delivery(session, Request(scope))
    except Exception as exc:  # noqa: BLE001 - a download must reach the visitor
        logger.warning(
            "installer delivery was not counted: file=%s error=%s",
            path,
            exc.__class__.__name__,
        )


class PublicStaticFilesWithInstallerDeliveries(VersionedPublicStaticFiles):
    """The public static surface, counting the installer files it delivers."""

    async def get_response(self, path: str, scope: dict[str, Any]) -> Response:
        response = await super().get_response(path, scope)
        await count_installer_delivery(path, scope, response)
        return response
