from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.delivery_gap import (
    AnalyticsDeliveryGap,
    build_delivery_gap,
)
from twobrain_rec_server.product_analytics.events import (
    ProductActivationEvent,
    build_activation_event,
)
from twobrain_rec_server.product_analytics.milestones import (
    MILESTONE_STATUS_DUPLICATE,
    default_milestone_guard,
    is_first_milestone_event,
)
from twobrain_rec_server.product_analytics.posthog_client import ProviderDeliveryResult
from twobrain_rec_server.product_analytics.router import ParallelMeasurementRouter
from twobrain_rec_server.product_analytics.telemetry_gate import analytics_collection_allowed


@dataclass(frozen=True, slots=True)
class ProductAnalyticsIngestResult:
    accepted: bool
    status: str
    event: ProductActivationEvent | None
    provider_results: list[ProviderDeliveryResult]
    delivery_gap: AnalyticsDeliveryGap | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "status": self.status,
            "event": self.event.as_payload() if self.event else None,
            "provider_results": [result.as_dict() for result in self.provider_results],
            "delivery_gap": self.delivery_gap.as_dict() if self.delivery_gap else None,
        }


class ProductAnalyticsIngestService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.measurement_router = ParallelMeasurementRouter(settings)

    def ingest(
        self,
        payload: Mapping[str, Any],
        *,
        telemetry_gate_state: str = "accepted",
    ) -> ProductAnalyticsIngestResult:
        if not self.settings.product_analytics_enabled:
            return ProductAnalyticsIngestResult(False, "disabled", None, [])
        if not analytics_collection_allowed(telemetry_gate_state):
            return ProductAnalyticsIngestResult(False, "telemetry_gate_required", None, [])
        event = build_activation_event(
            str(payload.get("event_name", "")),
            stable_pseudonymous_user_id=payload.get("stable_pseudonymous_user_id"),
            occurred_at=_parse_occurred_at(payload.get("occurred_at")),
            properties=payload.get("properties") if isinstance(payload.get("properties"), Mapping) else {},
        )
        if is_first_milestone_event(event.event_name):
            # The decision is made before any provider sees the event, so a
            # repeated submission of one milestone is acknowledged and counted
            # once (FR-025). The app keeps its own durable copy of the same rule.
            acceptance = default_milestone_guard().accept(
                stable_pseudonymous_user_id=event.stable_pseudonymous_user_id,
                event_name=event.event_name,
            )
            if acceptance.duplicate:
                return ProductAnalyticsIngestResult(
                    True,
                    MILESTONE_STATUS_DUPLICATE,
                    event,
                    [],
                    None,
                )
        provider_results = self.measurement_router.dispatch(event)
        return ProductAnalyticsIngestResult(
            True,
            "accepted",
            event,
            provider_results,
            build_delivery_gap(event.event_name, provider_results),
        )


def _parse_occurred_at(value: object) -> datetime | None:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise ValueError("occurred_at must be an ISO-8601 timestamp")
