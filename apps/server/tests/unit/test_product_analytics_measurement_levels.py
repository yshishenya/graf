"""Unit contracts of the three measurement levels (T003, FR-001, FR-002, FR-006)."""

from pathlib import Path

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.provider_config import (
    MEASUREMENT_LEVEL_KEYS,
    ProductAnalyticsProviderConfig,
    build_measurement_levels,
)
from twobrain_rec_server.product_analytics.retention import retention_days_for_category


def write_recorded_approvals(directory: Path) -> Path:
    """A complete, metadata-only approval register outside the repository."""

    from twobrain_rec_server.product_analytics.approvals import (
        APPROVAL_KINDS,
        APPROVAL_STATE_VERSION,
    )

    lines = [f"approval_state_version={APPROVAL_STATE_VERSION}"]
    for kind in APPROVAL_KINDS:
        lines.append(
            f"approval kind={kind} state=recorded approved_by=release_owner "
            f"approved_at=2026-09-18 scope=measurement_scope evidence_ref=ref-{kind}"
        )
    path = directory / "launch-approvals"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


FULL_APPROVALS = {
    "product_analytics_enabled": True,
    "product_analytics_validation_mode": "live_safe",
    "product_analytics_posthog_enabled": True,
    "product_analytics_legal_approved": True,
    "product_analytics_privacy_approved": True,
    "product_analytics_security_approved": True,
    "product_analytics_qa_approved": True,
    "product_analytics_disclosure_approved": True,
    "product_analytics_dashboard_ready": True,
    "product_analytics_provider_smoke_approved": True,
    "product_analytics_rollback_approved": True,
    "product_analytics_live_provider_delivery_approved": True,
}


def test_default_configuration_measures_only_the_anonymous_aggregate() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(Settings())

    assert [level.key for level in config.measurement_levels] == list(MEASUREMENT_LEVEL_KEYS)
    assert [level.level for level in config.measurement_levels] == [1, 2, 3]
    # Level 1 keeps no identifier and no link between visits, so it carries no
    # personal data: FR-009 requires that count on every public page, including
    # visitors who gave no consent, and FR-012 needs it as the denominator of the
    # consent share. The optional levels do process personal data and stay off.
    assert [level.key for level in config.enabled_measurement_levels()] == ["anonymous_aggregate"]
    level_1 = config.measurement_level("anonymous_aggregate")
    assert level_1.enabled is True
    assert level_1.blocked_reasons == ()
    for level in config.measurement_levels:
        if level.key == "anonymous_aggregate":
            continue
        assert level.enabled is False
        assert level.blocked_reasons, "a disabled level must name the reason it is off"


def test_default_levels_are_fail_closed_on_every_flag() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(Settings())

    # Level 1 is on by default, so the flag cannot be what keeps it running: the
    # anonymous aggregate must not depend on any optional switch staying on.
    assert config.measurement_level("anonymous_aggregate").blocked_reasons == ()
    assert config.measurement_level("anonymous_aggregate").requires_consent is False
    assert config.measurement_level("attribution_profiles").blocked_reasons == ("flag_disabled",)
    level_3 = config.measurement_level("provider_analytics")
    assert "provider_disabled" in level_3.blocked_reasons
    assert "live_provider_delivery_not_allowed" in level_3.blocked_reasons
    for approval in ("legal", "privacy", "security", "disclosure"):
        assert f"{approval}_not_approved" in level_3.blocked_reasons
    assert config.campaign_launch_allowed is False


def test_level_one_has_its_own_switch_and_no_provider_delivery() -> None:
    settings = Settings(product_analytics_anonymous_aggregate_enabled=True)
    config = ProductAnalyticsProviderConfig.from_settings(settings)

    level_1 = config.measurement_level("anonymous_aggregate")
    assert level_1.enabled is True
    assert level_1.blocked_reasons == ()
    assert level_1.identifiers_allowed is False
    assert level_1.requires_consent is False
    assert level_1.provider_delivery is False
    assert level_1.storage == "graf_postgres"
    assert "no personal data" in level_1.legal_basis
    # Level 1 alone must not switch on levels 2 and 3.
    assert [level.key for level in config.enabled_measurement_levels()] == ["anonymous_aggregate"]


def test_level_two_requires_the_product_analytics_flag() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(product_analytics_enabled=True)
    )

    assert [level.key for level in config.enabled_measurement_levels()] == [
        "anonymous_aggregate",
        "attribution_profiles",
    ]
    level_2 = config.measurement_level("attribution_profiles")
    assert level_2.identifiers_allowed is True
    assert level_2.provider_delivery is False
    assert "contract" in level_2.legal_basis


def test_level_three_stays_off_while_only_configuration_flags_approve_it(
    tmp_path: Path, monkeypatch
) -> None:
    """FR-044: a technical flag cannot switch provider measurement on by itself."""

    monkeypatch.setenv(
        "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE", str(tmp_path / "no-such-approvals")
    )
    config = ProductAnalyticsProviderConfig.from_settings(Settings(**FULL_APPROVALS))

    level_3 = config.measurement_level("provider_analytics")
    assert level_3.enabled is False
    assert "approval_missing:legal" in level_3.blocked_reasons
    assert "approval_missing:check" in level_3.blocked_reasons
    assert "approval_missing:delivery" in level_3.blocked_reasons


def test_level_three_requires_consent_provider_and_every_recorded_approval(tmp_path: Path) -> None:
    approval_file = write_recorded_approvals(tmp_path)
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(**FULL_APPROVALS), environ={"GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE": str(approval_file)}
    )

    level_3 = config.measurement_level("provider_analytics")
    assert level_3.enabled is True
    assert level_3.blocked_reasons == ()
    assert level_3.identifiers_allowed is True
    assert level_3.requires_consent is True
    assert level_3.provider_delivery is True
    assert "consent" in level_3.legal_basis
    assert [level.key for level in config.enabled_measurement_levels()] == [
        "anonymous_aggregate",
        "attribution_profiles",
        "provider_analytics",
    ]


@pytest.mark.parametrize(
    "missing",
    [
        "product_analytics_legal_approved",
        "product_analytics_privacy_approved",
        "product_analytics_security_approved",
        "product_analytics_disclosure_approved",
        "product_analytics_live_provider_delivery_approved",
        "product_analytics_dashboard_ready",
        "product_analytics_provider_smoke_approved",
        "product_analytics_rollback_approved",
    ],
)
def test_one_missing_condition_keeps_level_three_disabled(missing: str) -> None:
    settings = Settings(**{**FULL_APPROVALS, missing: False})
    config = ProductAnalyticsProviderConfig.from_settings(settings)

    assert config.measurement_level("provider_analytics").enabled is False


def test_rollback_mode_keeps_level_three_disabled() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(
        Settings(**{**FULL_APPROVALS, "product_analytics_rollback_mode": "all_disabled"})
    )

    assert config.measurement_level("provider_analytics").enabled is False
    assert "live_provider_delivery_not_allowed" in (
        config.measurement_level("provider_analytics").blocked_reasons
    )


def test_level_retention_follows_the_registered_categories() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(Settings())

    assert config.measurement_level("anonymous_aggregate").retention_days == (
        retention_days_for_category("anonymous_page_aggregate")
    )
    assert config.measurement_level("attribution_profiles").retention_days == (
        retention_days_for_category("client_acquisition_attribute")
    )
    assert config.measurement_level("provider_analytics").retention_days == (
        retention_days_for_category("posthog_product_events")
    )
    assert config.measurement_level("anonymous_aggregate").retention_days == 1095
    assert config.measurement_level("attribution_profiles").retention_days == 1095
    assert config.measurement_level("provider_analytics").retention_days == 365


def test_unknown_measurement_level_returns_none() -> None:
    config = ProductAnalyticsProviderConfig.from_settings(Settings())

    assert config.measurement_level("level_4_telepathy") is None


def test_redacted_summary_describes_levels_without_secrets() -> None:
    payload = ProductAnalyticsProviderConfig.from_settings(Settings()).as_redacted_dict()

    assert [level["key"] for level in payload["measurement_levels"]] == list(MEASUREMENT_LEVEL_KEYS)
    assert [level["enabled"] for level in payload["measurement_levels"]] == [True, False, False]
    assert "project_key" not in str(payload["measurement_levels"])


def test_level_builder_is_usable_directly_with_provider_configs() -> None:
    settings = Settings()
    config = ProductAnalyticsProviderConfig.from_settings(settings)

    levels = build_measurement_levels(
        settings,
        posthog=config.posthog,
        yandex=config.yandex,
        live_provider_delivery_allowed=False,
    )

    assert tuple(level.key for level in levels) == MEASUREMENT_LEVEL_KEYS
    assert [level.key for level in levels if level.enabled] == ["anonymous_aggregate"]
