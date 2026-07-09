from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import Problem
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.product_analytics.event_catalog import (
    catalog_payload,
    yandex_offline_conversion_event_names,
)
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.page_inventory import page_class_policies
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report
from twobrain_rec_server.product_analytics.retention import retention_rules
from twobrain_rec_server.product_analytics.telemetry_gate import (
    build_required_disclosure,
    is_product_use_allowed,
    limited_access_only,
    requires_acceptance,
)


class ProductAnalyticsEventRequest(BaseModel):
    event_name: str = Field(min_length=1)
    stable_pseudonymous_user_id: str | None = None
    occurred_at: datetime | None = None
    telemetry_gate_state: str = "accepted"
    properties: dict[str, Any] = Field(default_factory=dict)


PROBLEM_RESPONSES = {
    400: {"model": Problem, "description": "Bad request"},
    403: {"model": Problem, "description": "Forbidden"},
    422: {"model": Problem, "description": "Validation error"},
}

router = APIRouter(
    prefix="/api/v1/product-analytics",
    tags=["product-analytics"],
    responses=PROBLEM_RESPONSES,
    include_in_schema=True,
)


def _settings_from_request(request: Request) -> Settings:
    return getattr(request.app.state, "settings", None) or get_settings()


@router.get("/catalog")
async def product_analytics_catalog(request: Request) -> dict[str, Any]:
    settings = _settings_from_request(request)
    return {
        "enabled": settings.product_analytics_enabled,
        "validation_mode": settings.product_analytics_validation_mode,
        "provider_mode": settings.product_analytics_provider_mode,
        "events": catalog_payload(),
        "yandex_offline_conversion_events": list(yandex_offline_conversion_event_names()),
        "page_classes": [policy.as_dict() for policy in page_class_policies()],
        "retention": [rule.as_dict() for rule in retention_rules()],
        "providers": build_provider_readiness(settings).as_dict(),
        "rollout_readiness": build_rollout_readiness_report(settings).as_dict(),
    }


@router.get("/telemetry-gate/disclosure")
async def product_analytics_telemetry_gate_disclosure(request: Request) -> dict[str, Any]:
    settings = _settings_from_request(request)
    return build_required_disclosure(
        direct_desktop_egress=settings.product_analytics_direct_desktop_egress_enabled
    )


@router.get("/telemetry-gate/access")
async def product_analytics_telemetry_gate_access(state: str = "not_seen") -> dict[str, Any]:
    return {
        "state": state,
        "product_use_allowed": is_product_use_allowed(state),
        "requires_acceptance": requires_acceptance(state),
        "limited_access_only": limited_access_only(state),
    }


@router.post("/events")
async def product_analytics_events(request: Request, body: ProductAnalyticsEventRequest) -> dict[str, Any]:
    settings = _settings_from_request(request)
    if not settings.product_analytics_enabled:
        raise ProblemDetail(
            status=403,
            code="product_analytics_disabled",
            title="Product analytics disabled",
            detail="094 product analytics is disabled unless an explicit validation/rollout gate enables it.",
        )
    service = ProductAnalyticsIngestService(settings)
    try:
        result = service.ingest(body.model_dump(), telemetry_gate_state=body.telemetry_gate_state)
    except ValueError as exc:
        raise ProblemDetail(
            status=400,
            code="product_analytics_event_rejected",
            title="Product analytics event rejected",
            detail=str(exc),
        ) from exc
    if not result.accepted:
        raise ProblemDetail(
            status=403,
            code=f"product_analytics_{result.status}",
            title="Product analytics event not accepted",
        )
    return result.as_dict()
