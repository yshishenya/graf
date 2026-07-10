from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import ProductActivationEvent


@dataclass(frozen=True, slots=True)
class ProviderDeliveryResult:
    provider: str
    status: str
    detail: str
    retryable: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "status": self.status,
            "detail": self.detail,
            "retryable": self.retryable,
        }


class PostHogClientWrapper:
    def __init__(self, *, enabled: bool, host_present: bool, project_key_present: bool, validation_mode: str) -> None:
        self.enabled = enabled
        self.host_present = host_present
        self.project_key_present = project_key_present
        self.validation_mode = validation_mode

    @classmethod
    def from_settings(cls, settings: Settings) -> PostHogClientWrapper:
        return cls(
            enabled=settings.product_analytics_posthog_enabled,
            host_present=settings.product_analytics_posthog_host is not None,
            project_key_present=settings.product_analytics_posthog_project_key_file is not None,
            validation_mode=settings.product_analytics_validation_mode,
        )

    def capture(self, event: ProductActivationEvent) -> ProviderDeliveryResult:
        _ = event
        if not self.enabled:
            return ProviderDeliveryResult("posthog", "disabled", "PostHog product analytics is disabled")
        if not self.host_present or not self.project_key_present:
            return ProviderDeliveryResult(
                "posthog",
                "configuration_error",
                "PostHog host and project key file are required before delivery",
                retryable=False,
            )
        if self.validation_mode == "provider_smoke":
            return ProviderDeliveryResult("posthog", "dry_run", "Provider smoke mode does not send live events")
        return ProviderDeliveryResult("posthog", "blocked", "Live PostHog delivery is blocked by 094 rollout gate")
