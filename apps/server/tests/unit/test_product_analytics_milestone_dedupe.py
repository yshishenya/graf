"""FR-025: повторная отправка вехи не удваивает счёт (T052).

Решение принимается до того, как событие увидит провайдер, поэтому повторная
отправка не доходит ни до PostHog, ни до офлайн-конверсии Яндекса. Журнал
отправленных вех по умолчанию живёт в процессе, поэтому каждый тест берёт свой
псевдонимный идентификатор и не зависит от других тестов.
"""

from uuid import uuid4

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.identity import build_safe_identity
from twobrain_rec_server.product_analytics.ingest import ProductAnalyticsIngestService
from twobrain_rec_server.product_analytics.milestones import (
    MILESTONE_DEDUPE_RULE,
    MILESTONE_STATUS_DUPLICATE,
    MilestoneEmissionGuard,
    is_first_milestone_event,
    milestone_attribution_properties,
)

MILESTONE = "desktop_first_opened"
OTHER_MILESTONE = "first_value_session_completed"
RELIABILITY_LEVELS = {"linked", "weak", "unknown"}


def _pseudonymous_user() -> str:
    return build_safe_identity(user_source_id=str(uuid4())).stable_pseudonymous_user_id


def test_a_milestone_is_counted_once_per_pseudonymous_user() -> None:
    guard = MilestoneEmissionGuard()
    user = _pseudonymous_user()
    other_user = _pseudonymous_user()

    first = guard.accept(stable_pseudonymous_user_id=user, event_name=MILESTONE)

    assert first.accepted is True
    assert first.status == "accepted"
    assert first.duplicate is False
    assert first.dedupe_key == f"{user}|{MILESTONE}"
    assert guard.counted(stable_pseudonymous_user_id=user, event_name=MILESTONE) is True
    assert guard.counted(stable_pseudonymous_user_id=other_user, event_name=MILESTONE) is False

    repeated = guard.accept(stable_pseudonymous_user_id=user, event_name=MILESTONE)

    assert repeated.accepted is False
    assert repeated.status == MILESTONE_STATUS_DUPLICATE == "duplicate"
    assert repeated.duplicate is True
    assert repeated.reason == "milestone_already_counted"
    assert repeated.dedupe_key == first.dedupe_key

    # Другой псевдонимный пользователь и другая веха — свои первые события.
    assert (
        guard.accept(stable_pseudonymous_user_id=other_user, event_name=MILESTONE).accepted is True
    )
    assert (
        guard.accept(stable_pseudonymous_user_id=user, event_name=OTHER_MILESTONE).accepted is True
    )
    assert MILESTONE_DEDUPE_RULE == "first_milestone_per_pseudonymous_user"


def test_a_milestone_without_identity_is_counted_unlinked() -> None:
    guard = MilestoneEmissionGuard()

    # Сравнивать не с чем: счёт остаётся видимым как «без связки», а не теряется.
    acceptance = guard.accept(stable_pseudonymous_user_id=None, event_name=MILESTONE)

    assert acceptance.accepted is True
    assert acceptance.status == "accepted_unlinked"
    assert acceptance.dedupe_key is None


def test_accept_refuses_a_non_milestone_event_and_an_unsafe_identity() -> None:
    guard = MilestoneEmissionGuard()
    user = _pseudonymous_user()

    assert is_first_milestone_event(MILESTONE) is True
    for event_name in ("public_installer_download_clicked", "public_download_viewed", "unknown"):
        assert is_first_milestone_event(event_name) is False
        with pytest.raises(ValueError):
            guard.accept(stable_pseudonymous_user_id=user, event_name=event_name)

    # Сырой идентификатор и подделка под псевдоним не проходят проверку.
    for unsafe in ("raw-user-id-123", "graf_pseudo_user_zzzz", "user@example.com"):
        with pytest.raises(ValueError):
            guard.accept(stable_pseudonymous_user_id=unsafe, event_name=MILESTONE)


def test_the_ingest_service_delivers_a_repeated_milestone_only_once() -> None:
    payload = {
        "event_name": MILESTONE,
        "stable_pseudonymous_user_id": _pseudonymous_user(),
        "properties": milestone_attribution_properties(
            attribution_reliability="weak", campaign_known=True, bridge_present=True
        ),
    }

    first = ProductAnalyticsIngestService(Settings(product_analytics_enabled=True)).ingest(payload)

    assert first.accepted is True
    assert first.status != MILESTONE_STATUS_DUPLICATE
    assert first.event is not None
    assert first.event.event_name == MILESTONE
    assert first.provider_results != []

    # Другой экземпляр сервиса всё равно видит ту же веху: журнал живёт в
    # процессе, а не в объекте сервиса (FR-025).
    repeated = ProductAnalyticsIngestService(Settings(product_analytics_enabled=True)).ingest(
        payload
    )

    assert repeated.accepted is True
    assert repeated.status == MILESTONE_STATUS_DUPLICATE
    assert repeated.event is not None
    assert repeated.provider_results == []
    assert repeated.delivery_gap is None


@pytest.mark.parametrize(
    "properties_kwargs",
    [
        {},
        {"campaign_known": True},
        {"campaign_known": True, "account_connected": True},
        {"campaign_known": True, "account_connected": True, "fallback_recovered": True},
        {"campaign_known": False},
        {"attribution_reliability": "linked"},
        {"attribution_reliability": "weak"},
        {"attribution_reliability": "unknown"},
        {"attribution_reliability": "direct"},
        {"attribution_reliability": "campaign_linked_reliable"},
        {"bridge_present": True, "graf_attribution_id": "graf_attr_a1b2c3d4e5f60718293a4b5c6d7"},
    ],
)
def test_every_milestone_carries_exactly_one_reliability_level(properties_kwargs: dict) -> None:
    properties = milestone_attribution_properties(**properties_kwargs)

    assert "attribution_reliability" in properties
    assert properties["attribution_reliability"] in RELIABILITY_LEVELS
    assert "bridge_present" in properties
    assert isinstance(properties["bridge_present"], bool)


def test_the_reliability_level_follows_the_campaign_link() -> None:
    assert milestone_attribution_properties()["attribution_reliability"] == "unknown"
    assert (
        milestone_attribution_properties(campaign_known=False)["attribution_reliability"]
        == "unknown"
    )
    assert (
        milestone_attribution_properties(attribution_reliability="direct")[
            "attribution_reliability"
        ]
        == "unknown"
    )
    assert (
        milestone_attribution_properties(campaign_known=True, account_connected=True)[
            "attribution_reliability"
        ]
        == "linked"
    )
    assert milestone_attribution_properties(campaign_known=True)["attribution_reliability"] == "weak"
