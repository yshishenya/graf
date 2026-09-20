"""Unit contracts of the legal-basis lifecycle (T081, FR-048).

When the legal basis of a measurement level falls away, processing stops and the
affected data is deleted or anonymised within the term the retention rules
already set. These tests hold the two properties that make that binding: a lost
basis really refuses processing, and every erasure deadline is derived from
:mod:`retention` instead of a number written down again.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
    CATEGORY_DISPOSITIONS,
    EXECUTION_LOCAL,
    EXECUTION_PROVIDER_REQUEST,
    LEGAL_BASIS_CONFIRMED,
    LEGAL_BASIS_NOT_CONFIRMED,
    LEGAL_BASIS_WITHDRAWN,
    LEVEL_RETENTION_CATEGORIES,
    LegalBasisLifecycleError,
    basis_loss_evidence_lines,
    basis_withdrawal_state_file_path,
    level_processing_allowed,
    level_retention_categories,
    lost_basis_dispositions,
    measurement_level_basis_states,
    plan_processing_stop,
    read_basis_withdrawal_register,
    withdrawn_level_keys,
)
from twobrain_rec_server.product_analytics.provider_config import (
    ProductAnalyticsProviderConfig,
)
from twobrain_rec_server.product_analytics.readiness import (
    BLOCKER_LEGAL_BASIS_WITHDRAWN,
    build_rollout_readiness_report,
)
from twobrain_rec_server.product_analytics.retention import retention_rule

WITHDRAWAL_DATE = date(2026, 9, 18)
WITHDRAWAL_LINE = (
    "basis_withdrawal level=provider_analytics state=withdrawn "
    "withdrawn_at=2026-09-18 reason=consent_withdrawn_by_visitors "
    "evidence_ref=ev-273-basis-withdrawal"
)
PROVIDER_CATEGORIES = ("posthog_product_events", "yandex_page_events", "yandex_offline_conversions")


def _config(*, enabled: bool = True) -> ProductAnalyticsProviderConfig:
    return ProductAnalyticsProviderConfig.from_settings(
        Settings(
            product_analytics_enabled=enabled,
            product_analytics_anonymous_aggregate_enabled=enabled,
            product_analytics_posthog_enabled=enabled,
            product_analytics_yandex_all_pages_enabled=enabled,
            product_analytics_yandex_offline_enabled=enabled,
        )
    )


def _register(tmp_path: Path, *lines: str, version: str = "1"):
    path = tmp_path / "legal-basis-withdrawals"
    path.write_text(
        "\n".join((f"legal_basis_state_version={version}", *lines)) + "\n",
        encoding="utf-8",
    )
    return read_basis_withdrawal_register({BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)})


# --- The state of a level ---------------------------------------------------


def test_every_measurement_level_declares_its_storage_and_its_basis(tmp_path: Path) -> None:
    config = _config()
    states = measurement_level_basis_states(config)

    assert [state.level_key for state in states] == [
        "anonymous_aggregate",
        "attribution_profiles",
        "provider_analytics",
    ]
    # Level 3 also needs recorded launch approvals, so configuration alone
    # leaves it unconfirmed and it must not process anything.
    assert [state.state for state in states] == [
        LEGAL_BASIS_CONFIRMED,
        LEGAL_BASIS_CONFIRMED,
        LEGAL_BASIS_NOT_CONFIRMED,
    ]
    assert states[2].reason is not None
    for state in states:
        assert level_retention_categories(state.level_key)
    assert level_retention_categories("provider_analytics") == PROVIDER_CATEGORIES


def test_unknown_level_has_no_declared_storage() -> None:
    with pytest.raises(LegalBasisLifecycleError):
        level_retention_categories("screen_recording")


def test_disabled_level_is_not_confirmed() -> None:
    config = _config(enabled=False)
    states = measurement_level_basis_states(config)

    assert {state.state for state in states} == {LEGAL_BASIS_NOT_CONFIRMED}
    for state in states:
        assert level_processing_allowed(state.level_key, states) is False


def test_absent_register_leaves_configured_levels_confirmed(tmp_path: Path) -> None:
    register = read_basis_withdrawal_register(
        {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(tmp_path / "absent")}
    )

    assert register.available is False
    assert register.withdrawals == ()
    states = measurement_level_basis_states(_config(), withdrawals=register)
    assert level_processing_allowed("attribution_profiles", states) is True
    assert level_processing_allowed("provider_analytics", states) is False


def test_unknown_level_is_never_allowed_to_process(tmp_path: Path) -> None:
    states = measurement_level_basis_states(_config())

    assert level_processing_allowed("attribution_profiles", states) is True
    assert level_processing_allowed("attribution_profiles_v2", states) is False
    assert level_processing_allowed("attribution_profiles", ()) is False


def test_recorded_withdrawal_stops_the_level(tmp_path: Path) -> None:
    register = _register(tmp_path, WITHDRAWAL_LINE)

    states = measurement_level_basis_states(_config(), withdrawals=register)

    assert withdrawn_level_keys(states) == ("provider_analytics",)
    assert level_processing_allowed("provider_analytics", states) is False
    assert level_processing_allowed("attribution_profiles", states) is True
    withdrawn = register.withdrawal("provider_analytics")
    assert withdrawn is not None
    assert withdrawn.withdrawn_on() == WITHDRAWAL_DATE


def test_withdrawal_state_file_path_follows_the_environment(tmp_path: Path) -> None:
    explicit = tmp_path / "explicit-state"
    assert basis_withdrawal_state_file_path(
        {BASIS_WITHDRAWAL_STATE_FILE_ENV: str(explicit)}
    ) == str(explicit)
    assert basis_withdrawal_state_file_path(
        {"GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_DIR": str(tmp_path)}
    ) == str(tmp_path / "legal-basis-withdrawals")


def test_unsupported_state_version_is_reported(tmp_path: Path) -> None:
    register = _register(tmp_path, WITHDRAWAL_LINE, version="2")

    assert register.file_errors == ("legal_basis_state_version_unsupported",)
    assert len(register.withdrawals) == 1, "a protective record must not be dropped"


def test_unreadable_withdrawal_records_are_dropped(tmp_path: Path) -> None:
    register = _register(
        tmp_path,
        WITHDRAWAL_LINE.replace("level=provider_analytics", "level=unknown_level"),
        WITHDRAWAL_LINE.replace("withdrawn_at=2026-09-18", "withdrawn_at=not_a_date"),
        WITHDRAWAL_LINE.replace("state=withdrawn", "state=proposed"),
        WITHDRAWAL_LINE.replace("reason=consent_withdrawn_by_visitors", "reason=опа"),
        WITHDRAWAL_LINE,
    )

    assert len(register.withdrawals) == 1
    assert register.withdrawals[0].level_key == "provider_analytics"


def test_a_withdrawal_dated_in_the_future_is_not_effective_yet(tmp_path: Path) -> None:
    register = _register(
        tmp_path,
        WITHDRAWAL_LINE.replace("withdrawn_at=2026-09-18", "withdrawn_at=2027-01-01"),
    )

    assert register.withdrawals == ()


# --- The stop, and the term it has to happen in ----------------------------


def test_erasure_deadline_is_taken_from_the_retention_rules() -> None:
    lost_at = datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    disposition = plan_processing_stop(
        level_key="provider_analytics",
        basis_lost_at=lost_at,
        reason="consent_withdrawn_by_visitors",
    )

    assert disposition.processing_state == "stopped"
    assert [action.category for action in disposition.actions] == list(PROVIDER_CATEGORIES)
    for action in disposition.actions:
        rule = retention_rule(action.category)
        assert action.retention_days == rule.enforced_retention_days()
        assert action.due_at == lost_at + timedelta(days=rule.enforced_retention_days())
        assert action.disposition == CATEGORY_DISPOSITIONS[action.category]
        assert action.method == rule.provider_delete_method
        assert action.execution == (
            EXECUTION_LOCAL if rule.storage == "graf_postgres" else EXECUTION_PROVIDER_REQUEST
        )
    # FR-048 introduces no new number: the binding deadline is the shortest term.
    assert disposition.deadline == lost_at + timedelta(days=90)


def test_naive_basis_loss_moment_is_read_as_utc() -> None:
    disposition = plan_processing_stop(
        level_key="anonymous_aggregate",
        basis_lost_at=datetime(2026, 9, 18, 12, 0),  # noqa: DTZ001 - deliberately naive
        reason="legal_basis_withdrawn",
    )

    assert disposition.basis_lost_at == datetime(2026, 9, 18, 12, 0, tzinfo=UTC)
    assert disposition.deadline == datetime(2026, 9, 18, 12, 0, tzinfo=UTC) + timedelta(days=1095)


def test_provider_held_categories_are_ordered_from_the_provider() -> None:
    disposition = plan_processing_stop(
        level_key="provider_analytics",
        basis_lost_at=datetime(2026, 9, 18, tzinfo=UTC),
        reason="consent_withdrawn_by_visitors",
    )

    assert {action.execution for action in disposition.actions} == {EXECUTION_PROVIDER_REQUEST}
    assert all(action.storage != "graf_postgres" for action in disposition.actions)
    assert disposition.as_dict()["level_key"] == "provider_analytics"


def test_category_without_a_declared_disposition_is_a_configuration_error() -> None:
    with pytest.raises(LegalBasisLifecycleError):
        plan_processing_stop(
            level_key="provider_analytics",
            basis_lost_at=datetime(2026, 9, 18, tzinfo=UTC),
            reason="consent_withdrawn_by_visitors",
            affected_categories=("exported_report",),
        )


def test_level_without_an_affected_category_is_a_configuration_error() -> None:
    with pytest.raises(LegalBasisLifecycleError):
        plan_processing_stop(
            level_key="provider_analytics",
            basis_lost_at=datetime(2026, 9, 18, tzinfo=UTC),
            reason="consent_withdrawn_by_visitors",
            affected_categories=(),
        )


def test_lost_basis_dispositions_are_dated_by_the_records(tmp_path: Path) -> None:
    register = _register(tmp_path, WITHDRAWAL_LINE)

    plans = lost_basis_dispositions(
        _config(), withdrawals=register, now=datetime(2026, 9, 25, tzinfo=UTC)
    )

    assert [plan.level_key for plan in plans] == ["provider_analytics"]
    assert plans[0].basis_lost_at == datetime(2026, 9, 18, tzinfo=UTC)
    assert plans[0].deadline == datetime(2026, 9, 18, tzinfo=UTC) + timedelta(days=90)


def test_no_withdrawal_means_no_erasure_plan(tmp_path: Path) -> None:
    register = _register(tmp_path)

    assert lost_basis_dispositions(
        _config(), withdrawals=register, now=datetime(2026, 9, 25, tzinfo=UTC)
    ) == ()


# --- The evidence -----------------------------------------------------------


def test_evidence_lines_record_the_erasure_and_the_deadline() -> None:
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        BasisLossErasureResult,
    )

    erased_at = datetime(2026, 9, 20, tzinfo=UTC)
    due_at = datetime(2026, 12, 17, tzinfo=UTC)
    result = BasisLossErasureResult(
        level_key="attribution_profiles",
        category="visit_attribution",
        disposition="delete",
        execution=EXECUTION_LOCAL,
        rows_affected=3,
        due_at=due_at,
        erased_at=erased_at,
    )

    lines = basis_loss_evidence_lines([result], reason="legal_basis_withdrawn")

    assert len(lines) == 1
    assert "level=attribution_profiles" in lines[0]
    assert "category=visit_attribution" in lines[0]
    assert "rows_affected=3" in lines[0]
    assert "within_deadline=true" in lines[0]
    assert result.within_deadline is True
    assert "2026-12-17" in lines[0]


def test_late_erasure_is_recorded_as_late() -> None:
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        BasisLossErasureResult,
    )

    result = BasisLossErasureResult(
        level_key="attribution_profiles",
        category="visit_attribution",
        disposition="delete",
        execution=EXECUTION_LOCAL,
        rows_affected=1,
        due_at=datetime(2026, 12, 17, tzinfo=UTC),
        erased_at=datetime(2027, 1, 5, tzinfo=UTC),
    )

    assert result.within_deadline is False
    assert "within_deadline=false" in basis_loss_evidence_lines(
        [result], reason="legal_basis_withdrawn"
    )[0]


def test_evidence_refuses_personal_data() -> None:
    from twobrain_rec_server.product_analytics.advertising_transfer import (
        AdvertisingTransferTraceViolation,
    )
    from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
        BasisLossErasureResult,
        assert_metadata_only_evidence,
    )

    assert_metadata_only_evidence({"category": "visit_attribution", "rows_affected": 1})
    with pytest.raises(AdvertisingTransferTraceViolation):
        assert_metadata_only_evidence({"evidence_ref": "customer@example.com"})
    result = BasisLossErasureResult(
        level_key="attribution_profiles",
        category="visit_attribution",
        disposition="delete",
        execution=EXECUTION_LOCAL,
        rows_affected=0,
        due_at=datetime(2026, 12, 17, tzinfo=UTC),
        erased_at=datetime(2026, 9, 20, tzinfo=UTC),
    )
    assert result.as_dict()["level_key"] == "attribution_profiles"


# --- The readiness report ---------------------------------------------------


def test_readiness_is_blocked_while_a_withdrawal_is_recorded(tmp_path: Path) -> None:
    report = build_rollout_readiness_report(
        Settings(),
        environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(tmp_path / "absent")},
    )
    assert BLOCKER_LEGAL_BASIS_WITHDRAWN not in report.blockers
    assert report.states["legal_basis_lifecycle"] == "no_recorded_withdrawal"

    path = tmp_path / "withdrawal-state"
    path.write_text(
        "legal_basis_state_version=1\n" + WITHDRAWAL_LINE + "\n", encoding="utf-8"
    )
    blocked = build_rollout_readiness_report(
        Settings(), environ={BASIS_WITHDRAWAL_STATE_FILE_ENV: str(path)}
    )

    assert BLOCKER_LEGAL_BASIS_WITHDRAWN in blocked.blockers
    assert blocked.blockers.count(BLOCKER_LEGAL_BASIS_WITHDRAWN) == 1
    assert blocked.verdict == "blocked"
    assert blocked.states["legal_basis_lifecycle"] == (
        "processing_stopped_erasure_required:provider_analytics"
    )
    assert blocked.states["legal_basis_provider_analytics"] == LEGAL_BASIS_WITHDRAWN
    assert blocked.states["advertising_transfer"] == "blocked_no_recorded_basis"
    assert blocked.states["telecom_advertising"] == "blocked_subscriber_prior_consent_required"


def test_readiness_reports_the_recorded_transfer_basis(tmp_path: Path) -> None:
    from twobrain_rec_server.product_analytics.advertising_transfer import (
        ADVERTISING_TRANSFER_STATE_FILE_ENV,
    )

    path = tmp_path / "advertising-transfers"
    path.write_text(
        "advertising_transfer_state_version=1\n"
        "basis recipient=yandex_metrica purpose=yandex_offline_conversions "
        "state=confirmed basis=consent confirmed_by=privacy_reviewer "
        "confirmed_at=2026-09-18 scope=offline_conversion_transfer_basis\n",
        encoding="utf-8",
    )

    report = build_rollout_readiness_report(
        Settings(), environ={ADVERTISING_TRANSFER_STATE_FILE_ENV: str(path)}
    )

    assert report.states["advertising_transfer"] == "basis_recorded"


def test_category_dispositions_cover_every_level_category() -> None:
    for categories in LEVEL_RETENTION_CATEGORIES.values():
        for category in categories:
            assert category in CATEGORY_DISPOSITIONS
            assert retention_rule(category).enforced_retention_days() > 0


# --- The approved deployment, and the same deployment after a withdrawal ----


def _approval_environ(tmp_path: Path) -> dict[str, str]:
    """Every launch approval recorded by a named role, as the operator keeps it."""

    from twobrain_rec_server.product_analytics.approvals import (
        APPROVAL_KINDS,
        APPROVAL_STATE_FILE_ENV,
    )

    records = [
        f"approval kind={kind} state=recorded approved_by={kind}_role_owner "
        "approved_at=2026-09-18 scope=feature_273_launch"
        for kind in APPROVAL_KINDS
    ]
    path = tmp_path / "launch-approvals"
    path.write_text(
        "\n".join(("approval_state_version=1", *records)) + "\n", encoding="utf-8"
    )
    return {APPROVAL_STATE_FILE_ENV: str(path)}


def _approved_settings(**overrides) -> Settings:
    arguments = {
        "product_analytics_enabled": True,
        "product_analytics_anonymous_aggregate_enabled": True,
        "product_analytics_posthog_enabled": True,
        "product_analytics_yandex_all_pages_enabled": True,
        "product_analytics_yandex_offline_enabled": True,
        "product_analytics_validation_mode": "live_safe",
        "product_analytics_provider_mode": "parallel_measurement",
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
    arguments.update(overrides)
    return Settings(**arguments)


def test_every_level_is_confirmed_once_its_approvals_are_recorded(tmp_path: Path) -> None:
    environ = _approval_environ(tmp_path)
    settings = _approved_settings()

    states = measurement_level_basis_states(
        ProductAnalyticsProviderConfig.from_settings(settings, environ=environ)
    )
    assert [state.state for state in states] == [
        LEGAL_BASIS_CONFIRMED,
        LEGAL_BASIS_CONFIRMED,
        LEGAL_BASIS_CONFIRMED,
    ]
    assert all(level_processing_allowed(state.level_key, states) for state in states)

    report = build_rollout_readiness_report(settings, environ=environ)
    assert report.states["legal_basis_lifecycle"] == "no_recorded_withdrawal"
    assert report.states["legal_basis_provider_analytics"] == LEGAL_BASIS_CONFIRMED
    assert BLOCKER_LEGAL_BASIS_WITHDRAWN not in report.blockers


def test_a_recorded_withdrawal_stops_a_level_even_after_its_approvals(
    tmp_path: Path,
) -> None:
    environ = _approval_environ(tmp_path)
    withdrawal = tmp_path / "legal-basis-withdrawals"
    withdrawal.write_text(
        "legal_basis_state_version=1\n" + WITHDRAWAL_LINE + "\n", encoding="utf-8"
    )
    environ[BASIS_WITHDRAWAL_STATE_FILE_ENV] = str(withdrawal)
    settings = _approved_settings()

    states = measurement_level_basis_states(
        ProductAnalyticsProviderConfig.from_settings(settings, environ=environ),
        withdrawals=read_basis_withdrawal_register(environ),
    )
    report = build_rollout_readiness_report(settings, environ=environ)

    assert level_processing_allowed("provider_analytics", states) is False
    assert report.states["legal_basis_provider_analytics"] == LEGAL_BASIS_WITHDRAWN
    assert BLOCKER_LEGAL_BASIS_WITHDRAWN in report.blockers
    assert report.states["legal_basis_lifecycle"].startswith(
        "processing_stopped_erasure_required:"
    )
