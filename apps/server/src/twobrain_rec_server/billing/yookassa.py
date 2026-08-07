from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.config import Settings


class YooKassaConfigurationError(RuntimeError):
    pass


class YooKassaProviderError(RuntimeError):
    pass


ALLOWED_YOOKASSA_HOSTS = frozenset(
    {
        "api.yookassa.ru",
        "api.yookassa.test",
        "yookassa.ru",
        "yookassa.test",
        "yoomoney.ru",
    }
)
ALLOWED_YOOKASSA_API_HOSTS = frozenset({"api.yookassa.ru", "api.yookassa.test"})


def is_allowed_confirmation_url(value: object) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlsplit(value)
    return parsed.scheme == "https" and parsed.hostname in ALLOWED_YOOKASSA_HOSTS


def _read_secret(path: Path | None) -> str:
    if path is None or not path.is_file():
        raise YooKassaConfigurationError("YooKassa secret is unavailable")
    value = path.read_text(encoding="utf-8").strip()
    if not value:
        raise YooKassaConfigurationError("YooKassa secret is empty")
    return value


def read_webhook_secret(path: Path | None) -> str:
    return _read_secret(path)


class YooKassaClient:
    """Allowlisted payment/observation adapter; refund mutation is impossible."""

    def __init__(self, settings: Settings, *, transport: httpx.AsyncBaseTransport | None = None) -> None:
        if settings.billing_yookassa_base_url is None or not settings.billing_yookassa_shop_id:
            raise YooKassaConfigurationError("YooKassa is not configured")
        self._base_url = str(settings.billing_yookassa_base_url).rstrip("/")
        parsed_base_url = urlsplit(self._base_url)
        if (
            parsed_base_url.scheme != "https"
            or parsed_base_url.hostname not in ALLOWED_YOOKASSA_API_HOSTS
            or parsed_base_url.username
            or parsed_base_url.password
            or parsed_base_url.path not in ("", "/")
            or parsed_base_url.query
            or parsed_base_url.fragment
        ):
            raise YooKassaConfigurationError("YooKassa API base URL is not allowlisted")
        self._shop_id = settings.billing_yookassa_shop_id
        self._provider_floor_minor = settings.billing_provider_floor_minor
        self._secret = _read_secret(settings.billing_yookassa_secret_file)
        self._transport = transport

    @property
    def supports_zero_amount_binding(self) -> bool:
        # YooKassa checkout is amount-bearing; never emulate a zero-charge bind.
        return False

    async def __aenter__(self) -> YooKassaClient:
        self._http = httpx.AsyncClient(
            base_url=self._base_url,
            auth=(self._shop_id, self._secret),
            timeout=20,
            transport=self._transport,
        )
        return self

    async def __aexit__(self, *_: object) -> None:
        await self._http.aclose()

    async def create_payment(
        self,
        *,
        amount_minor: int,
        currency: str,
        description: str,
        idempotence_key: str,
        metadata: dict[str, str],
        save_payment_method: bool = False,
    ) -> dict[str, Any]:
        if amount_minor < self._provider_floor_minor:
            raise ValueError("payment amount is below provider floor")
        payload = {
            "amount": {"value": f"{amount_minor / 100:.2f}", "currency": currency},
            "capture": True,
            "description": description[:128],
            "metadata": metadata,
            "save_payment_method": save_payment_method,
            "confirmation": {"type": "redirect", "return_url": metadata.get("return_url", "")},
        }
        return await self._request("POST", "/v3/payments", payload, idempotence_key=idempotence_key)

    async def get_payment(self, payment_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v3/payments/{validate_provider_identifier(payment_id)}")

    async def list_refunds(
        self,
        *,
        payment_id: str | None = None,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        if limit is not None and not 1 <= limit <= 100:
            raise ValueError("refund list limit must be between 1 and 100")
        params: dict[str, str] = {}
        if payment_id:
            params["payment_id"] = payment_id
        if cursor:
            params["cursor"] = cursor
        if limit is not None:
            params["limit"] = str(limit)
        return await self._request("GET", "/v3/refunds", params=params or None)

    async def get_receipt(self, receipt_id: str) -> dict[str, Any]:
        return await self._request("GET", f"/v3/receipts/{validate_provider_identifier(receipt_id)}")

    async def _request(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
        *,
        idempotence_key: str | None = None,
        params: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        headers = {"Idempotence-Key": idempotence_key} if idempotence_key else {}
        response = await self._http.request(method, path, json=payload, headers=headers, params=params)
        if response.status_code >= 400:
            raise YooKassaProviderError(f"YooKassa request failed: {response.status_code}")
        try:
            data = response.json()
        except json.JSONDecodeError as exc:
            raise YooKassaProviderError("YooKassa returned invalid JSON") from exc
        if not isinstance(data, dict):
            raise YooKassaProviderError("YooKassa response must be an object")
        return data
