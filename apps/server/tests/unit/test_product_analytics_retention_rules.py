"""Unit contracts of the retention terms of feature 273 (T007, FR-050)."""

from dataclasses import replace

import pytest

from twobrain_rec_server.product_analytics.retention import (
    GRAF_CONTROLLED_STORAGES,
    RETENTION_ENFORCEMENTS,
    RETENTION_STORAGES,
    AnalyticsRetentionConfigurationError,
    AnalyticsRetentionRule,
    retention_days_for_category,
    retention_rule,
    retention_rules,
    validate_retention_rules,
)

NEW_CATEGORIES = (
    "posthog_product_events",
    "anonymous_page_aggregate",
    "client_acquisition_attribute",
    "visit_attribution",
)


def test_owner_policy_keeps_history_without_an_age_deadline() -> None:
    for category in NEW_CATEGORIES:
        rule = retention_rule(category)
        assert rule.enforced_retention_days() is None
        assert rule.retention_mode == "until_decision"
        assert rule.enforcement == "decision_required"
        assert rule.storage in GRAF_CONTROLLED_STORAGES


def test_unknown_category_is_a_configuration_error_not_keep_forever() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        retention_days_for_category("category_that_was_never_registered")
    with pytest.raises(AnalyticsRetentionConfigurationError):
        retention_days_for_category("")


def test_provider_rule_without_a_term_is_refused() -> None:
    for invalid in (None, 0, -1):
        with pytest.raises(AnalyticsRetentionConfigurationError):
            replace(retention_rule("yandex_webvisor"), minimum_retention_days=invalid)


def test_rule_with_a_maximum_below_its_minimum_is_refused() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        replace(retention_rule("yandex_webvisor"), maximum_retention_days=30)


def test_unknown_storage_or_enforcement_is_refused() -> None:
    for overrides in ({"storage": "some_other_cloud"}, {"enforcement": "we_will_remember"}):
        with pytest.raises(AnalyticsRetentionConfigurationError):
            replace(retention_rule("anonymous_page_aggregate"), **overrides)


def test_graf_controlled_storage_cannot_fall_back_to_manual_age_policy() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        replace(retention_rule("anonymous_page_aggregate"), enforcement="manual_process")


def test_registered_categories_all_declare_storage_and_enforcement() -> None:
    validate_retention_rules()

    rules = retention_rules()
    assert len(rules) == len({rule.category for rule in rules})
    for rule in rules:
        assert rule.storage in RETENTION_STORAGES
        assert rule.enforcement in RETENTION_ENFORCEMENTS
        assert rule.retention_mode in {"until_decision", "provider_controlled"}
        assert "storage" in rule.as_dict()
        assert "enforcement" in rule.as_dict()


@pytest.mark.parametrize("mode", ["", "unknown", "forever"])
def test_missing_or_unknown_mode_is_refused(mode: str) -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            "synthetic",
            None,
            None,
            "graf_controlled",
            "separate decision",
            "controlled storage only",
            enforcement="decision_required",
            retention_mode=mode,
        )


@pytest.mark.parametrize(
    "days,enforcement", [(365, "decision_required"), (None, "scheduled_purge")]
)
def test_until_decision_cannot_hide_age_enforcement(days, enforcement) -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            "synthetic",
            days,
            days,
            "graf_controlled",
            "separate decision",
            "controlled storage only",
            enforcement=enforcement,
            retention_mode="until_decision",
        )
