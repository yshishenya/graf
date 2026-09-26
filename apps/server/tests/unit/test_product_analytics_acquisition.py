"""Unit contracts of the level 2 acquisition module (T002)."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest

from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_CONFIDENCE_LEVELS,
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    ATTRIBUTION_WINDOW_DAYS,
    build_client_acquisition_attribute,
    build_visit_attribution,
    build_visit_attribution_from_attribution,
    is_within_attribution_window,
    resolve_attribution_confidence,
    resolve_last_non_direct_source,
)
from twobrain_rec_server.product_analytics.forbidden_fields import (
    CLIENT_ACQUISITION_ALLOWED_FIELDS,
    VISIT_ATTRIBUTION_ALLOWED_FIELDS,
    find_client_acquisition_violations,
    find_visit_attribution_violations,
)

NOW = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)


def test_attribution_window_is_capped_at_ninety_days() -> None:
    assert ATTRIBUTION_WINDOW_DAYS == 90
    attribution = build_visit_attribution(
        landing_path="/download", source="yandex_direct", first_seen_at=NOW
    )

    assert attribution.expires_at - attribution.first_seen_at == timedelta(days=90)
    for invalid in (0, -1, 91, 365):
        with pytest.raises(ValueError):
            build_visit_attribution(landing_path="/", ttl_days=invalid)


def test_visit_attribution_expires_and_is_then_unusable() -> None:
    attribution = build_visit_attribution(landing_path="/", first_seen_at=NOW)

    assert attribution.is_expired(now=NOW + timedelta(days=89)) is False
    assert attribution.is_expired(now=NOW + timedelta(days=90)) is True
    assert is_within_attribution_window(NOW, now=NOW + timedelta(days=89)) is True
    assert is_within_attribution_window(NOW, now=NOW + timedelta(days=90)) is False
    assert is_within_attribution_window(NOW, now=NOW + timedelta(days=91)) is False
    assert is_within_attribution_window(NOW + timedelta(minutes=1), now=NOW) is False


def test_last_non_direct_source_selects_the_newest_live_visit() -> None:
    older = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        campaign="older",
        first_seen_at=NOW - timedelta(days=10),
    )
    newer = build_visit_attribution(
        landing_path="/download",
        source="google_ads",
        campaign="newer",
        first_seen_at=NOW - timedelta(days=2),
    )
    direct_like = build_visit_attribution(landing_path="/download", first_seen_at=NOW - timedelta(days=1))

    selected = resolve_last_non_direct_source([older, direct_like, newer], now=NOW)

    assert selected is newer


def test_yclid_only_visit_is_a_known_last_non_direct_source() -> None:
    visit = build_visit_attribution(
        landing_path="/download",
        yclid="1234567890abc",
        first_seen_at=NOW - timedelta(days=2),
    )

    assert visit.campaign_known() is True
    assert resolve_last_non_direct_source([visit], now=NOW) is visit


def test_last_non_direct_source_ignores_expired_and_future_visits() -> None:
    expired = build_visit_attribution(
        landing_path="/download",
        source="old",
        campaign="expired",
        first_seen_at=NOW - timedelta(days=90),
    )
    future = type(expired)(
        attribution_ref="graf_visit_abcdef0123456789",
        landing_path="/download",
        first_seen_at=NOW + timedelta(minutes=1),
        expires_at=NOW + timedelta(days=91),
        source="future",
        campaign="future",
    )

    assert resolve_last_non_direct_source([expired, future], now=NOW) is None


def test_visit_attribution_reference_is_opaque_and_unguessable() -> None:
    first = build_visit_attribution(landing_path="/", first_seen_at=NOW)
    second = build_visit_attribution(landing_path="/", first_seen_at=NOW)

    assert first.attribution_ref.startswith("graf_visit_")
    assert first.attribution_ref != second.attribution_ref


def test_visit_attribution_has_only_allowlisted_fields() -> None:
    attribution = build_visit_attribution(
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q3_b2c_launch_ru",
        yclid="1234567890abc",
        first_seen_at=NOW,
    )

    assert set(attribution.as_dict()) == set(VISIT_ATTRIBUTION_ALLOWED_FIELDS)
    assert find_visit_attribution_violations(attribution.as_dict()) == ()


def test_visit_attribution_drops_unsafe_labels_and_keeps_the_window_shape() -> None:
    attribution = build_visit_attribution_from_attribution(
        {
            "utm_source": "Yandex_Direct",
            "utm_medium": "CPC",
            "utm_campaign": "customer@example.com",
            "utm_content": "https://private.example/signed?token=abc",
            "utm_term": "+7 999 111 22 33",
        },
        landing_path="/download",
        first_seen_at=NOW,
    )

    assert attribution.source == "yandex_direct"
    assert attribution.medium == "cpc"
    assert attribution.campaign is None
    assert attribution.content is None
    assert attribution.term is None
    assert attribution.campaign_known() is True


def test_visit_attribution_rejects_private_pages() -> None:
    for path in ("/meetings", "/cabinet", "/api/v1/health/live"):
        with pytest.raises(ValueError):
            build_visit_attribution(landing_path=path)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1234567890abc", "1234567890abc"),
        ("yclid_1234567890", "yclid_1234567890"),
        ("short", None),
        ("", None),
        (None, None),
        (1234567890, None),
        ("with space 1234567890", None),
        ("x" * 121, None),
    ],
)
def test_yclid_is_kept_only_when_it_has_a_sane_shape(value, expected) -> None:
    attribution = build_visit_attribution(landing_path="/", yclid=value, first_seen_at=NOW)

    assert attribution.yclid == expected


def test_client_attribute_uses_a_pseudonym_and_never_the_raw_account_id() -> None:
    account_id = uuid4()
    attribute = build_client_acquisition_attribute(
        account_id=account_id,
        landing_path="/download",
        source="yandex_direct",
        medium="cpc",
        campaign="2026q3_b2c_launch_ru",
        captured_at=NOW,
        linked_automatically=True,
    )

    analytics_view = attribute.as_analytics_dict()
    assert set(analytics_view) == set(CLIENT_ACQUISITION_ALLOWED_FIELDS)
    assert find_client_acquisition_violations(analytics_view) == ()
    assert attribute.account_id == account_id
    assert analytics_view["account_pseudonym"].startswith("graf_pseudo_")
    assert str(account_id) not in str(analytics_view)
    assert analytics_view["attribution_rule"] == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert analytics_view["attribution_confidence"] == "linked"


def test_client_attribute_analytics_view_never_carries_a_raw_yclid() -> None:
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/download",
        source="yandex_direct",
        yclid="1234567890abc",
        captured_at=NOW,
    )

    analytics_view = attribute.as_analytics_dict()
    assert analytics_view["yclid_present"] is True
    assert "yclid" not in analytics_view
    assert "1234567890abc" not in str(analytics_view)
    # The stored row keeps the click identifier, because level 2 is entitled to it.
    assert attribute.as_storage_dict()["yclid"] == "1234567890abc"


def test_client_attribute_drops_unsafe_labels() -> None:
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(),
        landing_path="/",
        source="Email",
        campaign="customer@example.com",
        content="IvanPetrov",
        captured_at=NOW,
    )

    assert attribute.source == "email"
    assert attribute.campaign is None
    assert attribute.content is None
    # A source without a campaign is a weak link, never a confident one.
    assert attribute.attribution_confidence == "weak"


@pytest.mark.parametrize(
    ("campaign_known", "linked", "fallback", "expected"),
    [
        (True, True, False, "linked"),
        (True, False, False, "weak"),
        (True, True, True, "weak"),
        (True, False, True, "weak"),
        (False, True, False, "unknown"),
        (False, False, False, "unknown"),
    ],
)
def test_attribution_confidence_levels(
    campaign_known: bool, linked: bool, fallback: bool, expected: str
) -> None:
    assert (
        resolve_attribution_confidence(
            campaign_known=campaign_known,
            linked_automatically=linked,
            fallback_recovered=fallback,
        )
        == expected
    )
    assert expected in ATTRIBUTION_CONFIDENCE_LEVELS


def test_unknown_campaign_is_never_reported_as_direct() -> None:
    attribute = build_client_acquisition_attribute(
        account_id=uuid4(), landing_path="/", captured_at=NOW
    )

    assert attribute.attribution_confidence == "unknown"
    assert attribute.source is None
    assert attribute.medium is None


def test_only_the_last_non_direct_rule_is_accepted() -> None:
    with pytest.raises(ValueError):
        build_client_acquisition_attribute(
            account_id=uuid4(),
            landing_path="/",
            attribution_rule="first_touch",
            captured_at=NOW,
        )
    with pytest.raises(ValueError):
        build_client_acquisition_attribute(
            account_id=uuid4(),
            landing_path="/",
            attribution_confidence="certain",
            captured_at=NOW,
        )


def test_client_attribute_rejects_private_pages() -> None:
    for path in ("/meetings", "/cabinet"):
        with pytest.raises(ValueError):
            build_client_acquisition_attribute(account_id=uuid4(), landing_path=path, captured_at=NOW)


def test_level_two_may_use_identity_pseudonyms_unlike_level_one() -> None:
    attribute = build_client_acquisition_attribute(
        account_id=UUID(int=7), landing_path="/", captured_at=NOW
    )
    again = build_client_acquisition_attribute(
        account_id=UUID(int=7), landing_path="/", captured_at=NOW
    )

    # Level 2 is built on the pseudonym of identity.py: it is stable for the
    # same account and it is not the raw identifier itself.
    assert attribute.account_pseudonym == again.account_pseudonym
    assert attribute.account_pseudonym.startswith("graf_pseudo_account_")
    assert attribute.account_pseudonym != str(attribute.account_id)
    assert not attribute.account_pseudonym.endswith(str(UUID(int=7)))
