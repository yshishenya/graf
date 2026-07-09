from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from twobrain_rec_server.product_analytics.posthog_client import ProviderDeliveryResult

_NON_GAP_STATUSES = {"delivered", "dry_run", "not_applicable"}


@dataclass(frozen=True, slots=True)
class AnalyticsDeliveryGap:
    event_name: str
    providers: tuple[str, ...]
    status: str
    caveat: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_name": self.event_name,
            "providers": list(self.providers),
            "status": self.status,
            "caveat": self.caveat,
        }


def build_delivery_gap(
    event_name: str,
    provider_results: list[ProviderDeliveryResult],
) -> AnalyticsDeliveryGap | None:
    gap_providers = tuple(
        result.provider for result in provider_results if result.status not in _NON_GAP_STATUSES
    )
    if not gap_providers:
        return None
    return AnalyticsDeliveryGap(
        event_name=event_name,
        providers=gap_providers,
        status="measurement_gap",
        caveat="Provider delivery did not complete; product use must continue and dashboards must disclose this gap.",
    )
