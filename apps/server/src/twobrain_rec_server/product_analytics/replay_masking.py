from __future__ import annotations

from dataclasses import dataclass

from twobrain_rec_server.product_analytics.page_inventory import PageClassAnalyticsPolicy


@dataclass(frozen=True, slots=True)
class ReplayMaskingDecision:
    page_class: str
    launch_state: str
    replay_allowed: bool
    masking_required: bool
    attributes: dict[str, str]
    caveat: str

    def as_dict(self) -> dict[str, object]:
        return {
            "page_class": self.page_class,
            "launch_state": self.launch_state,
            "replay_allowed": self.replay_allowed,
            "masking_required": self.masking_required,
            "attributes": dict(self.attributes),
            "caveat": self.caveat,
        }


def masking_attributes() -> dict[str, str]:
    return {
        "data-graf-analytics-private": "true",
        "data-ph-mask": "true",
        "data-graf-replay-disabled": "true",
        "data-ym-hide-content": "true",
        "data-ym-disable-keys": "true",
    }


def replay_decision_for_policy(policy: PageClassAnalyticsPolicy) -> ReplayMaskingDecision:
    replay_allowed = policy.posthog_replay_allowed and policy.yandex_webvisor_allowed
    return ReplayMaskingDecision(
        page_class=policy.page_class,
        launch_state=policy.launch_state,
        replay_allowed=replay_allowed,
        masking_required=not replay_allowed,
        attributes={} if replay_allowed else masking_attributes(),
        caveat=policy.dashboard_caveat,
    )
