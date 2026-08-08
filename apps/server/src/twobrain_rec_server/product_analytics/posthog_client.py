from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib import error, request

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import ProductActivationEvent
from twobrain_rec_server.product_analytics.forbidden_fields import (
    assert_no_forbidden_fields,
    assert_no_security_credential_fields,
)
from twobrain_rec_server.product_analytics.provider_secrets import (
    ProviderSecretError,
    read_secret_file,
    secret_file_status,
)


@dataclass(frozen=True, slots=True)
class ProviderTransportResponse:
    status_code: int
    body: str = ""


ProviderTransport = Callable[[str, Mapping[str, str], bytes, float], ProviderTransportResponse]


@dataclass(frozen=True, slots=True)
class ProviderDeliveryResult:
    provider: str
    status: str
    detail: str
    retryable: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        body = {
            "provider": self.provider,
            "status": self.status,
            "detail": self.detail,
            "retryable": self.retryable,
        }
        if self.metadata:
            body["metadata"] = dict(self.metadata)
        return body


class PostHogClientWrapper:
    def __init__(
        self,
        *,
        enabled: bool,
        host: str | None,
        project_key_file: Path | None,
        project_key_present: bool,
        validation_mode: str,
        live_delivery_allowed: bool,
        transport: ProviderTransport | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        self.enabled = enabled
        self.host = host.rstrip("/") if host else None
        self.project_key_file = project_key_file
        self.project_key_present = project_key_present
        self.validation_mode = validation_mode
        self.live_delivery_allowed = live_delivery_allowed
        self.transport = transport or _default_json_transport
        self.timeout_seconds = timeout_seconds

    @classmethod
    def from_settings(cls, settings: Settings) -> PostHogClientWrapper:
        project_key_status = secret_file_status(
            settings.product_analytics_posthog_project_key_file,
            logical_name="POSTHOG_PROJECT_KEY",
        )
        return cls(
            enabled=settings.product_analytics_posthog_enabled,
            host=str(settings.product_analytics_posthog_host) if settings.product_analytics_posthog_host else None,
            project_key_file=settings.product_analytics_posthog_project_key_file,
            project_key_present=project_key_status.present,
            validation_mode=settings.product_analytics_validation_mode,
            live_delivery_allowed=settings.product_analytics_live_provider_delivery_allowed(),
        )

    def capture(self, event: ProductActivationEvent) -> ProviderDeliveryResult:
        if not self.enabled:
            return ProviderDeliveryResult("posthog", "disabled", "PostHog product analytics is disabled")
        if not event.stable_pseudonymous_user_id:
            return ProviderDeliveryResult(
                "posthog",
                "identity_missing",
                "PostHog delivery requires a stable pseudonymous analytics identity",
                retryable=False,
            )
        properties = dict(event.properties)
        properties.update(
            {
                "surface": event.surface,
                "owner": event.owner,
                "delivery_mode": event.delivery_mode,
                "source_feature": "096-product-analytics-provider-rollout",
            }
        )
        return self.capture_event(
            event_name=event.event_name,
            distinct_id=event.stable_pseudonymous_user_id,
            properties=properties,
            timestamp=event.occurred_at,
        )

    def capture_event(
        self,
        *,
        event_name: str,
        distinct_id: str,
        properties: Mapping[str, Any],
        timestamp: datetime | None = None,
    ) -> ProviderDeliveryResult:
        if not self.enabled:
            return ProviderDeliveryResult("posthog", "disabled", "PostHog product analytics is disabled")
        if not self.host or not self.project_key_file or not self.project_key_present:
            return ProviderDeliveryResult(
                "posthog",
                "configuration_error",
                "PostHog host and project key file are required before delivery",
                retryable=False,
            )
        try:
            # Browser autocapture reaches this wrapper without going through
            # ``build_activation_event``.  Enforce the complete privacy
            # boundary here as well, so a harmless-looking field (for example
            # a DOM role containing an email address) cannot leave GRAF.
            assert_no_forbidden_fields(properties)
            assert_no_security_credential_fields(properties)
        except ValueError as exc:
            return ProviderDeliveryResult(
                "posthog",
                "payload_rejected",
                "PostHog payload contains credential, secret, local-path, or raw-content material",
                retryable=False,
                metadata={"rejection": exc.__class__.__name__},
            )
        if self.validation_mode == "provider_smoke":
            return ProviderDeliveryResult("posthog", "dry_run", "Provider smoke mode does not send live events")
        if self.validation_mode != "live_safe" or not self.live_delivery_allowed:
            return ProviderDeliveryResult(
                "posthog",
                "live_safe_blocked",
                "Live PostHog delivery requires explicit production rollout approval",
                retryable=True,
            )
        try:
            project_key = read_secret_file(self.project_key_file, logical_name="POSTHOG_PROJECT_KEY").value
        except ProviderSecretError:
            return ProviderDeliveryResult(
                "posthog",
                "configuration_error",
                "PostHog project key file is missing, empty, or unreadable",
                retryable=False,
            )
        body = {
            "api_key": project_key,
            "event": event_name,
            "distinct_id": distinct_id,
            "timestamp": (timestamp or datetime.now(UTC)).isoformat(),
            "properties": dict(properties),
        }
        try:
            response = self.transport(
                f"{self.host}/capture/",
                {"Content-Type": "application/json"},
                json.dumps(body, separators=(",", ":"), sort_keys=True).encode("utf-8"),
                self.timeout_seconds,
            )
        except (OSError, TimeoutError) as exc:
            return ProviderDeliveryResult(
                "posthog",
                "network_error",
                "PostHog capture endpoint was not reachable",
                retryable=True,
                metadata={"error": exc.__class__.__name__},
            )
        if 200 <= response.status_code < 300:
            return ProviderDeliveryResult(
                "posthog",
                "live_safe_sent",
                "PostHog capture accepted the metadata-only live-safe event",
                metadata={
                    "endpoint": "self_hosted_capture",
                    "event_name": event_name,
                    "payload": "redacted",
                    "project_key": "configured_redacted",
                },
            )
        return ProviderDeliveryResult(
            "posthog",
            "provider_error",
            "PostHog capture endpoint returned a non-success status",
            retryable=response.status_code >= 500 or response.status_code == 429,
            metadata={"status_code": response.status_code, "provider_body": "redacted"},
        )


def _default_json_transport(
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
