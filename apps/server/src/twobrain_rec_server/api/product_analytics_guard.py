from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from collections.abc import Awaitable, Callable
from typing import Any

PRODUCT_ANALYTICS_POST_PATHS = frozenset(
    {
        "/api/v1/product-analytics/events",
        "/api/v1/product-analytics/posthog-web-capture",
        "/api/v1/product-analytics/posthog-desktop-capture",
    }
)


class _RequestTooLarge(Exception):
    pass


class ProductAnalyticsIngressGuard:
    """Bound anonymous telemetry before FastAPI/Pydantic allocates its body.

    The process-local limiter is a last line of defence; the production edge
    must still apply a distributed limit when multiple API replicas are used.
    """

    def __init__(
        self,
        app: Callable[..., Awaitable[Any]],
        *,
        max_body_bytes: int = 262_144,
        max_requests: int = 120,
        window_seconds: int = 60,
    ) -> None:
        self.app = app
        self.max_body_bytes = max_body_bytes
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._hits: dict[str, deque[float]] = {}
        self._lock = asyncio.Lock()

    async def __call__(self, scope: dict[str, Any], receive, send) -> None:
        if (
            scope.get("type") != "http"
            or scope.get("method") != "POST"
            or scope.get("path") not in PRODUCT_ANALYTICS_POST_PATHS
        ):
            await self.app(scope, receive, send)
            return
        if _content_length(scope) > self.max_body_bytes:
            await _send_problem(send, 413, "product_analytics_body_too_large")
            return
        client = scope.get("client")
        client_key = str(client[0]) if isinstance(client, (tuple, list)) and client else "unknown"
        if not await self._allow(client_key):
            await _send_problem(send, 429, "product_analytics_rate_limited")
            return
        consumed = 0

        async def limited_receive():
            nonlocal consumed
            message = await receive()
            if message.get("type") == "http.request":
                consumed += len(message.get("body", b""))
                if consumed > self.max_body_bytes:
                    raise _RequestTooLarge
            return message

        try:
            await self.app(scope, limited_receive, send)
        except _RequestTooLarge:
            await _send_problem(send, 413, "product_analytics_body_too_large")

    async def _allow(self, client_key: str) -> bool:
        now = time.monotonic()
        cutoff = now - self.window_seconds
        async with self._lock:
            hits = self._hits.setdefault(client_key, deque())
            while hits and hits[0] <= cutoff:
                hits.popleft()
            if len(hits) >= self.max_requests:
                return False
            hits.append(now)
            if len(self._hits) > 4096:
                self._hits = {key: value for key, value in self._hits.items() if value and value[-1] > cutoff}
            return True


def _content_length(scope: dict[str, Any]) -> int:
    for raw_name, raw_value in scope.get("headers", []):
        if raw_name.lower() == b"content-length":
            try:
                return max(0, int(raw_value))
            except (TypeError, ValueError):
                return 0
    return 0


async def _send_problem(send, status_code: int, code: str) -> None:
    body = json.dumps({"code": code}, separators=(",", ":")).encode()
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())],
        }
    )
    await send({"type": "http.response.body", "body": body})
