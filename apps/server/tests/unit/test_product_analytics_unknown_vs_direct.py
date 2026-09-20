"""FR-018, FR-024: неизвестная кампания отличима от прямого захода (T051).

Прямой заход — это свойство источника визита (измерение уровня 1), а не
уверенность в связке кампании (уровень 2). Смешение этих двух вещей и есть
ошибка, которую запрещает FR-024: событие без известной кампании обязано
помечаться ``unknown`` и никогда ``direct``.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    ATTRIBUTION_SOURCE_CAMPAIGN,
    ATTRIBUTION_SOURCE_DIRECT,
    ATTRIBUTION_SOURCE_UNKNOWN,
    ATTRIBUTION_WINDOW_DAYS,
    DIRECT_REFERRER_CATEGORY,
    VisitAttribution,
    build_client_acquisition_attribute_from_visits,
    build_visit_attribution,
    classify_attribution_source,
    resolve_last_non_direct_source,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    build_anonymous_aggregate_bucket,
)
from twobrain_rec_server.product_analytics.attribution import (
    normalize_attribution_reliability,
    resolve_conversion_reliability,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    find_anonymous_aggregate_violations,
)
from twobrain_rec_server.product_analytics.milestones import milestone_attribution_properties

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
RELIABILITY_LEVELS = {"linked", "weak", "unknown"}


def test_the_direct_marker_is_a_source_and_not_a_reliability() -> None:
    assert DIRECT_REFERRER_CATEGORY == "direct"
    assert ATTRIBUTION_SOURCE_DIRECT == DIRECT_REFERRER_CATEGORY
    assert ATTRIBUTION_SOURCE_DIRECT not in RELIABILITY_LEVELS


@pytest.mark.parametrize(
    ("campaign_known", "referrer_category", "expected"),
    [
        (True, DIRECT_REFERRER_CATEGORY, ATTRIBUTION_SOURCE_CAMPAIGN),
        (True, "paid", ATTRIBUTION_SOURCE_CAMPAIGN),
        (True, None, ATTRIBUTION_SOURCE_CAMPAIGN),
        (False, DIRECT_REFERRER_CATEGORY, ATTRIBUTION_SOURCE_DIRECT),
        (False, "Direct", ATTRIBUTION_SOURCE_DIRECT),
        (False, "paid", ATTRIBUTION_SOURCE_UNKNOWN),
        (False, "referral", ATTRIBUTION_SOURCE_UNKNOWN),
        (False, "organic", ATTRIBUTION_SOURCE_UNKNOWN),
        (False, None, ATTRIBUTION_SOURCE_UNKNOWN),
        (False, "", ATTRIBUTION_SOURCE_UNKNOWN),
    ],
)
def test_classify_attribution_source(
    campaign_known: bool, referrer_category: str | None, expected: str
) -> None:
    # Известные метки кампании всегда важнее категории источника, а прямой
    # заход определяется только самим источником (FR-018).
    assert (
        classify_attribution_source(
            campaign_known=campaign_known, referrer_category=referrer_category
        )
        == expected
    )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("direct", None),
        ("DIRECT", None),
        ("direct ", None),
        ("linked", "linked"),
        ("weak", "weak"),
        ("unknown", "unknown"),
        ("campaign_linked_reliable", "linked"),
        ("campaign_linked_weak", "weak"),
        ("counted_unlinked", "unknown"),
        ("not_linkable", "unknown"),
        ("something_else", None),
        (None, None),
        (1, None),
    ],
)
def test_direct_is_never_translated_into_a_reliability_level(value, expected) -> None:
    assert normalize_attribution_reliability(value) == expected


def test_no_conversion_combination_produces_direct_as_reliability() -> None:
    levels = set()
    for campaign_known in (True, False):
        for account_connected in (True, False):
            for fallback_recovered in (True, False):
                level = resolve_conversion_reliability(
                    campaign_known=campaign_known,
                    account_connected=account_connected,
                    fallback_recovered=fallback_recovered,
                )
                assert level in RELIABILITY_LEVELS
                assert level != DIRECT_REFERRER_CATEGORY
                levels.add(level)

    assert levels == RELIABILITY_LEVELS
    # Свойства каждой вехи всегда несут ровно один из трёх уровней.
    for reliability in (None, "direct", "campaign_linked_weak", "counted_unlinked"):
        properties = milestone_attribution_properties(
            attribution_reliability=reliability, campaign_known=False, bridge_present=True
        )
        assert properties["attribution_reliability"] in RELIABILITY_LEVELS
        assert properties["attribution_reliability"] != DIRECT_REFERRER_CATEGORY
    assert (
        milestone_attribution_properties(attribution_reliability="direct")[
            "attribution_reliability"
        ]
        == "unknown"
    )


def test_a_direct_visit_is_never_counted_as_a_campaign() -> None:
    # У ``VisitAttribution`` нет поля категории источника: прямой заход — это
    # визит без меток, и правило выбирает только визиты с метками (FR-017).
    direct = VisitAttribution(
        attribution_ref="graf_visit_directa1b2c3d4e5f60718293",
        landing_path="/download",
        first_seen_at=NOW,
        expires_at=NOW + timedelta(days=ATTRIBUTION_WINDOW_DAYS),
    )
    labeled = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q3_b2c_launch_ru",
        first_seen_at=NOW,
    )
    expired = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q2_old_campaign",
        first_seen_at=NOW - timedelta(days=ATTRIBUTION_WINDOW_DAYS + 1),
    )

    assert classify_attribution_source(
        campaign_known=direct.campaign_known(), referrer_category=DIRECT_REFERRER_CATEGORY
    ) == ATTRIBUTION_SOURCE_DIRECT
    assert direct.campaign_known() is False
    assert resolve_last_non_direct_source([direct], now=NOW) is None
    assert resolve_last_non_direct_source([expired], now=NOW) is None
    assert resolve_last_non_direct_source([direct, labeled], now=NOW) is labeled
    assert resolve_last_non_direct_source([labeled, direct], now=NOW) is labeled

    attribute = build_client_acquisition_attribute_from_visits(
        account_id=uuid4(), visits=[direct], captured_at=NOW
    )
    assert attribute.attribution_rule == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert attribute.attribution_confidence == "unknown"
    assert attribute.source is None
    assert attribute.medium is None
    assert attribute.campaign is None


def test_the_level_one_dimension_and_the_level_two_confidence_stay_distinct() -> None:
    # Уровень 1: «direct» — это измерение о том, откуда пришёл визит.
    bucket = build_anonymous_aggregate_bucket(
        path="/download",
        occurred_at=NOW,
        referrer_category=DIRECT_REFERRER_CATEGORY,
    )
    assert bucket.referrer_category == DIRECT_REFERRER_CATEGORY
    assert find_anonymous_aggregate_violations(bucket.as_dict()) == ()

    # Уровень 2: у той же ситуации кампания неизвестна, и это никогда не «direct».
    confidence = milestone_attribution_properties(
        campaign_known=False, bridge_present=False
    )["attribution_reliability"]
    assert confidence == "unknown"
    assert confidence != bucket.referrer_category
