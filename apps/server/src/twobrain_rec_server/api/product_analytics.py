from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.api.schemas import Problem
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.product_analytics.event_catalog import (
    catalog_payload,
    yandex_offline_conversion_event_names,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.identity import is_safe_pseudonymous_id
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.page_inventory import page_class_policies
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper
from twobrain_rec_server.product_analytics.provider_config import ProductAnalyticsProviderConfig
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
from twobrain_rec_server.product_analytics.readiness import build_rollout_readiness_report
from twobrain_rec_server.product_analytics.retention import (
    provider_lifecycle_records,
    retention_rules,
)
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


class PostHogAutocaptureEventRequest(BaseModel):
    distinct_id: str | None = Field(default=None, max_length=120)
    event_type: Literal["ready", "pageview", "click"] = "pageview"
    page_class: str = Field(min_length=1, max_length=80)
    path_class: str | None = Field(default=None, max_length=80)
    tag_name: str | None = Field(default=None, max_length=24)
    role: str | None = Field(default=None, max_length=80)
    analytics_action: str | None = Field(default=None, max_length=80)
    analytics_target: str | None = Field(default=None, max_length=80)
    identity_state: str | None = Field(default=None, max_length=80)
    workspace_pseudonym: str | None = Field(default=None, max_length=120)
    device_class: str | None = Field(default=None, max_length=80)
    sensitivity: str | None = Field(default=None, max_length=40)
    source: str = Field(default="browser_autocapture", max_length=80)


class PostHogDesktopCaptureRequest(BaseModel):
    event: str = Field(min_length=1)
    distinct_id: str = Field(min_length=1, max_length=120)
    timestamp: datetime | None = None
    telemetry_gate_state: str = "accepted"
    properties: dict[str, Any] = Field(default_factory=dict)
    api_key_state: str = "server_injected_redacted"


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
        "provider_config": ProductAnalyticsProviderConfig.from_settings(settings).as_redacted_dict(),
        "provider_lifecycle": [record.as_dict() for record in provider_lifecycle_records()],
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


@router.post("/posthog-web-capture")
async def product_analytics_posthog_web_capture(
    request: Request,
    body: PostHogAutocaptureEventRequest,
) -> dict[str, Any]:
    settings = _settings_from_request(request)
    provider_config = ProductAnalyticsProviderConfig.from_settings(settings)
    if not (
        settings.product_analytics_enabled
        and provider_config.posthog.enabled
        and provider_config.posthog.autocapture_enabled
        and provider_config.posthog.web_direct_enabled
        and provider_config.posthog.credential_suppression_enabled
    ):
        raise ProblemDetail(
            status=403,
            code="posthog_autocapture_disabled",
            title="PostHog autocapture disabled",
            detail="PostHog web autocapture is disabled or missing credential suppression.",
        )
    distinct_id = body.distinct_id or "graf_pseudo_browser_anonymous"
    if not is_safe_pseudonymous_id(distinct_id):
        raise ProblemDetail(
            status=400,
            code="posthog_autocapture_identity_rejected",
            title="PostHog autocapture identity rejected",
            detail="Autocapture distinct_id must be a GRAF pseudonymous analytics identity.",
        )
    if body.workspace_pseudonym and not is_safe_pseudonymous_id(body.workspace_pseudonym):
        raise ProblemDetail(
            status=400,
            code="posthog_autocapture_workspace_identity_rejected",
            title="PostHog autocapture workspace identity rejected",
            detail="Autocapture workspace pseudonym must be a GRAF pseudonymous analytics identity.",
        )
    properties = body.model_dump(exclude_none=True)
    properties.update(
        {
            "delivery_mode": "first_party_browser_proxy",
            "source_feature": "096-product-analytics-provider-rollout",
            "replay_enabled": False,
        }
    )
    result = PostHogClientWrapper.from_settings(settings).capture_event(
        event_name=f"graf_web_autocapture_{body.event_type}",
        distinct_id=distinct_id,
        properties=properties,
    )
    if result.status == "payload_rejected":
        raise ProblemDetail(
            status=400,
            code="posthog_autocapture_rejected",
            title="PostHog autocapture event rejected",
            detail="Autocapture event contained forbidden analytics material.",
        )
    if result.status in {"configuration_error", "disabled"}:
        raise ProblemDetail(
            status=403,
            code=f"posthog_autocapture_{result.status}",
            title="PostHog autocapture event not accepted",
            detail=result.detail,
        )
    return result.as_dict()


@router.post("/posthog-desktop-capture")
async def product_analytics_posthog_desktop_capture(
    request: Request,
    body: PostHogDesktopCaptureRequest,
) -> dict[str, Any]:
    settings = _settings_from_request(request)
    if not (
        settings.product_analytics_enabled
        and settings.product_analytics_posthog_enabled
        and settings.product_analytics_posthog_desktop_direct_enabled
        and settings.product_analytics_direct_desktop_egress_enabled
    ):
        raise ProblemDetail(
            status=403,
            code="posthog_desktop_direct_disabled",
            title="PostHog desktop direct route disabled",
            detail="Desktop PostHog direct routing requires explicit runtime enablement and disclosure gates.",
        )
    if body.telemetry_gate_state != "accepted":
        raise ProblemDetail(
            status=403,
            code="posthog_desktop_telemetry_not_accepted",
            title="Product analytics telemetry not accepted",
        )
    if body.api_key_state != "server_injected_redacted":
        raise ProblemDetail(
            status=400,
            code="posthog_desktop_secret_state_invalid",
            title="PostHog desktop route must not include a project key",
        )
    event_properties = {
        key: value
        for key, value in body.properties.items()
        if key not in {"delivery_mode", "source_feature", "api_key_state"}
    }
    try:
        event = build_activation_event(
            body.event,
            stable_pseudonymous_user_id=body.distinct_id,
            occurred_at=body.timestamp,
            properties=event_properties,
        )
    except ValueError as exc:
        raise ProblemDetail(
            status=400,
            code="posthog_desktop_event_rejected",
            title="PostHog desktop event rejected",
            detail=str(exc),
        ) from exc
    properties = dict(event.properties)
    properties.update(
        {
            "surface": event.surface,
            "owner": event.owner,
            "delivery_mode": "first_party_desktop_proxy",
            "source_feature": "096-product-analytics-provider-rollout",
        }
    )
    result = PostHogClientWrapper.from_settings(settings).capture_event(
        event_name=event.event_name,
        distinct_id=event.stable_pseudonymous_user_id,
        properties=properties,
        timestamp=event.occurred_at,
    )
    if result.status == "payload_rejected":
        raise ProblemDetail(
            status=400,
            code="posthog_desktop_payload_rejected",
            title="PostHog desktop payload rejected",
            detail="PostHog desktop payload contained forbidden analytics material.",
        )
    if result.status in {"configuration_error", "disabled"}:
        raise ProblemDetail(
            status=403,
            code=f"posthog_desktop_{result.status}",
            title="PostHog desktop event not accepted",
            detail=result.detail,
        )
    return result.as_dict()
