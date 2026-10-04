from __future__ import annotations

import json
import time
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

import pytest
from pydantic import ValidationError

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
                    for kind in (
                        "legal",
                        "privacy",
                        "security",
                        "qa",
                        "rollback",
                        "delivery",
                        "check",
                    )
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
    basis.write_text("legal_basis_state_version=1\n", encoding="utf-8")
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


def test_provider_gate_blocks_browser_provider_when_product_analytics_disabled(
    tmp_path: Path,
) -> None:
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
    settings = _settings(
        tmp_path,
        product_analytics_posthog_host=None,
        product_analytics_posthog_project_key_file=None,
    )
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


def test_provider_gate_blocks_withdrawn_provider_level_for_posthog_and_yandex(
    tmp_path: Path,
) -> None:
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


def _loss_settings(tmp_path: Path, **overrides) -> Settings:
    values = {
        "product_analytics_posthog_backup_policy": "owner_accepted_loss",
        "product_analytics_explicit_funnel_enabled": True,
        "product_analytics_provider_mode": "posthog_primary",
        "product_analytics_posthog_autocapture_enabled": False,
        "product_analytics_posthog_web_direct_enabled": False,
    }
    values.update(overrides)
    return _settings(tmp_path, **values)


def _no_backup_evidence(tmp_path: Path) -> dict[str, str]:
    environ = _write_evidence(tmp_path)
    Path(environ[BACKUP_STATE_FILE_ENV]).unlink()
    Path(environ[RESTORE_STATE_FILE_ENV]).unlink()
    return environ


def test_posthog_loss_policy_is_explicit_default_required() -> None:
    assert Settings().product_analytics_posthog_backup_policy == "required"
    with pytest.raises(ValidationError):
        Settings(product_analytics_posthog_backup_policy="disabled")


def test_posthog_loss_exception_keeps_raw_evidence_and_campaign_blocked(tmp_path: Path) -> None:
    from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness

    settings = _loss_settings(tmp_path)
    environ = _no_backup_evidence(tmp_path)
    readiness = build_provider_readiness(settings, environ=environ)
    gate = resolve_provider_delivery_gate(settings, provider="posthog", environ=environ)
    campaign = resolve_provider_delivery_gate(settings, provider="campaign", environ=environ)
    assert gate.allowed is True
    assert gate.campaign_launch_allowed is False
    assert gate.as_dict()["approval_gate"]["campaign_launch_allowed"] is False
    assert set(gate.waived_operations_blockers) == {
        "backup_state_unavailable",
        "restore_verification_missing",
    }
    assert readiness.analytics_operations.configured is False
    assert "backup_state_unavailable" in readiness.analytics_operations.blockers
    assert readiness.posthog.metadata["backup_restore"] == "not_required_owner_accepted_loss"
    assert readiness.posthog.metadata["backup_loss_caveat"] == "analytics_may_be_unrecoverable"
    assert readiness.analytics_operations.metadata["backup_last_result"] == "unknown"
    assert campaign.allowed is False
    assert "backup_state_unavailable" in campaign.operations_blockers
    assert "analytics_operations_not_ready" in campaign.blockers
    assert campaign.waived_operations_blockers == ()
    required = settings.model_copy(update={"product_analytics_posthog_backup_policy": "required"})
    restored = resolve_provider_delivery_gate(required, provider="posthog", environ=environ)
    assert restored.allowed is False
    assert "backup_state_unavailable" in restored.operations_blockers
    assert restored.waived_operations_blockers == ()


@pytest.mark.parametrize(
    "overrides",
    [
        {"product_analytics_explicit_funnel_enabled": False},
        {"product_analytics_provider_mode": "parallel_measurement"},
        {"product_analytics_provider_mode": "disabled"},
        {"product_analytics_posthog_enabled": False},
        {"product_analytics_posthog_autocapture_enabled": True},
        {"product_analytics_posthog_web_direct_enabled": True},
        {"product_analytics_posthog_desktop_direct_enabled": True},
        {"product_analytics_direct_desktop_egress_enabled": True},
        {"product_analytics_replay_enabled": True},
        {"product_analytics_yandex_all_pages_enabled": True},
        {"product_analytics_yandex_offline_enabled": True},
    ],
)
def test_posthog_loss_exception_rejects_scope_expansion(tmp_path: Path, overrides: dict) -> None:
    gate = resolve_provider_delivery_gate(
        _loss_settings(tmp_path, **overrides),
        provider="posthog",
        environ=_no_backup_evidence(tmp_path),
    )
    assert gate.allowed is False
    assert "posthog_backup_exception_scope_invalid" in gate.blockers
    assert gate.waived_operations_blockers == ()
    assert "backup_state_unavailable" in gate.operations_blockers


@pytest.mark.parametrize("provider", ["yandex_all_pages", "yandex_offline", "campaign"])
def test_other_paths_never_receive_posthog_loss_exception(tmp_path: Path, provider: str) -> None:
    gate = resolve_provider_delivery_gate(
        _loss_settings(tmp_path),
        provider=provider,
        environ=_no_backup_evidence(tmp_path),
    )
    assert gate.allowed is False
    assert "backup_state_unavailable" in gate.operations_blockers
    assert gate.waived_operations_blockers == ()


@pytest.mark.parametrize("case", ["retention", "access", "legal", "withdrawn", "smoke", "rollback"])
def test_loss_policy_never_waives_remaining_proofs(tmp_path: Path, case: str) -> None:
    settings = _loss_settings(tmp_path)
    environ = _no_backup_evidence(tmp_path)
    if case == "retention":
        Path(environ[RETENTION_STATE_FILE_ENV]).unlink()
    elif case == "access":
        Path(environ["GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE"]).unlink()
    elif case == "withdrawn":
        Path(environ[BASIS_WITHDRAWAL_STATE_FILE_ENV]).write_text(
            "legal_basis_state_version=1\nbasis_withdrawal level=provider_analytics state=withdrawn "
            "withdrawn_at=2026-10-04 reason=legal_basis_withdrawn evidence_ref=synthetic\n"
        )
    else:
        field = {"legal": "legal", "smoke": "provider_smoke", "rollback": "rollback"}[case]
        settings = settings.model_copy(update={f"product_analytics_{field}_approved": False})
    gate = resolve_provider_delivery_gate(settings, provider="posthog", environ=environ)
    assert gate.allowed is False
    if case == "retention":
        assert "retention_state_unavailable" in gate.operations_blockers
    if case == "access":
        assert "analytics_access_governance_not_ready" in gate.blockers


def test_loss_policy_preserves_stale_failed_backup_receipts(tmp_path: Path) -> None:
    from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness

    settings = _loss_settings(tmp_path)
    environ = _write_evidence(tmp_path)
    Path(environ[BACKUP_STATE_FILE_ENV]).write_text(
        "backup_state_version=1\nlast_attempt_result=failed\nlast_success_epoch=1\ncopies_local=0\ncopies_offsite=0\n"
    )
    Path(environ[RESTORE_STATE_FILE_ENV]).write_text(
        "restore_state_version=1\nlast_verify_result=failed\nlast_verify_epoch=1\n"
    )
    readiness = build_provider_readiness(settings, environ=environ)
    gate = resolve_provider_delivery_gate(settings, provider="posthog", environ=environ)
    assert gate.allowed is True
    assert readiness.analytics_operations.metadata["backup_last_result"] == "failed"
    assert readiness.analytics_operations.metadata["restore_verification_result"] == "failed"
    assert set(gate.waived_operations_blockers) == {
        "backup_stale",
        "backup_copy_count_below_minimum",
        "backup_offsite_copy_missing",
        "restore_verification_failed",
    }


@pytest.mark.parametrize(
    "event_name,properties,event_id",
    [
        ("desktop_account_connected", {}, None),
        ("desktop_account_connected", {}, "client-supplied"),
        ("$autocapture", {}, "derived"),
        ("desktop_account_connected", {"unexpected_category": "unknown"}, "derived"),
    ],
)
def test_loss_policy_blocks_generic_capture_before_secret_read(
    tmp_path: Path,
    monkeypatch,
    event_name: str,
    properties: dict,
    event_id: str | None,
) -> None:
    from twobrain_rec_server.product_analytics import posthog_client, provider_secrets

    calls = []
    monkeypatch.setattr(provider_secrets, "read_secret_file", lambda *args, **kwargs: pytest.fail("readiness secret read"))
    monkeypatch.setattr(
        posthog_client, "read_secret_file", lambda *args, **kwargs: pytest.fail("secret read")
    )
    client = posthog_client.PostHogClientWrapper.from_settings(
        _loss_settings(tmp_path),
        environ=_no_backup_evidence(tmp_path),
    )
    client.transport = lambda *args: calls.append(args)
    distinct_id = "graf_pseudo_user_synthetic"
    if event_id == "derived":
        event_id = str(uuid5(NAMESPACE_URL, f"graf-explicit-funnel-v1:{distinct_id}:{event_name}"))
    result = client.capture_event(
        event_name=event_name,
        distinct_id=distinct_id,
        properties=properties,
        explicit_event_id=event_id,
    )
    assert result.status == "live_safe_blocked"
    assert result.metadata["blockers"] == ["posthog_backup_exception_explicit_path_required"]
    assert calls == []


def test_explicit_loss_policy_retries_same_uuid_with_no_ip_transport_contract(
    tmp_path: Path,
) -> None:
    from twobrain_rec_server.product_analytics.explicit_funnel import deliver_milestone
    from twobrain_rec_server.product_analytics.posthog_client import (
        PostHogClientWrapper,
        ProviderTransportResponse,
    )

    settings = _loss_settings(tmp_path)
    calls = []

    def transport(url, headers, body, timeout):
        calls.append(json.loads(body))
        return ProviderTransportResponse(503 if len(calls) == 1 else 200, '{"status":1}')

    client = PostHogClientWrapper.from_settings(settings, environ=_no_backup_evidence(tmp_path))
    client.transport = transport
    state = {
        "consent": {
            "state": "accepted",
            "copy_version": settings.public_analytics_consent_copy_version,
        }
    }
    payload = {
        "event_name": "desktop_account_connected",
        "properties": {"auth_method_category": "unknown"},
    }
    state, receipt = deliver_milestone(
        settings, user_id="synthetic-user", state=state, payload=payload, provider=client
    )
    assert receipt["accepted"] is False
    state, receipt = deliver_milestone(
        settings, user_id="synthetic-user", state=state, payload=payload, provider=client
    )
    assert receipt["accepted"] is True and receipt["ingestion_verified"] is False
    state, duplicate = deliver_milestone(
        settings, user_id="synthetic-user", state=state, payload=payload, provider=client
    )
    assert duplicate["status"] == "duplicate" and duplicate["ingestion_verified"] is False
    assert len(calls) == 2 and calls[0]["uuid"] == calls[1]["uuid"]
    assert (
        calls[1]["properties"]["$ip"] is None and calls[1]["properties"]["$geoip_disable"] is True
    )
