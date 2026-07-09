from __future__ import annotations

from dataclasses import dataclass, field

from twobrain_rec_server.product_analytics.event_catalog import PRODUCT_ACTIVATION_EVENT_NAMES

FIRST_MILESTONE_EVENTS = PRODUCT_ACTIVATION_EVENT_NAMES
USEFUL_RESULT_TYPES = ("transcript", "summary", "outcome", "action_items", "approved_equivalent")


@dataclass(slots=True)
class FirstMilestoneLedger:
    emitted: set[tuple[str, str]] = field(default_factory=set)

    def should_emit(self, stable_pseudonymous_user_id: str, event_name: str) -> bool:
        if event_name not in FIRST_MILESTONE_EVENTS:
            raise ValueError("event is not a first milestone")
        return (stable_pseudonymous_user_id, event_name) not in self.emitted

    def record(self, stable_pseudonymous_user_id: str, event_name: str) -> bool:
        if not self.should_emit(stable_pseudonymous_user_id, event_name):
            return False
        self.emitted.add((stable_pseudonymous_user_id, event_name))
        return True


@dataclass(frozen=True, slots=True)
class FirstValueDecision:
    eligible: bool
    reason: str
    useful_result_type: str | None = None


def first_value_decision(
    *,
    result_state: str,
    useful_output_present: bool,
    useful_result_type: str | None,
    imported_or_historical: bool = False,
) -> FirstValueDecision:
    if imported_or_historical:
        return FirstValueDecision(False, "imported_or_historical_result")
    if result_state != "ready":
        return FirstValueDecision(False, "result_not_ready")
    if not useful_output_present:
        return FirstValueDecision(False, "useful_output_absent")
    if useful_result_type not in USEFUL_RESULT_TYPES:
        return FirstValueDecision(False, "unsupported_useful_result_type")
    return FirstValueDecision(True, "ready_useful_result_viewed", useful_result_type)


def is_first_value_eligible(
    *,
    result_state: str,
    useful_output_present: bool,
    useful_result_type: str | None,
    imported_or_historical: bool = False,
) -> bool:
    return first_value_decision(
        result_state=result_state,
        useful_output_present=useful_output_present,
        useful_result_type=useful_result_type,
        imported_or_historical=imported_or_historical,
    ).eligible
