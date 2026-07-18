from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from urllib import error, parse, request

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.event_catalog import YANDEX_OFFLINE_CONVERSION_EVENTS
from twobrain_rec_server.product_analytics.events import ProductActivationEvent
from twobrain_rec_server.product_analytics.posthog_client import (
    ProviderDeliveryResult,
    ProviderTransport,
    ProviderTransportResponse,
)
from twobrain_rec_server.product_analytics.provider_secrets import (
    ProviderSecretError,
    read_secret_file,
    secret_file_status,
)


@dataclass(frozen=True, slots=True)
class YandexOfflineConversionRow:
    event_name: str
    conversion_date_time: str
    conversion_unix_time: int
    identity_kind: str
    identity_value_source: str
    dedupe_key: str
    upload_batch_id: str
    upload_state: str
    attribution_reliability: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "event_name": self.event_name,
            "conversion_date_time": self.conversion_date_time,
            "conversion_unix_time": str(self.conversion_unix_time),
            "identity_kind": self.identity_kind,
            "identity_value_source": self.identity_value_source,
            "dedupe_key": self.dedupe_key,
            "upload_batch_id": self.upload_batch_id,
            "upload_state": self.upload_state,
            "attribution_reliability": self.attribution_reliability,
        }


def is_yandex_offline_event_allowed(event_name: str) -> bool:
    return event_name in YANDEX_OFFLINE_CONVERSION_EVENTS


def build_yandex_offline_conversion(event: ProductActivationEvent) -> YandexOfflineConversionRow:
    if not is_yandex_offline_event_allowed(event.event_name):
        raise ValueError("event is not in the 096 Yandex offline conversion subset")
    identity_kind, identity_value_source = _identity_source_for_event(event)
    dedupe_key = _dedupe_key(event, identity_kind)
    return YandexOfflineConversionRow(
        event_name=event.event_name,
        conversion_date_time=event.occurred_at.isoformat(),
        conversion_unix_time=int(event.occurred_at.timestamp()),
        identity_kind=identity_kind,
        identity_value_source=identity_value_source,
        dedupe_key=dedupe_key,
        upload_batch_id="graf_yandex_batch_" + hashlib.sha256(
            f"{event.event_name}|{event.occurred_at.date().isoformat()}".encode()
        ).hexdigest()[:16],
        upload_state="queued",
        attribution_reliability=event.properties.get("attribution_reliability"),
    )


def _identity_source_for_event(event: ProductActivationEvent) -> tuple[str, str]:
    if event.properties.get("yandex_user_id_present") is True and event.stable_pseudonymous_user_id:
        return "UserId", "graf_pseudonymous_user_redacted"
    if event.properties.get("yandex_client_id_present") is True:
        return "ClientId", "runtime_yandex_client_id_redacted"
    if event.properties.get("yclid_present") is True:
        return "Yclid", "runtime_yclid_redacted"
    raise ValueError("Yandex offline conversion requires UserId, ClientId, or Yclid source")


def _dedupe_key(event: ProductActivationEvent, identity_kind: str) -> str:
    identity_material = _dedupe_identity_material(event, identity_kind)
    material = "|".join(
        (
            event.event_name,
            identity_kind,
            identity_material,
            event.occurred_at.isoformat(),
        )
    )
    return "graf_yandex_dedupe_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:32]


def _dedupe_identity_material(event: ProductActivationEvent, identity_kind: str) -> str:
    if identity_kind == "UserId":
        if not event.stable_pseudonymous_user_id:
            raise ValueError("Yandex UserId dedupe requires a stable pseudonymous user identity")
        return event.stable_pseudonymous_user_id
    return f"{identity_kind}:runtime_identity_pending"


class YandexOfflineConversionExporter:
    def __init__(
        self,
        *,
        enabled: bool,
        counter_id: str | None,
        oauth_token_file: Path | None,
        oauth_file_present: bool,
        validation_mode: str,
        live_delivery_allowed: bool,
        transport: ProviderTransport | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.enabled = enabled
        self.counter_id = counter_id.strip() if counter_id else None
        self.oauth_token_file = oauth_token_file
        self.oauth_file_present = oauth_file_present
        self.validation_mode = validation_mode
        self.live_delivery_allowed = live_delivery_allowed
        self.transport = transport or _default_multipart_transport
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> YandexOfflineConversionExporter:
        oauth_status = secret_file_status(
            settings.product_analytics_yandex_oauth_token_file,
            logical_name="YANDEX_OAUTH_TOKEN",
        )
        return cls(
            enabled=settings.product_analytics_yandex_offline_enabled,
            counter_id=settings.product_analytics_yandex_counter_id,
            oauth_token_file=settings.product_analytics_yandex_oauth_token_file,
            oauth_file_present=oauth_status.present,
            validation_mode=settings.product_analytics_validation_mode,
            live_delivery_allowed=settings.product_analytics_live_provider_delivery_allowed(),
        )

    def export(self, event: ProductActivationEvent) -> ProviderDeliveryResult:
        if not is_yandex_offline_event_allowed(event.event_name):
            return ProviderDeliveryResult("yandex_offline", "not_applicable", "Event is not in Yandex offline subset")
        if not self.enabled:
            return ProviderDeliveryResult("yandex_offline", "disabled", "Yandex offline conversions are disabled")
        if not self.counter_id or not self.oauth_token_file or not self.oauth_file_present:
            return ProviderDeliveryResult(
                "yandex_offline",
                "configuration_error",
                "Yandex counter and auth secret file are required before offline conversion upload",
            )
        row = build_yandex_offline_conversion(event)
        if self.validation_mode == "provider_smoke":
            return ProviderDeliveryResult("yandex_offline", "dry_run", "Provider smoke mode does not upload conversions")
        if self.validation_mode != "live_safe" or not self.live_delivery_allowed:
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_blocked",
                "Live Yandex offline upload requires explicit rollout approval",
                retryable=True,
            )
        try:
            oauth_token = read_secret_file(self.oauth_token_file, logical_name="YANDEX_OAUTH_TOKEN").value
            upload_body, upload_headers = build_yandex_offline_multipart_body(row, event)
        except (ProviderSecretError, ValueError):
            return ProviderDeliveryResult(
                "yandex_offline",
                "configuration_error",
                "Yandex offline upload requires a readable OAuth token file and supported runtime identity",
                retryable=False,
            )
        url = _upload_url(self.counter_id)
        headers = {
            **upload_headers,
            "Authorization": f"OAuth {oauth_token}",
        }
        try:
            response = self.transport(url, headers, upload_body, self.timeout_seconds)
        except (OSError, TimeoutError) as exc:
            return ProviderDeliveryResult(
                "yandex_offline",
                "network_error",
                "Yandex offline upload endpoint was not reachable",
                retryable=True,
                metadata={"error": exc.__class__.__name__},
            )
        if 200 <= response.status_code < 300:
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_uploaded",
                "Yandex offline conversion upload accepted the live-safe batch",
                metadata={
                    "event_name": row.event_name,
                    "identity_kind": row.identity_kind,
                    "line_count": 1,
                    "counter_id": "configured_redacted",
                    "oauth_token": "configured_redacted",
                    "provider_response": "redacted",
                    "upload_batch_id": row.upload_batch_id,
                },
            )
        return ProviderDeliveryResult(
            "yandex_offline",
            "provider_error",
            "Yandex offline upload endpoint returned a non-success status",
            retryable=response.status_code >= 500 or response.status_code == 429,
            metadata={"status_code": response.status_code, "provider_body": "redacted"},
        )


def build_yandex_offline_multipart_body(
    row: YandexOfflineConversionRow,
    event: ProductActivationEvent,
) -> tuple[bytes, dict[str, str]]:
    identity_value = _identity_value_for_upload(row, event)
    csv_body = _build_yandex_offline_csv(row, identity_value)
    boundary = "----graf096YandexOfflineConversionBoundary"
    multipart = (
        f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="offline-conversions.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        f"{csv_body}\r\n"
        f"--{boundary}--\r\n"
    ).encode()
    return multipart, {"Content-Type": f"multipart/form-data; boundary={boundary}"}


def _identity_value_for_upload(row: YandexOfflineConversionRow, event: ProductActivationEvent) -> str:
    if row.identity_kind == "UserId" and event.stable_pseudonymous_user_id:
        return event.stable_pseudonymous_user_id
    raise ValueError("runtime Yandex ClientId/Yclid resolver is not configured for this event")


def _build_yandex_offline_csv(row: YandexOfflineConversionRow, identity_value: str) -> str:
    buffer = io.StringIO()
    fields = ["Target", "DateTime", row.identity_kind, "PurchaseId"]
    writer = csv.DictWriter(buffer, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerow(
        {
            "Target": row.event_name,
            "DateTime": row.conversion_unix_time,
            row.identity_kind: identity_value,
            "PurchaseId": row.dedupe_key,
        }
    )
    return buffer.getvalue()


def _upload_url(counter_id: str) -> str:
    query = parse.urlencode({"type": "BASIC", "comment": "graf_096_product_activation"})
    return f"https://api-metrika.yandex.net/management/v1/counter/{counter_id}/offline_conversions/upload?{query}"


def _default_multipart_transport(
    url: str,
    headers: Mapping[str, str],
    body: bytes,
    timeout_seconds: float,
) -> ProviderTransportResponse:
    req = request.Request(url, data=body, headers=dict(headers), method="POST")
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            return ProviderTransportResponse(status_code=int(response.status), body=response.read(512).decode("utf-8"))
    except error.HTTPError as exc:
        return ProviderTransportResponse(status_code=int(exc.code), body=exc.read(512).decode("utf-8"))
