import json
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.posthog_client import (
    PostHogClientWrapper,
    ProviderTransportResponse,
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
            "role": "owner@example.test",
            "display_name": "Product Owner",
            "analytics_action": "settings_opened",
        },
    )
    secret_result = client.capture_event(
        event_name="graf_web_autocapture_click",
        distinct_id="graf_pseudo_user_0123456789abcdef",
        properties={
            "role": "owner@example.test",
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


def test_posthog_live_safe_delivery_posts_capture_payload_without_result_payload_leak(tmp_path: Path) -> None:
    project_key_file = tmp_path / "posthog_project_key"
    project_key_file.write_text("synthetic-posthog-key", encoding="utf-8")
    calls: list[tuple[str, dict, dict]] = []

    def fake_transport(url: str, headers: dict, body: bytes, timeout: float) -> ProviderTransportResponse:
        calls.append((url, dict(headers), json.loads(body.decode("utf-8"))))
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
        )
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
