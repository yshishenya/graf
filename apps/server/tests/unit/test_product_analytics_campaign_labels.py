"""Unit contracts of campaign label normalisation on the public layer (T009)."""

import pytest

from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    MAX_ANONYMOUS_AGGREGATE_LABEL_LENGTH,
    sanitize_anonymous_aggregate_label,
)
from twobrain_rec_server.public.analytics import normalize_public_campaign_attribution

UNSAFE_LABELS = (
    "IvanPetrov",
    "Ivan.Petrov",
    "ivan.petrov",
    "customer@example.com",
    "+7 999 111 22 33",
    "8 999 111 22 33",
    "1234567890",
    "https://private.example/signed?token=abc",
    "access_token",
    "signed_url",
    "Иван",
    "campaign with spaces",
    "campaign/with/slash",
    "campaign\\with\\backslash",
    "campaign?query=1",
    "campaign#anchor",
    "a" * (MAX_ANONYMOUS_AGGREGATE_LABEL_LENGTH + 1),
)

SAFE_LABELS = (
    "2026q3_b2c_launch_ru",
    "hero_a",
    "meeting_recorder",
    "campaign-42",
    "brand:launch.2026",
    "a" * MAX_ANONYMOUS_AGGREGATE_LABEL_LENGTH,
)


def _attribution(**values) -> dict:
    return normalize_public_campaign_attribution(values, landing_path="/")


@pytest.mark.parametrize("value", UNSAFE_LABELS)
def test_unsafe_labels_are_dropped_with_a_visible_status(value: str) -> None:
    attribution = _attribution(utm_campaign=value)

    assert attribution["utm_campaign"] is None
    assert attribution["normalization_status"] == "unsafe_dropped"


@pytest.mark.parametrize("value", SAFE_LABELS)
def test_safe_labels_are_kept_without_rewriting(value: str) -> None:
    attribution = _attribution(utm_campaign=value)

    assert attribution["utm_campaign"] == value
    assert attribution["normalization_status"] == "clean"


def test_source_and_medium_are_lowercased_before_the_safety_check() -> None:
    attribution = _attribution(utm_source="Yandex_Direct", utm_medium="CPC")

    assert attribution["utm_source"] == "yandex_direct"
    assert attribution["utm_medium"] == "cpc"
    assert attribution["normalization_status"] == "normalized"


def test_normalization_status_is_missing_without_campaign_labels() -> None:
    attribution = _attribution()

    assert attribution["normalization_status"] == "missing"
    assert attribution["referrer_category"] == "direct"


def test_public_layer_and_aggregate_share_one_label_decider() -> None:
    for value in (*UNSAFE_LABELS, *SAFE_LABELS):
        attribution = _attribution(utm_campaign=value)
        shared = sanitize_anonymous_aggregate_label(value)

        assert attribution["utm_campaign"] == shared


def test_dropped_labels_do_not_leave_the_dropped_value_in_the_payload() -> None:
    attribution = _attribution(
        utm_campaign="IvanPetrov", utm_content="customer@example.com", utm_term="79991112233"
    )

    assert "IvanPetrov" not in str(attribution)
    assert "customer@example.com" not in str(attribution)
    assert "79991112233" not in str(attribution)
    assert attribution["normalization_status"] == "unsafe_dropped"
