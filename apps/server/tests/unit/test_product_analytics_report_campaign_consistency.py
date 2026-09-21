"""Согласованность разбивки по кампаниям между Метрикой и продуктом (T061; SC-008).

Набор ``infra/analytics/dashboards/consistency/sample-campaign-breakdown.json``
описывает одни и те же вымышленные визиты дважды: как строки отчёта Метрики и как
записи атрибуции продуктовой аналитики. Проверка применяет настоящее правило
атрибуции из кода продукта, настоящее правило окна 90 дней и настоящий очиститель
меток, после чего сравнивает корзины кампаний.

Проверяются и положительный случай (разбивки совпадают), и отрицательные: подмена
кампании, переименование прямого захода в неизвестную кампанию, отсутствие окна,
отсутствие очистителя меток и раскрытие слишком маленькой корзины.
"""

import json
from collections import Counter
from datetime import datetime
from pathlib import Path
from uuid import NAMESPACE_DNS, uuid5

import pytest

from twobrain_rec_server.product_analytics.acquisition import (
    ATTRIBUTION_RULE_LAST_NON_DIRECT_90D,
    ATTRIBUTION_WINDOW_DAYS,
    build_client_acquisition_attribute,
    is_within_attribution_window,
)
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    MINIMUM_AGGREGATE_BUCKET_SIZE,
    is_disclosed_bucket,
    sanitize_anonymous_aggregate_label,
)

REPO_ROOT = Path(__file__).parents[4]
DASHBOARDS_ROOT = REPO_ROOT / "infra" / "analytics" / "dashboards"
CATALOG_PATH = DASHBOARDS_ROOT / "catalog.json"
SAMPLE_PATH = DASHBOARDS_ROOT / "consistency" / "sample-campaign-breakdown.json"

DIRECT_BUCKET = "прямой заход"
UNKNOWN_BUCKET = "кампания неизвестна"
LANDING_PATH = "/"


def _sample() -> dict:
    return json.loads(SAMPLE_PATH.read_text(encoding="utf-8"))


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _bucket(label: str | None, *, traffic_kind: str | None) -> str:
    """Корзина кампании по единому правилу для обеих поверхностей."""
    if label:
        return label
    if traffic_kind == "direct":
        return DIRECT_BUCKET
    return UNKNOWN_BUCKET


def _split_disclosed(buckets: Counter[str]) -> dict:
    disclosed = {name: visits for name, visits in buckets.items() if is_disclosed_bucket(visits)}
    suppressed = {
        name: visits for name, visits in buckets.items() if not is_disclosed_bucket(visits)
    }
    return {
        "disclosed": disclosed,
        "suppressed_buckets": len(suppressed),
        "suppressed_visits": sum(suppressed.values()),
    }


def metrica_breakdown(
    sample: dict,
    *,
    apply_period: bool = True,
    apply_normalizer: bool = True,
    rename_direct: bool = False,
) -> dict:
    """Разбивка по кампаниям так, как её даёт отчёт Метрики."""
    surface = sample["surfaces"]["yandex_metrica"]
    period = sample["period"]
    rows = list(surface["rows"])
    if not apply_period:
        rows += list(surface["rows_outside_period"])

    buckets: Counter[str] = Counter()
    for row in rows:
        if apply_period and not (period["from"] <= row["date"] <= period["to"]):
            continue
        raw_campaign = row["campaign_raw"]
        if rename_direct and row["traffic_source"] == "direct":
            raw_campaign = "unknown"
        label = sanitize_anonymous_aggregate_label(raw_campaign) if apply_normalizer else raw_campaign
        traffic_kind = None if rename_direct else row["traffic_source"]
        buckets[_bucket(label, traffic_kind=traffic_kind)] += row["visits"]

    return _split_disclosed(buckets)


def product_analytics_breakdown(
    sample: dict,
    *,
    apply_window: bool = True,
    reassign_visit: str | None = None,
    disclose_small_buckets: bool = False,
) -> dict:
    """Разбивка по кампаниям так, как её даёт продуктовая аналитика."""
    surface = sample["surfaces"]["product_analytics"]
    checked_at = datetime.fromisoformat(sample["checked_at"])
    rows = list(surface["rows"])
    if not apply_window:
        rows += list(surface["rows_outside_window"])

    buckets: Counter[str] = Counter()
    for row in rows:
        seen_at = datetime.fromisoformat(row["first_seen_at"])
        if apply_window and not is_within_attribution_window(
            seen_at, now=checked_at, window_days=ATTRIBUTION_WINDOW_DAYS
        ):
            continue
        campaign = row["campaign_raw"]
        if reassign_visit is not None and row["visit_ref"] == reassign_visit:
            campaign = "brand-search"
        attribute = build_client_acquisition_attribute(
            account_id=uuid5(NAMESPACE_DNS, row["visit_ref"]),
            landing_path=LANDING_PATH,
            source=row["source"],
            medium=row["medium"],
            campaign=campaign,
            captured_at=seen_at,
            linked_automatically=row["linked_automatically"],
        )
        buckets[
            _bucket(attribute.campaign, traffic_kind=row["referrer_category"])
        ] += 1

    if disclose_small_buckets:
        disclosed = {name: visits for name, visits in buckets.items() if visits > 0}
        return {"disclosed": disclosed, "suppressed_buckets": 0, "suppressed_visits": 0}
    return _split_disclosed(buckets)


def differences(metrica: dict, product_analytics: dict) -> list[str]:
    """Расхождения разбивок. Пустой список означает согласованность."""
    found: list[str] = []
    for name in sorted(set(metrica["disclosed"]) | set(product_analytics["disclosed"])):
        left = metrica["disclosed"].get(name)
        right = product_analytics["disclosed"].get(name)
        if left != right:
            found.append(f"кампания {name}: Метрика {left}, продукт {right}")
    if metrica["suppressed_buckets"] != product_analytics["suppressed_buckets"]:
        found.append(
            "число скрытых корзин: "
            f"Метрика {metrica['suppressed_buckets']}, продукт {product_analytics['suppressed_buckets']}"
        )
    if metrica["suppressed_visits"] != product_analytics["suppressed_visits"]:
        found.append("визиты в скрытых корзинах не совпадают")
    return found


def test_prepared_sample_has_matching_campaign_breakdowns() -> None:
    sample = _sample()
    expected = sample["expected"]

    metrica = metrica_breakdown(sample)
    product_analytics = product_analytics_breakdown(sample)

    assert differences(metrica, product_analytics) == []
    assert metrica == product_analytics
    assert metrica["disclosed"] == expected["disclosed_buckets"]
    assert metrica["suppressed_buckets"] == expected["suppressed_buckets"]
    assert metrica["suppressed_visits"] == expected["suppressed_visits"]
    assert sum(metrica["disclosed"].values()) == expected["disclosed_visits"]
    assert (
        sum(metrica["disclosed"].values()) + metrica["suppressed_visits"]
        == expected["total_in_scope_visits"]
    )


def test_sample_uses_one_attribution_rule_on_both_surfaces() -> None:
    sample = _sample()
    catalog = _catalog()

    assert sample["single_rule"]["rule"] == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert sample["single_rule"]["rule"] == catalog["attribution_rule"]["rule"]
    assert sample["window_days"] == ATTRIBUTION_WINDOW_DAYS == catalog["attribution_rule"]["window_days"]
    assert sample["minimum_bucket_size"] == MINIMUM_AGGREGATE_BUCKET_SIZE
    assert sample["single_rule"]["unknown_is_not_direct"] is True

    check = catalog["consistency_check"]
    assert check["single_rule"]["rule"] == ATTRIBUTION_RULE_LAST_NON_DIRECT_90D
    assert Path(DASHBOARDS_ROOT / check["sample"]) == SAMPLE_PATH


def test_visit_outside_the_window_is_excluded_on_both_surfaces() -> None:
    sample = _sample()
    expected = sample["expected"]

    metrica_inside = metrica_breakdown(sample)
    product_inside = product_analytics_breakdown(sample)

    metrica_outside = metrica_breakdown(sample, apply_period=False)
    product_outside = product_analytics_breakdown(sample, apply_window=False)

    assert metrica_outside["disclosed"]["brand-search"] == (
        metrica_inside["disclosed"]["brand-search"] + 1
    )
    assert product_outside["disclosed"]["brand-search"] == (
        product_inside["disclosed"]["brand-search"] + 1
    )
    assert differences(metrica_outside, product_outside) == []
    assert expected["excluded_out_of_period_or_window"] == 1


def test_unknown_campaign_is_not_the_same_as_a_direct_visit() -> None:
    sample = _sample()

    metrica = metrica_breakdown(sample)
    product_analytics = product_analytics_breakdown(sample)

    assert DIRECT_BUCKET in metrica["disclosed"]
    assert UNKNOWN_BUCKET in metrica["disclosed"]
    assert DIRECT_BUCKET != UNKNOWN_BUCKET
    assert metrica["disclosed"][DIRECT_BUCKET] == product_analytics["disclosed"][DIRECT_BUCKET] == 3

    direct_row = next(
        row
        for row in sample["surfaces"]["product_analytics"]["rows"]
        if row["referrer_category"] == "direct"
    )
    unknown_row = next(
        row
        for row in sample["surfaces"]["product_analytics"]["rows"]
        if row["referrer_category"] == "organic" and row["campaign_raw"] is None
    )
    direct_attribute = build_client_acquisition_attribute(
        account_id=uuid5(NAMESPACE_DNS, direct_row["visit_ref"]),
        landing_path=LANDING_PATH,
        captured_at=datetime.fromisoformat(direct_row["first_seen_at"]),
    )
    unknown_attribute = build_client_acquisition_attribute(
        account_id=uuid5(NAMESPACE_DNS, unknown_row["visit_ref"]),
        landing_path=LANDING_PATH,
        captured_at=datetime.fromisoformat(unknown_row["first_seen_at"]),
    )

    # Обе записи не несут кампанию, но корзины у них разные: прямой заход не
    # выдаётся за неизвестную кампанию и наоборот (FR-024).
    assert direct_attribute.attribution_confidence == "unknown"
    assert unknown_attribute.attribution_confidence == "unknown"
    assert _bucket(None, traffic_kind="direct") == DIRECT_BUCKET
    assert _bucket(None, traffic_kind="organic") == UNKNOWN_BUCKET


def test_label_that_looks_unsafe_is_dropped_on_both_surfaces() -> None:
    sample = _sample()

    unsafe_visits = sum(
        row["visits"]
        for row in sample["surfaces"]["yandex_metrica"]["rows"]
        if row["campaign_raw"] and sanitize_anonymous_aggregate_label(row["campaign_raw"]) is None
    )
    assert unsafe_visits == 1

    metrica = metrica_breakdown(sample)
    product_analytics = product_analytics_breakdown(sample)

    assert "graf promo" not in metrica["disclosed"]
    assert "graf promo" not in product_analytics["disclosed"]
    assert metrica["disclosed"][UNKNOWN_BUCKET] == product_analytics["disclosed"][UNKNOWN_BUCKET] == 4


def test_both_surfaces_hide_the_same_small_buckets() -> None:
    sample = _sample()

    metrica = metrica_breakdown(sample)
    product_analytics = product_analytics_breakdown(sample)

    assert metrica["suppressed_buckets"] == product_analytics["suppressed_buckets"] == 1
    assert metrica["suppressed_visits"] == product_analytics["suppressed_visits"] == 2
    assert "retargeting" not in metrica["disclosed"]
    assert is_disclosed_bucket(2) is False


@pytest.mark.parametrize(
    ("case_id", "metrica_kwargs", "product_kwargs"),
    [
        ("N1", {}, {"reassign_visit": "v13"}),
        ("N2", {"rename_direct": True}, {}),
        ("N3", {}, {"apply_window": False}),
        ("N4", {"apply_normalizer": False}, {}),
        ("N5", {}, {"disclose_small_buckets": True}),
    ],
)
def test_divergence_cases_are_detected(
    case_id: str,
    metrica_kwargs: dict,
    product_kwargs: dict,
) -> None:
    sample = _sample()
    declared = {case["case_id"] for case in sample["negative_cases"]}
    assert case_id in declared

    metrica = metrica_breakdown(sample, **metrica_kwargs)
    product_analytics = product_analytics_breakdown(sample, **product_kwargs)

    found = differences(metrica, product_analytics)
    assert found, f"{case_id}: расхождение не обнаружено"


def test_mismatch_rule_blocks_campaign_conclusions() -> None:
    catalog = _catalog()
    check = catalog["consistency_check"]

    assert "не публикуются" in check["on_mismatch"]
    assert len(check["mismatch_causes"]) >= 5
    assert check["live_tolerance"]["relative_difference_max"] == 0.05
    assert "точное совпадение" in check["expected_on_sample"]
