from __future__ import annotations

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import ProductActivationEvent
from twobrain_rec_server.product_analytics.posthog_client import (
    PostHogClientWrapper,
    ProviderDeliveryResult,
)
from twobrain_rec_server.product_analytics.yandex_offline import YandexOfflineConversionExporter


class ParallelMeasurementRouter:
    def __init__(self, settings: Settings) -> None:
        self.posthog = PostHogClientWrapper.from_settings(settings)
        self.yandex_offline = YandexOfflineConversionExporter.from_settings(settings)

    def dispatch(self, event: ProductActivationEvent) -> list[ProviderDeliveryResult]:
        return [
            self.posthog.capture(event),
            self.yandex_offline.export(event),
        ]
