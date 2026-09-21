import json
import time
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.approvals import APPROVAL_KINDS
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.posthog_client import (
    PostHogClientWrapper,
    ProviderTransportResponse,
)
from twobrain_rec_server.product_analytics.provider_readiness import (
    BACKUP_STATE_FILE_ENV,
    RESTORE_STATE_FILE_ENV,
    RETENTION_STATE_FILE_ENV,
)


def _event():
    return build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id="graf_pseudo_user_0123456789abcdef",
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
        },
    )


def test_posthog_provider_smoke_uses_dry_run_without_raw_payload(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
        )
    )

    result = client.capture(_event())
    body = result.as_dict()

    assert result.provider == "posthog"
    assert result.status == "dry_run"
    assert result.retryable is False
    assert "synthetic-posthog-key" not in str(body)
    assert "stable_pseudonymous_user_id" not in str(body)
    assert "properties" not in str(body)


def test_posthog_provider_does_not_synthesize_anonymous_identity(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
        )
    )
    event = build_activation_event(
        "desktop_first_opened",
        properties={"platform": "macos", "bridge_present": True},
    )

    result = client.capture(event)

    assert result.status == "identity_missing"
    assert result.retryable is False
    assert "graf_pseudo_anonymous" not in str(result.as_dict())


def test_posthog_provider_smoke_allows_product_identity_but_rejects_secrets(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
        )
    )

    identity_result = client.capture_event(
        event_name="graf_web_autocapture_click",
        distinct_id="graf_pseudo_user_0123456789abcdef",
        properties={
            "role": "owner",
            "identity_state": "authenticated_pseudonymous",
            "analytics_action": "settings_opened",
        },
    )
    secret_result = client.capture_event(
        event_name="graf_web_autocapture_click",
        distinct_id="graf_pseudo_user_0123456789abcdef",
        properties={
            "role": "owner",
            "analytics_action": "access_token",
        },
    )

    assert identity_result.status == "dry_run"
    assert secret_result.status == "payload_rejected"


def test_posthog_live_safe_delivery_is_blocked_without_execute_approval(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="render_only",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
        )
    )

    result = client.capture(_event())

    assert result.status == "live_safe_blocked"
    assert result.retryable is True
    assert result.detail == "Live PostHog delivery requires explicit production rollout approval"


def _write_live_gate_evidence(tmp_path: Path) -> dict[str, str]:
    now = int(time.time())
    backup = tmp_path / "backup-state"
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
    restore = tmp_path / "restore-state"
    restore.write_text(
        "\n".join(
            (
                "restore_state_version=1",
                "last_verify_result=pass",
                f"last_verify_epoch={now - 2 * 86400}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    retention = tmp_path / "retention-state"
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
    approvals = tmp_path / "launch-approvals"
    approvals.write_text(
        "\n".join(
            (
                "approval_state_version=1",
                *(
                    f"approval kind={kind} state=recorded approved_by=release_owner approved_at=2026-09-18 scope=measurement_scope evidence_ref=ref-{kind}"
                    for kind in APPROVAL_KINDS
                ),
            )
        )
        + "\n",
        encoding="utf-8",
    )
    access = tmp_path / "access-governance-state"
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
    return {
        BACKUP_STATE_FILE_ENV: str(backup),
        RESTORE_STATE_FILE_ENV: str(restore),
        RETENTION_STATE_FILE_ENV: str(retention),
        "GRAF_PRODUCT_ANALYTICS_APPROVAL_STATE_FILE": str(approvals),
        "GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE": str(access),
        "GRAF_PRODUCT_ANALYTICS_LEGAL_BASIS_STATE_FILE": str(tmp_path / "missing-withdrawals"),
    }


def test_posthog_live_delivery_never_transports_without_common_gate(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    calls: list[object] = []

    def fake_transport(*args) -> ProviderTransportResponse:
        calls.append(args)
        return ProviderTransportResponse(status_code=200, body='{"status":"ok"}')

    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="live_safe",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_legal_approved=True,
            product_analytics_privacy_approved=True,
            product_analytics_security_approved=True,
            product_analytics_qa_approved=True,
            product_analytics_disclosure_approved=True,
            product_analytics_dashboard_ready=True,
            product_analytics_provider_smoke_approved=True,
            product_analytics_rollback_approved=True,
            product_analytics_live_provider_delivery_approved=True,
        ),
        environ={},
    )
    client.transport = fake_transport

    result = client.capture(_event())

    assert result.status == "live_safe_blocked"
    assert "analytics_operations_not_ready" in result.metadata["blockers"]
    assert calls == []


def test_posthog_live_safe_delivery_posts_capture_payload_without_result_payload_leak(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    calls: list[tuple[str, dict, dict]] = []

    def fake_transport(url: str, headers: dict, body: bytes, timeout: float) -> ProviderTransportResponse:
        calls.append((url, dict(headers), json.loads(body.decode("utf-8"))))
        return ProviderTransportResponse(status_code=200, body='{"status":"ok"}')

    gate_environ = _write_live_gate_evidence(tmp_path)
    access_path = Path(gate_environ["GRAF_PRODUCT_ANALYTICS_ACCESS_GOVERNANCE_STATE_FILE"])
    access_text = access_path.read_text(encoding="utf-8")
    access_path.write_text(
        access_text.replace("reviewed_at=1799999940", "reviewed_at=1789865441")
        .replace("expires_at=1800086400", "expires_at=1789951901"),
        encoding="utf-8",
    )
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="live_safe",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
            product_analytics_posthog_host="https://analytics.example.test",
            product_analytics_posthog_project_key_file=project_key_file,
            product_analytics_legal_approved=True,
            product_analytics_privacy_approved=True,
            product_analytics_security_approved=True,
            product_analytics_qa_approved=True,
            product_analytics_disclosure_approved=True,
            product_analytics_dashboard_ready=True,
            product_analytics_provider_smoke_approved=True,
            product_analytics_rollback_approved=True,
            product_analytics_live_provider_delivery_approved=True,
        ),
        environ=gate_environ,
    )
    client.transport = fake_transport

    result = client.capture(_event())

    assert result.status == "live_safe_sent"
    assert calls[0][0] == "https://analytics.example.test/capture/"
    assert calls[0][1]["Content-Type"] == "application/json"
    assert calls[0][2]["api_key"] == "synthetic-posthog-key"
    assert calls[0][2]["event"] == "desktop_account_connected"
    assert calls[0][2]["distinct_id"] == "graf_pseudo_user_0123456789abcdef"
    assert calls[0][2]["properties"]["source_feature"] == "096-product-analytics-provider-rollout"
    result_body = result.as_dict()
    assert "synthetic-posthog-key" not in str(result_body)
    assert "graf_pseudo_user_0123456789abcdef" not in str(result_body)
    assert "properties" not in str(result_body)


def test_posthog_missing_secret_or_host_is_configuration_error() -> None:
    client = PostHogClientWrapper.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="posthog_primary",
            product_analytics_posthog_enabled=True,
        )
    )

    result = client.capture(_event())

    assert result.status == "configuration_error"
    assert result.retryable is False


def test_posthog_disabled_returns_measurement_gap_not_product_failure() -> None:
    client = PostHogClientWrapper.from_settings(Settings())

    result = client.capture(_event())

    assert result.status == "disabled"
    assert result.retryable is False
