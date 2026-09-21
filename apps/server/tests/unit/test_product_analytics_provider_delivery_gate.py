from __future__ import annotations

import time
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.legal_basis_lifecycle import (
    BASIS_WITHDRAWAL_STATE_FILE_ENV,
)
from twobrain_rec_server.product_analytics.provider_delivery_gate import (
    resolve_provider_delivery_gate,
)
from twobrain_rec_server.product_analytics.provider_readiness import (
    BACKUP_STATE_FILE_ENV,
    RESTORE_STATE_FILE_ENV,
    RETENTION_STATE_FILE_ENV,
)


def _write_evidence(tmp_path: Path) -> dict[str, str]:
    now = int(time.time())
    backup = tmp_path / "backup"
    backup.write_text(
        "\n".join(
            (
                "backup_state_version=1",
                "last_attempt_result=pass",
                f"last_success_epoch={now - 3600}",
                "copies_local=2",
                "copies_offsite=1",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    restore = tmp_path / "restore"
    restore.write_text(
        f"restore_state_version=1\nlast_verify_result=pass\nlast_verify_epoch={now - 3600}\n",
        encoding="utf-8",
    )
    retention = tmp_path / "retention"
    retention.write_text(
        "\n".join(
            (
                "retention_state_version=1",
                "result=pass",
                "category=measurement_events retention_days=365 storage=clickhouse enforcement=row_ttl enforcement_verified=true",
                "category=anonymous_aggregate retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true",
                "category=visit_attribution retention_days=90 storage=postgres enforcement=scheduled_task enforcement_verified=true",
                "category=acquisition_attribute retention_days=1095 storage=postgres enforcement=scheduled_task enforcement_verified=true",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    approvals = tmp_path / "approvals"
    approvals.write_text(
        "\n".join(
            (
                "approval_state_version=1",
                *(
                    f"approval kind={kind} state=recorded approved_by=release_owner approved_at=2026-09-18 scope=measurement_scope evidence_ref=ref-{kind}"
                    for kind in ("legal", "privacy", "security", "qa", "rollback", "delivery", "check")
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    access = tmp_path / "access"
    digest = "sha256:" + "a" * 64
    access.write_text(
        "\n".join(
            (
                "access_governance_state_version=1",
                f"reviewed_at={now - 60}",
                f"expires_at={now + 86400}",
                "accepted_operator_count=2",
                "mfa_operator_count=2",
                f"repository_digest={digest}",
                f"config_digest={digest}",
                f"installed_guard_digest={digest}",
                "revocation_review=complete",
                "credential_rotation_review=complete",
                "audit_review=complete",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    basis = tmp_path / "basis"
    basis.write_text("basis_state_version=1\n", encoding="utf-8")
    return {
        BACKUP_STATE_FILE_ENV: str(backup),
        RESTORE_STATE_FILE_ENV: str(restore),
        RETENTION_STATE_FILE_ENV: str(retention),
        "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE": str(approvals),
        "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": str(access),
        "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE": str(basis),
    }


def _settings(tmp_path: Path, **overrides) -> Settings:
    key = tmp_path / "posthog-key"
    key.write_text("phc_test", encoding="utf-8")
    values = {
        "product_analytics_enabled": True,
        "product_analytics_validation_mode": "live_safe",
        "product_analytics_posthog_enabled": True,
        "product_analytics_posthog_host": "https://analytics.example.test",
        "product_analytics_posthog_project_key_file": key,
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
    values.update(overrides)
    return Settings(**values)


def _withdrawal_evidence(tmp_path: Path, level_key: str) -> dict[str, str]:
    environ = _write_evidence(tmp_path)
    Path(environ[BASIS_WITHDRAWAL_STATE_FILE_ENV]).write_text(
        "legal_basis_state_version=1\n"
        f"basis_withdrawal level={level_key} state=withdrawn "
        "withdrawn_at=2026-09-18 reason=legal_basis_withdrawn "
        "evidence_ref=ev-273-provider-gate\n",
        encoding="utf-8",
    )
    return environ


def test_provider_gate_blocks_browser_provider_when_product_analytics_disabled(tmp_path: Path) -> None:
    settings = _settings(tmp_path, product_analytics_enabled=False)
    gate = resolve_provider_delivery_gate(
        settings,
        provider="yandex_all_pages",
        environ=_write_evidence(tmp_path),
    )

    assert gate.allowed is False
    assert "product_analytics_disabled" in gate.blockers
    assert gate.campaign_launch_allowed is False


def test_provider_gate_cannot_report_launch_allowed_when_provider_configuration_is_missing(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path, product_analytics_posthog_host=None, product_analytics_posthog_project_key_file=None)
    gate = resolve_provider_delivery_gate(
        settings,
        provider="posthog",
        environ=_write_evidence(tmp_path),
    )

    assert gate.allowed is False
    assert gate.campaign_launch_allowed is False
    assert "missing_posthog_host" in gate.approval_gate.configuration_blockers
    assert "missing_posthog_project_key_file" in gate.approval_gate.configuration_blockers


def test_provider_gate_blocks_unreadable_yandex_token_before_delivery(tmp_path: Path) -> None:
    settings = _settings(
        tmp_path,
        product_analytics_posthog_enabled=False,
        product_analytics_yandex_offline_enabled=True,
        product_analytics_yandex_counter_id="123",
        product_analytics_yandex_oauth_token_file=tmp_path / "missing-token",
    )
    gate = resolve_provider_delivery_gate(
        settings,
        provider="yandex_offline",
        environ=_write_evidence(tmp_path),
    )

    assert gate.allowed is False
    assert "missing_yandex_oauth_token_file" in gate.blockers


def test_provider_gate_scopes_withdrawal_to_provider_level(tmp_path: Path) -> None:
    gate = resolve_provider_delivery_gate(
        _settings(tmp_path),
        provider="posthog",
        environ=_withdrawal_evidence(tmp_path, "anonymous_aggregate"),
    )

    assert gate.allowed is True
    assert "legal_basis_withdrawn" not in gate.blockers


def test_provider_gate_blocks_withdrawn_provider_level_for_posthog_and_yandex(tmp_path: Path) -> None:
    environ = _withdrawal_evidence(tmp_path, "provider_analytics")

    for provider in ("posthog", "yandex"):
        gate = resolve_provider_delivery_gate(
            _settings(tmp_path),
            provider=provider,
            environ=environ,
        )

        assert "legal_basis_withdrawn" in gate.blockers
        assert "provider_analytics_basis_not_confirmed" in gate.blockers


def test_campaign_gate_blocks_withdrawal_at_any_measurement_level(tmp_path: Path) -> None:
    for level_key in ("anonymous_aggregate", "attribution_profiles", "provider_analytics"):
        gate = resolve_provider_delivery_gate(
            _settings(tmp_path),
            provider="campaign",
            environ=_withdrawal_evidence(tmp_path, level_key),
        )

        assert "legal_basis_withdrawn" in gate.blockers
