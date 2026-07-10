from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.event_catalog import YANDEX_OFFLINE_CONVERSION_EVENTS
from twobrain_rec_server.product_analytics.events import ProductActivationEvent
from twobrain_rec_server.product_analytics.posthog_client import ProviderDeliveryResult


@dataclass(frozen=True, slots=True)
class YandexOfflineConversionRow:
    event_name: str
    conversion_date_time: str
    stable_pseudonymous_user_id: str | None
    attribution_reliability: str | None

    def as_dict(self) -> dict[str, str | None]:
        return {
            "event_name": self.event_name,
            "conversion_date_time": self.conversion_date_time,
            "stable_pseudonymous_user_id": self.stable_pseudonymous_user_id,
            "attribution_reliability": self.attribution_reliability,
        }


def is_yandex_offline_event_allowed(event_name: str) -> bool:
    return event_name in YANDEX_OFFLINE_CONVERSION_EVENTS


def build_yandex_offline_conversion(event: ProductActivationEvent) -> YandexOfflineConversionRow:
    if not is_yandex_offline_event_allowed(event.event_name):
        raise ValueError("event is not in the default Yandex offline conversion subset")
    return YandexOfflineConversionRow(
        event_name=event.event_name,
        conversion_date_time=event.occurred_at.isoformat(),
        stable_pseudonymous_user_id=event.stable_pseudonymous_user_id,
        attribution_reliability=event.properties.get("attribution_reliability"),
    )


class YandexOfflineConversionExporter:
    def __init__(self, *, enabled: bool, counter_present: bool, oauth_file_present: bool, validation_mode: str) -> None:
        self.enabled = enabled
        self.counter_present = counter_present
        self.oauth_file_present = oauth_file_present
        self.validation_mode = validation_mode

    @classmethod
    def from_settings(cls, settings: Settings) -> YandexOfflineConversionExporter:
        return cls(
            enabled=settings.product_analytics_yandex_offline_enabled,
            counter_present=settings.product_analytics_yandex_counter_id is not None,
            oauth_file_present=settings.product_analytics_yandex_oauth_token_file is not None,
            validation_mode=settings.product_analytics_validation_mode,
        )

    def export(self, event: ProductActivationEvent) -> ProviderDeliveryResult:
        if not is_yandex_offline_event_allowed(event.event_name):
            return ProviderDeliveryResult("yandex_offline", "not_applicable", "Event is not in Yandex offline subset")
        if not self.enabled:
            return ProviderDeliveryResult("yandex_offline", "disabled", "Yandex offline conversions are disabled")
        if not self.counter_present or not self.oauth_file_present:
            return ProviderDeliveryResult(
                "yandex_offline",
                "configuration_error",
                "Yandex counter ID and OAuth token file are required before offline conversion upload",
            )
        _ = build_yandex_offline_conversion(event)
        if self.validation_mode == "provider_smoke":
            return ProviderDeliveryResult("yandex_offline", "dry_run", "Provider smoke mode does not upload conversions")
        return ProviderDeliveryResult("yandex_offline", "blocked", "Live Yandex upload is blocked by 094 rollout gate")
