from __future__ import annotations

import csv
import hashlib
import io
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.advertising_transfer import (
    RECIPIENT_YANDEX_METRICA,
    TRANSFER_PURPOSE_OFFLINE_CONVERSIONS,
    AdvertisingTransferDecision,
    AdvertisingTransferRegister,
    OptionalMeasurementConsent,
    VisitorDisclosure,
    build_visitor_disclosure,
    evaluate_advertising_transfer,
    optional_measurement_consent_from_event,
    read_advertising_transfer_register,
    revocation_trace_lines,
)
from twobrain_rec_server.product_analytics.event_catalog import YANDEX_OFFLINE_CONVERSION_EVENTS
from twobrain_rec_server.product_analytics.events import ProductActivationEvent
from twobrain_rec_server.product_analytics.posthog_client import (
    ProviderDeliveryResult,
    ProviderTransport,
    ProviderTransportResponse,
)
from twobrain_rec_server.product_analytics.provider_delivery_gate import (
    resolve_provider_delivery_gate,
)
from twobrain_rec_server.product_analytics.provider_secrets import (
    ProviderSecretError,
    read_secret_file,
    secret_file_status,
)

# The recipient and the purpose of this transfer, spelled out so the gate and
# the provider client cannot disagree about what is being sent (FR-028).
YANDEX_OFFLINE_TRANSFER_RECIPIENT = RECIPIENT_YANDEX_METRICA
YANDEX_OFFLINE_TRANSFER_PURPOSE = TRANSFER_PURPOSE_OFFLINE_CONVERSIONS

# The visitor-facing consent copy of the site, read from the packaged templates
# when the caller does not hand over the rendered pages. A missing file leaves
# the page absent, and an absent page cannot disclose anything.
PUBLIC_CONSENT_PAGE_FILES: Mapping[str, str] = {
    "analytics_consent": "analytics_consent.html",
    "cookies": "cookies.html",
    "privacy": "privacy.html",
    "terms": "terms.html",
}


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


def _transfer_metadata(
    decision: AdvertisingTransferDecision,
    transfer_ref: str,
) -> dict[str, Any]:
    """Metadata of a refused transfer: named blockers and nothing personal.

    The refused transfer keeps the same opaque reference the provider would have
    received, so a retry of the very same data is recognisable and is refused
    again instead of being sent (FR-049). When the refusal comes from a
    revocation, the trace lines are returned too, so the caller can persist the
    evidence that the withdrawal reached the recipient.
    """

    metadata: dict[str, Any] = {
        "blockers": list(decision.blockers),
        "transfer_ref": transfer_ref,
        "recipient": decision.recipient,
        "purpose": decision.purpose,
        "transfer_facts": dict(decision.facts),
    }
    if decision.revocation_trace is not None:
        metadata["revocation_trace"] = dict(decision.revocation_trace)
        metadata["revocation_state_lines"] = list(
            revocation_trace_lines(decision.revocation_trace)
        )
    return metadata


def yandex_offline_transfer_ref(event: ProductActivationEvent) -> str:
    """The opaque reference of one transfer.

    It is the same value the provider receives as the purchase id, so a refused
    transfer and a delivered one are recognisably the same piece of data without
    naming a visitor (FR-049).
    """

    try:
        identity_kind, _ = _identity_source_for_event(event)
    except ValueError:
        identity_kind = "unresolved"
    return _dedupe_key(event, identity_kind)


def packaged_visitor_disclosure_pages() -> dict[str, str]:
    """Read the consent copy the site publishes from the packaged templates.

    The pages are what the visitor actually reads, which is the only honest
    source for "the transfer was disclosed". A template that cannot be read
    contributes nothing, and an incomplete disclosure blocks the transfer
    instead of being assumed.
    """

    from twobrain_rec_server.templates import package_path

    try:
        root = Path(package_path("twobrain_rec_server.public", "templates", "public"))
    except (ImportError, OSError, ModuleNotFoundError):
        return {}
    pages: dict[str, str] = {}
    for surface, filename in PUBLIC_CONSENT_PAGE_FILES.items():
        path = root / filename
        try:
            pages[surface] = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            continue
    return pages


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
        transfer_register: AdvertisingTransferRegister | None = None,
        visitor_disclosure: VisitorDisclosure | None = None,
        disclosure_revision: str | None = None,
        settings: Settings | None = None,
        environ: Mapping[str, str] | None = None,
        transport: ProviderTransport | None = None,
        timeout_seconds: float = 8.0,
    ) -> None:
        self.enabled = enabled
        self.counter_id = counter_id.strip() if counter_id else None
        self.oauth_token_file = oauth_token_file
        self.oauth_file_present = oauth_file_present
        self.validation_mode = validation_mode
        self.live_delivery_allowed = live_delivery_allowed
        # FR-028: the recorded basis and the disclosure the visitor saw are the
        # two conditions of the transfer. Without them the exporter has nothing
        # to transfer under, so both default to "absent".
        self.transfer_register = transfer_register
        self.visitor_disclosure = visitor_disclosure
        self.disclosure_revision = disclosure_revision
        self.settings = settings
        self.environ = environ
        self.transport = transport or _default_multipart_transport
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        environ: Mapping[str, str] | None = None,
        site_pages: Mapping[str, str] | None = None,
    ) -> YandexOfflineConversionExporter:
        oauth_status = secret_file_status(
            settings.product_analytics_yandex_oauth_token_file,
            logical_name="YANDEX_OAUTH_TOKEN",
        )
        pages = packaged_visitor_disclosure_pages() if site_pages is None else dict(site_pages)
        return cls(
            enabled=settings.product_analytics_yandex_offline_enabled,
            counter_id=settings.product_analytics_yandex_counter_id,
            oauth_token_file=settings.product_analytics_yandex_oauth_token_file,
            oauth_file_present=oauth_status.present,
            validation_mode=settings.product_analytics_validation_mode,
            live_delivery_allowed=settings.product_analytics_live_provider_delivery_allowed(),
            transfer_register=read_advertising_transfer_register(environ),
            visitor_disclosure=build_visitor_disclosure(pages),
            disclosure_revision=settings.public_analytics_consent_copy_version,
            settings=settings,
            environ=environ,
        )

    def transfer_decision(
        self,
        event: ProductActivationEvent,
        *,
        visitor_consent: OptionalMeasurementConsent | None = None,
    ) -> AdvertisingTransferDecision:
        """Ask the transfer gate about one event (FR-028, FR-029, FR-049).

        The transfer of a visitor's data is a level 3 action, so it happens only
        with that visitor's ``advertising_attribution`` decision. That decision
        belongs to the request that carried it, so the caller hands it over
        explicitly; the event's own categories are used only when the event
        carries them, and an absent decision is a refusal, never a permission.
        Nothing here reads a provider flag.
        """

        register = self.transfer_register
        consent = (
            visitor_consent
            if visitor_consent is not None
            else optional_measurement_consent_from_event(event)
        )
        return evaluate_advertising_transfer(
            purpose=YANDEX_OFFLINE_TRANSFER_PURPOSE,
            recipient=YANDEX_OFFLINE_TRANSFER_RECIPIENT,
            basis=(
                register.basis(
                    purpose=YANDEX_OFFLINE_TRANSFER_PURPOSE,
                    recipient=YANDEX_OFFLINE_TRANSFER_RECIPIENT,
                )
                if register is not None
                else None
            ),
            disclosure=self.visitor_disclosure,
            measurement_consent=consent,
            register=register,
            transfer_ref=yandex_offline_transfer_ref(event),
            expected_disclosure_revision=self.disclosure_revision,
        )

    def export(
        self,
        event: ProductActivationEvent,
        *,
        visitor_consent: OptionalMeasurementConsent | None = None,
    ) -> ProviderDeliveryResult:
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
        if self.validation_mode != "live_safe":
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_blocked",
                "Live Yandex offline upload requires explicit rollout approval",
                retryable=True,
            )
        # FR-028/FR-049: no confirmed basis, no visitor disclosure or a revoked
        # recipient means no transfer at all, and no secret is read and no
        # request is built before that is settled.
        decision = self.transfer_decision(event, visitor_consent=visitor_consent)
        if not decision.allowed:
            return ProviderDeliveryResult(
                "yandex_offline",
                decision.status,
                "Yandex offline conversion transfer is not authorised",
                retryable=False,
                metadata=_transfer_metadata(decision, row.dedupe_key),
            )
        if not self.live_delivery_allowed:
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_blocked",
                "Live Yandex offline upload requires explicit rollout approval",
                retryable=True,
            )
        if self.settings is None:
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_blocked",
                "Live Yandex offline upload requires a resolved readiness gate",
                retryable=True,
            )
        delivery_gate = resolve_provider_delivery_gate(
            self.settings,
            provider="yandex_offline",
            environ=self.environ,
        )
        if not delivery_gate.allowed:
            return ProviderDeliveryResult(
                "yandex_offline",
                "live_safe_blocked",
                "Live Yandex offline upload is blocked by rollout readiness",
                retryable=True,
                metadata={"blockers": list(delivery_gate.blockers)},
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
