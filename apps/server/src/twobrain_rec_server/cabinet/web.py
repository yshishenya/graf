from __future__ import annotations

from fastapi import APIRouter

from twobrain_rec_server.cabinet.web_routes import (
    auth,
    browser,
    calendar,
    deletion,
    desktop,
    provider_links,
    spaces,
    static,
)
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.milestones import first_value_decision
from twobrain_rec_server.product_analytics.telemetry_gate import build_required_disclosure

router = APIRouter(tags=["cabinet-web"])
router.include_router(static.router)
router.include_router(auth.router)
router.include_router(browser.router)
router.include_router(calendar.router)
router.include_router(provider_links.router)
router.include_router(spaces.router)
router.include_router(deletion.router)
router.include_router(desktop.router)


def build_first_result_viewed_product_analytics_payload(
    *,
    stable_pseudonymous_user_id: str,
    result_state: str,
    useful_output_present: bool,
    surface: str = "cabinet_web",
    elapsed_bucket: str | None = None,
) -> dict[str, object]:
    event = build_activation_event(
        "first_result_viewed",
        stable_pseudonymous_user_id=stable_pseudonymous_user_id,
        properties={
            "result_state": result_state,
            "useful_output_present": useful_output_present,
            "surface": surface,
            **({"elapsed_bucket": elapsed_bucket} if elapsed_bucket else {}),
        },
    )
    return event.as_payload()


def build_first_value_product_analytics_payload(
    *,
    stable_pseudonymous_user_id: str,
    result_state: str,
    useful_output_present: bool,
    useful_result_type: str | None,
    elapsed_bucket: str | None = None,
) -> dict[str, object] | None:
    decision = first_value_decision(
        result_state=result_state,
        useful_output_present=useful_output_present,
        useful_result_type=useful_result_type,
    )
    if not decision.eligible:
        return None
    event = build_activation_event(
        "first_value_session_completed",
        stable_pseudonymous_user_id=stable_pseudonymous_user_id,
        properties={
            "first_recording_completed": True,
            "first_result_viewed": True,
            "useful_output_present": True,
            "useful_result_type": decision.useful_result_type,
            "attribution_reliability": "campaign_linked_reliable",
            **({"elapsed_bucket": elapsed_bucket} if elapsed_bucket else {}),
        },
    )
    return event.as_payload()


def cabinet_product_telemetry_gate_context(*, direct_desktop_egress: bool = False) -> dict[str, object]:
    return build_required_disclosure(direct_desktop_egress=direct_desktop_egress)
