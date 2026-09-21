"""Правила стоимости результата фичи 273 (T057; FR-041, SC-007).

Проверяется код продукта, а не копия правил в тесте: расход разбирается
выгрузкой кабинета, соединяется с конверсиями по кампании и превращается в
стоимость результата функциями
:mod:`twobrain_rec_server.product_analytics.ad_cabinet_spend`. Тест держит
образец выгрузки и образец счётчиков конверсий — это разрешено, — но считает
продукт.

Отдельно сверяются определения: метрики, формулы и поля соединения объявлены в
``infra/analytics/dashboards/catalog.json``, и артефакт обязан совпадать с
кодом, иначе определение и поведение разойдутся.
"""

import json
import os
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics.ad_cabinet_spend import (
    AD_CABINET_EXPORT_COLUMNS,
    AD_CABINET_EXPORT_REQUIRED_COLUMNS,
    AMBIGUOUS_MATCH_LABEL,
    COST_JOIN_METRICS,
    COST_JOIN_RULES,
    SPEND_FRESHNESS_HOURS,
    UNDEFINED_VALUE_LABEL,
    UNMATCHED_CAMPAIGN_LABEL,
    ad_cabinet_spend_freshness_state,
    build_ad_cabinet_spend_export,
    build_cost_join_report,
    cost_join_metric,
    cost_per_result,
    read_ad_cabinet_spend_export,
    render_cost,
    spend_reconciliation_delta,
)

REPO_ROOT = Path(__file__).parents[4]
CATALOG_PATH = REPO_ROOT / "infra" / "analytics" / "dashboards" / "catalog.json"

PERIOD_START = date(2026, 9, 1)
PERIOD_END = date(2026, 9, 2)

# Образец выгрузки кабинета: две кампании за два дня и расход без кампании.
SPEND_EXPORT_SAMPLE = """date,campaign,ad_group,ad,spend_rub,impressions,clicks
2026-09-01,brand-search,grp-brand,ad-brand,6000,1000,50
2026-09-02,brand-search,grp-brand,ad-brand,6000,1000,50
2026-09-01,generic-search,grp-generic,ad-generic,15000,2000,80
2026-09-02,generic-search,grp-generic,ad-generic,15000,2000,80
2026-09-01,,grp-none,ad-none,3000,100,10
2026-09-02,,grp-none,ad-none,3000,100,10
"""

# Образец счётчиков конверсий с отчётной поверхности: активации по кампании.
CONVERSIONS_SAMPLE = {
    "brand-search": {"first_value": 6, "download_intent_clicks": 400},
    "generic-search": {"first_value": 4, "download_intent_clicks": 200},
}


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _export(text: str = SPEND_EXPORT_SAMPLE):
    return build_ad_cabinet_spend_export(text, state_path="/tmp/ad-cabinet-spend.csv")


def _report(metric_id: str = "cost_per_activation", **kwargs):
    return build_cost_join_report(
        _export(),
        kwargs.pop("conversions", CONVERSIONS_SAMPLE),
        period_start=kwargs.pop("period_start", PERIOD_START),
        period_end=kwargs.pop("period_end", PERIOD_END),
        metric_id=metric_id,
        **kwargs,
    )


def test_cost_join_metrics_are_declared_in_the_catalog_and_in_the_product() -> None:
    cost_join = _catalog()["cost_join"]
    declared = {metric["id"]: metric for metric in cost_join["metrics"]}

    for metric in COST_JOIN_METRICS:
        artifact = declared[metric.metric_id]
        assert artifact["formula"] == metric.formula
        assert artifact["responsible_metric"] == metric.responsible_metric
        assert artifact["undefined_rendered_as"] == UNDEFINED_VALUE_LABEL
        assert artifact["undefined_when"] == metric.undefined_when
        assert metric.results_field is not None

    assert set(declared) == {metric.metric_id for metric in COST_JOIN_METRICS} | {
        "spend_reconciliation_delta"
    }
    reconciliation = cost_join_metric("spend_reconciliation_delta")
    assert declared[reconciliation.metric_id]["formula"] == reconciliation.formula
    assert reconciliation.formula == "spend_in_report - spend_in_cabinet"


def test_cost_source_fields_match_the_declared_export() -> None:
    cost_source = _catalog()["cost_join"]["cost_source"]

    assert cost_source["surface"] == "ad_cabinet_export"
    assert tuple(cost_source["fields"]) == AD_CABINET_EXPORT_COLUMNS
    assert set(AD_CABINET_EXPORT_REQUIRED_COLUMNS) <= set(cost_source["fields"])

    join = _catalog()["cost_join"]["join"]
    assert {"cost_field": "campaign", "conversion_field": "utm_campaign"} in join["keys"]


def test_cost_per_activation_is_computed_per_campaign_by_the_product() -> None:
    report = _report()

    costs = {row.label: row.cost_per_result for row in report.rows}

    assert costs == {"brand-search": 2000.0, "generic-search": 7500.0}
    assert costs["brand-search"] < costs["generic-search"]
    assert report.spend_period_complete is True
    assert report.spend_loaded is True
    assert all(row.state == "measured" for row in report.rows)
    assert [row.rendered_cost for row in report.rows] == ["2 000.00", "7 500.00"]


def test_zero_results_is_not_a_zero_cost() -> None:
    report = _report(conversions={"brand-search": {"first_value": 0}})
    row = next(row for row in report.rows if row.label == "brand-search")

    assert row.cost_per_result is None
    assert row.rendered_cost == UNDEFINED_VALUE_LABEL
    assert row.state == "no_results"

    assert cost_per_result(9_000.0, 0) is None
    assert cost_per_result(0.0, 0) is None
    assert render_cost(cost_per_result(9_000.0, 0)) == UNDEFINED_VALUE_LABEL


def test_confirmed_zero_spend_with_a_result_is_a_real_zero() -> None:
    zero_spend = """date,campaign,spend_rub
2026-09-01,brand-search,0
2026-09-02,brand-search,0
"""
    report = build_cost_join_report(
        build_ad_cabinet_spend_export(zero_spend),
        {"brand-search": {"first_value": 5}},
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    row = next(row for row in report.rows if row.label == "brand-search")

    assert row.cost_per_result == 0.0
    assert row.rendered_cost != UNDEFINED_VALUE_LABEL
    assert row.state == "true_zero"
    assert cost_per_result(0.0, 5) == 0.0


@pytest.mark.parametrize(
    "kwargs",
    [
        {"spend_loaded": False},
        {"spend_period_complete": False},
    ],
)
def test_missing_or_partial_spend_has_no_cost(kwargs: dict) -> None:
    assert cost_per_result(12_000.0, 6, **kwargs) is None
    assert cost_per_result(None, 6) is None
    assert cost_per_result(12_000.0, None) is None


def test_partial_period_is_not_reported_as_a_cost() -> None:
    missing_day = """date,campaign,spend_rub
2026-09-01,brand-search,12000
"""
    report = build_cost_join_report(
        build_ad_cabinet_spend_export(missing_day),
        {"brand-search": {"first_value": 6}},
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    row = next(row for row in report.rows if row.label == "brand-search")

    assert report.spend_period_complete is False
    assert row.cost_per_result is None
    assert row.rendered_cost == UNDEFINED_VALUE_LABEL
    assert row.state == "partial_period"


def test_missing_export_is_not_read_as_a_zero_cost() -> None:
    unavailable = build_ad_cabinet_spend_export("")
    report = build_cost_join_report(
        unavailable,
        CONVERSIONS_SAMPLE,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    assert report.spend_loaded is False
    assert report.blocked_reason == "spend_not_loaded"
    assert all(row.cost_per_result is None for row in report.rows)
    assert all(row.rendered_cost == UNDEFINED_VALUE_LABEL for row in report.rows)


def test_broken_export_row_makes_the_whole_export_unusable() -> None:
    broken = """date,campaign,spend_rub
2026-09-01,brand-search,6000
2026-09-02,brand-search,not-a-number
"""
    export = build_ad_cabinet_spend_export(broken)

    assert export.usable is False
    assert "row_3_spend_rub" in export.file_errors
    report = build_cost_join_report(
        export,
        CONVERSIONS_SAMPLE,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    assert report.spend_loaded is False
    assert all(row.cost_per_result is None for row in report.rows)


def test_mixed_vat_basis_and_currency_refuse_the_cost() -> None:
    mixed = """date,campaign,spend_rub,currency,vat_basis
2026-09-01,brand-search,6000,RUB,with_vat
2026-09-02,brand-search,6000,RUB,without_vat
"""
    export = build_ad_cabinet_spend_export(mixed)

    assert export.usable is False
    assert "ad_cabinet_export_mixed_vat_basis" in export.file_errors


def test_download_intent_does_not_replace_the_result() -> None:
    intent = _report("cost_per_download_intent")
    activation = _report("cost_per_activation")

    intent_costs = {row.label: row.cost_per_result for row in intent.rows}
    activation_costs = {row.label: row.cost_per_result for row in activation.rows}

    assert intent_costs["brand-search"] == 30.0
    assert activation_costs["brand-search"] == 2000.0
    assert intent_costs["brand-search"] < activation_costs["brand-search"]
    assert "не заменяет стоимость результата" in cost_join_metric("cost_per_download_intent").note

    declared = {metric["id"]: metric for metric in _catalog()["cost_join"]["metrics"]}
    assert declared["cost_per_download_intent"]["note"] == cost_join_metric(
        "cost_per_download_intent"
    ).note
    assert declared["cost_per_activation"]["responsible_metric"] == "first_value"


def test_unknown_spend_is_not_spread_over_other_campaigns() -> None:
    report = _report()

    assert len(report.unmatched_rows) == 1
    unmatched = report.unmatched_rows[0]
    assert unmatched.label == UNMATCHED_CAMPAIGN_LABEL
    assert unmatched.spend_rub == 6000.0
    assert unmatched.cost_per_result is None
    assert unmatched.rendered_cost == UNDEFINED_VALUE_LABEL

    # Расход без кампании не растворён в сопоставленных строках: сумма строк и
    # несопоставленной строки равна расходу выгрузки.
    total = sum(row.spend_rub for row in report.rows) + unmatched.spend_rub
    assert total == 48_000.0
    assert {row.label for row in report.rows} == {"brand-search", "generic-search"}


def test_campaign_without_conversions_gets_no_backfilled_cost() -> None:
    report = _report(conversions={"brand-search": {"first_value": 6}})
    generic = next(row for row in report.rows if row.label == "generic-search")

    assert generic.spend_rub == 30_000.0
    assert generic.results == 0
    assert generic.cost_per_result is None
    assert generic.state == "no_results"
    assert "пропорционально кликам" in COST_JOIN_RULES["no_backfill_from_totals"]


def test_ambiguous_ad_label_is_named_and_not_silently_matched() -> None:
    ambiguous = """date,campaign,ad,spend_rub
2026-09-01,brand-search,ad-shared,6000
2026-09-02,generic-search,ad-shared,6000
"""
    report = build_cost_join_report(
        build_ad_cabinet_spend_export(ambiguous),
        {"brand-search": {"first_value": 6}, "generic-search": {"first_value": 4}},
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    assert report.ambiguous_labels == ("ad-shared",)
    assert AMBIGUOUS_MATCH_LABEL in COST_JOIN_RULES["ambiguous_match"]
    assert report.blocked_reason == "ambiguous_spend_excluded"
    assert len(report.ambiguous_rows) == 2
    assert all(row.label == AMBIGUOUS_MATCH_LABEL for row in report.ambiguous_rows)
    assert all(row.state == "ambiguous" for row in report.ambiguous_rows)
    # Неоднозначный расход не попадает в стоимость кампании и остаётся отдельной
    # строкой с явным состоянием, чтобы итог не выглядел подтверждённым.
    assert {row.label for row in report.rows} == {"brand-search", "generic-search"}
    assert all(row.cost_per_result is None for row in report.rows)
    assert all(row.state == "ambiguous" for row in report.rows)


def test_freshness_boundary_is_fresh_only_through_26_hours() -> None:
    loaded_at = datetime(2026, 9, 2, 12, 0, tzinfo=UTC)
    assert (
        ad_cabinet_spend_freshness_state(
            loaded_at,
            now=loaded_at + timedelta(hours=SPEND_FRESHNESS_HOURS),
        )
        == "fresh"
    )
    assert (
        ad_cabinet_spend_freshness_state(
            loaded_at,
            now=loaded_at + timedelta(hours=SPEND_FRESHNESS_HOURS, seconds=1),
        )
        == "stale"
    )
    assert ad_cabinet_spend_freshness_state(None, now=loaded_at) == "unchecked"


def test_stale_export_blocks_cost_and_reports_freshness(tmp_path: Path) -> None:
    path = tmp_path / "ad-cabinet-spend.csv"
    path.write_text(SPEND_EXPORT_SAMPLE, encoding="utf-8")
    loaded_at = datetime(2026, 9, 1, 0, 0, tzinfo=UTC)
    os.utime(path, (loaded_at.timestamp(), loaded_at.timestamp()))

    export = read_ad_cabinet_spend_export(
        {"TWOBRAIN_PRODUCT_ANALYTICS_AD_CABINET_EXPORT_FILE": str(path)},
        now=loaded_at + timedelta(hours=SPEND_FRESHNESS_HOURS, seconds=1),
    )
    report = build_cost_join_report(
        export,
        CONVERSIONS_SAMPLE,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )

    assert export.freshness_state == "stale"
    assert report.spend_freshness_state == "stale"
    assert report.spend_loaded is False
    assert report.blocked_reason == "spend_stale"
    assert all(row.cost_per_result is None for row in report.rows)


def test_zero_results_rule_wins_over_zero_spend_rule() -> None:
    assert cost_per_result(0.0, 0) is None
    assert "главнее" in COST_JOIN_RULES["zero_results"]
    assert "не определена независимо от расхода" in COST_JOIN_RULES["zero_spend"]


def test_personal_data_in_the_export_refuses_the_cost() -> None:
    leaky = """date,campaign,ad,spend_rub
2026-09-01,brand-search,ad-brand,6000
2026-09-02,brand-search,client@example.com,6000
"""
    export = build_ad_cabinet_spend_export(leaky)

    # Выгрузку кладет оператор, и отчет не должен становиться способом протащить
    # контакты в аналитику: такая выгрузка не используется целиком.
    assert export.usable is False
    assert any(
        error.startswith("ad_cabinet_export_forbidden_fields:") for error in export.file_errors
    )
    report = build_cost_join_report(
        export,
        CONVERSIONS_SAMPLE,
        period_start=PERIOD_START,
        period_end=PERIOD_END,
    )
    assert report.spend_loaded is False
    assert all(row.cost_per_result is None for row in report.rows)


def test_export_without_the_required_columns_is_not_a_spend_export() -> None:
    export = build_ad_cabinet_spend_export("date,campaign\n2026-09-01,brand-search\n")

    assert export.usable is False
    assert "ad_cabinet_export_columns_missing:spend_rub" in export.file_errors


def test_reconciliation_delta_needs_both_sides() -> None:
    assert spend_reconciliation_delta(spend_in_report=12_000.0, spend_in_cabinet=11_500.0) == 500.0
    assert spend_reconciliation_delta(spend_in_report=None, spend_in_cabinet=11_500.0) is None
    assert spend_reconciliation_delta(spend_in_report=12_000.0, spend_in_cabinet=None) is None
