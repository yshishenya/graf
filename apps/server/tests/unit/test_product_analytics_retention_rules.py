"""Unit contracts of the retention terms of feature 273 (T007, FR-050)."""

import pytest

from twobrain_rec_server.product_analytics.retention import (
    AUTOMATIC_ENFORCEMENTS,
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

NEW_CATEGORIES = {
    "posthog_product_events": 365,
    "anonymous_page_aggregate": 1095,
    "client_acquisition_attribute": 1095,
    "visit_attribution": 90,
}


def test_new_categories_have_the_required_terms() -> None:
    for category, days in NEW_CATEGORIES.items():
        rule = retention_rule(category)

        assert rule.minimum_retention_days == days
        assert rule.enforced_retention_days() == days


@pytest.mark.parametrize("category", sorted(NEW_CATEGORIES))
def test_new_categories_name_a_storage_and_an_enforcement(category: str) -> None:
    rule = retention_rule(category)

    assert rule.storage in RETENTION_STORAGES
    assert rule.enforcement in RETENTION_ENFORCEMENTS
    assert rule.storage in GRAF_CONTROLLED_STORAGES
    assert rule.enforcement in AUTOMATIC_ENFORCEMENTS


def test_unknown_category_is_a_configuration_error_not_keep_forever() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        retention_days_for_category("category_that_was_never_registered")
    with pytest.raises(AnalyticsRetentionConfigurationError):
        retention_days_for_category("")


def test_rule_without_a_term_is_refused() -> None:
    for invalid in (None, 0, -1):
        with pytest.raises(AnalyticsRetentionConfigurationError):
            AnalyticsRetentionRule(
                category="synthetic_without_term",
                minimum_retention_days=invalid,
                maximum_retention_days=None,
                delete_on_user_request="not_stored",
                provider_delete_method="none",
                deletion_truth="not_stored",
            )


def test_rule_with_a_maximum_below_its_minimum_is_refused() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            category="synthetic_inverted",
            minimum_retention_days=90,
            maximum_retention_days=30,
            delete_on_user_request="not_stored",
            provider_delete_method="none",
            deletion_truth="not_stored",
        )


def test_unknown_storage_or_enforcement_is_refused() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            category="synthetic_storage",
            minimum_retention_days=90,
            maximum_retention_days=90,
            delete_on_user_request="not_stored",
            provider_delete_method="none",
            deletion_truth="not_stored",
            storage="some_other_cloud",
        )
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            category="synthetic_enforcement",
            minimum_retention_days=90,
            maximum_retention_days=90,
            delete_on_user_request="not_stored",
            provider_delete_method="none",
            deletion_truth="not_stored",
            enforcement="we_will_remember",
        )


def test_graf_controlled_storage_requires_automatic_enforcement() -> None:
    with pytest.raises(AnalyticsRetentionConfigurationError):
        AnalyticsRetentionRule(
            category="synthetic_manual",
            minimum_retention_days=90,
            maximum_retention_days=90,
            delete_on_user_request="not_stored",
            provider_delete_method="none",
            deletion_truth="not_stored",
            storage="graf_postgres",
            enforcement="manual_process",
        )


def test_registered_categories_all_declare_storage_and_enforcement() -> None:
    validate_retention_rules()

    rules = retention_rules()
    assert len(rules) == len({rule.category for rule in rules})
    for rule in rules:
        assert rule.storage in RETENTION_STORAGES
        assert rule.enforcement in RETENTION_ENFORCEMENTS
        assert rule.minimum_retention_days >= 1
        assert "storage" in rule.as_dict()
        assert "enforcement" in rule.as_dict()
