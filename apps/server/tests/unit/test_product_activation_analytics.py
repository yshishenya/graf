import re
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.forbidden_fields import (
    ForbiddenFieldViolation,
    assert_no_forbidden_fields,
    find_forbidden_fields,
)
from twobrain_rec_server.product_analytics.identity import (
    build_safe_identity,
    is_safe_pseudonymous_id,
)
from twobrain_rec_server.product_analytics.milestones import (
    FirstMilestoneLedger,
    first_value_decision,
)
from twobrain_rec_server.product_analytics.posthog_client import PostHogClientWrapper
from twobrain_rec_server.product_analytics.telemetry_gate import (
    ProductTelemetryGateRecord,
    analytics_collection_allowed,
    is_product_use_allowed,
    limited_access_only,
    transition_gate_state,
)

REPO_ROOT = Path(__file__).parents[4]


def _production_settings(**overrides):
    values = {
        "env": "production",
        "database_url": "postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
        "minio_endpoint": "rec-minio:9000",
        "minio_access_key": "twobrain_rec_api",
        "minio_secret_key": "prod-api-secret",
        "minio_bucket": "twobrain-rec-ingest",
        "web_csrf_secret": "prod-web-csrf-secret-32-bytes-minimum",
        "auth_ru_local_storage_attested": True,
    }
    values.update(overrides)
    return Settings(**values)


def test_product_analytics_is_disabled_by_default() -> None:
    settings = Settings()

    assert settings.product_analytics_enabled is False
    assert settings.product_analytics_validation_mode == "disabled"
    assert settings.product_analytics_provider_mode == "disabled"
    assert settings.product_analytics_posthog_enabled is False
    assert settings.product_analytics_yandex_all_pages_enabled is False
    assert settings.product_analytics_yandex_offline_enabled is False
    assert settings.product_analytics_retention_min_days == 90
    assert settings.product_analytics_direct_desktop_egress_enabled is False


def test_product_analytics_validation_modes_are_restricted() -> None:
    assert Settings(product_analytics_validation_mode="live_safe").product_analytics_validation_mode == "live_safe"
    with pytest.raises(ValidationError, match="product_analytics_validation_mode"):
        Settings(product_analytics_validation_mode="live")
    with pytest.raises(ValidationError, match="product_analytics_provider_mode"):
        Settings(product_analytics_provider_mode="all_providers")
    with pytest.raises(ValidationError, match="product_analytics_retention_min_days"):
        Settings(product_analytics_retention_min_days=89)


def test_production_rejects_enabled_product_analytics_without_explicit_gates() -> None:
    with pytest.raises(ValidationError, match="non-disabled validation mode"):
        _production_settings(product_analytics_enabled=True)
    with pytest.raises(ValidationError, match="explicit provider mode"):
        _production_settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="render_only",
        )


def test_production_rejects_direct_desktop_egress_without_all_approvals() -> None:
    with pytest.raises(ValidationError, match="direct desktop product analytics egress"):
        _production_settings(
            product_analytics_direct_desktop_egress_enabled=True,
            product_analytics_direct_desktop_egress_approved=True,
            product_analytics_legal_approved=True,
            product_analytics_provider_smoke_approved=False,
        )


def test_forbidden_field_validator_rejects_private_identity_and_content() -> None:
    payload = {
        "event_name": "first_result_viewed",
        "properties": {
            "meeting_title": "Customer call",
            "email": "user@example.com",
            "local_file_path": "/Users/alice/meeting.wav",
        },
    }

    findings = find_forbidden_fields(payload)

    assert "$.properties.meeting_title" in findings
    assert "$.properties.email" in findings
    assert "$.properties.local_file_path" in findings
    with pytest.raises(ForbiddenFieldViolation):
        assert_no_forbidden_fields(payload)


def test_forbidden_field_validator_allows_graf_pseudonymous_ids_with_phone_like_hashes() -> None:
    payload = {
        "stable_pseudonymous_user_id": "graf_pseudo_user_0df5e588f8ab9069052309bedb08556d",
        "posthog_distinct_id": "graf_pseudo_user_0df5e588f8ab9069052309bedb08556d",
        "workspace_pseudonym": "graf_pseudo_workspace_6ab157262fc817139fa0cdd20dd3d88d",
    }

    assert find_forbidden_fields(payload) == ()
    assert_no_forbidden_fields(payload)


def test_safe_identity_is_pseudonymous_and_has_no_raw_ids() -> None:
    identity = build_safe_identity(
        user_source_id=str(UUID("00000000-0000-0000-0000-000000000094")),
        workspace_source_id="workspace-094",
        account_source_id="account-094",
        device_class="macos",
    )

    assert identity.stable_pseudonymous_user_id.startswith("graf_pseudo_user_")
    assert "00000000-0000-0000-0000-000000000094" not in identity.stable_pseudonymous_user_id
    assert identity.workspace_pseudonym and identity.workspace_pseudonym.startswith("graf_pseudo_workspace_")
    assert identity.account_pseudonym and identity.account_pseudonym.startswith("graf_pseudo_account_")


def test_safe_pseudonymous_identity_contract_is_strict() -> None:
    assert is_safe_pseudonymous_id("graf_pseudo_browser_anonymous")
    assert is_safe_pseudonymous_id("graf_pseudo_user_0df5e588f8ab9069052309bedb08556d")
    assert is_safe_pseudonymous_id("graf_pseudo_workspace_6ab157262fc81713")
    assert is_safe_pseudonymous_id("graf_pseudo_account_01234567")

    assert not is_safe_pseudonymous_id("graf_pseudo_user_realname")
    assert not is_safe_pseudonymous_id("graf_pseudo_user_abc")
    assert not is_safe_pseudonymous_id("graf_pseudo_device_0123456789abcdef")
    assert not is_safe_pseudonymous_id("graf_pseudo_user_01234567@example.test")


def test_event_builder_rejects_fields_outside_allowlist() -> None:
    identity = build_safe_identity(user_source_id="user-094")

    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id=identity.stable_pseudonymous_user_id,
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
        },
    )

    assert event.event_name == "desktop_account_connected"
    assert event.properties["bridge_present"] is True
    with pytest.raises(ForbiddenFieldViolation):
        build_activation_event(
            "desktop_account_connected",
            stable_pseudonymous_user_id=identity.stable_pseudonymous_user_id,
            properties={"meeting_title": "Private"},
        )


def test_first_value_requires_ready_useful_result_view() -> None:
    assert first_value_decision(
        result_state="ready",
        useful_output_present=True,
        useful_result_type="summary",
    ).eligible
    assert not first_value_decision(
        result_state="processing",
        useful_output_present=True,
        useful_result_type="summary",
    ).eligible
    assert not first_value_decision(
        result_state="ready",
        useful_output_present=False,
        useful_result_type="summary",
    ).eligible
    assert not first_value_decision(
        result_state="ready",
        useful_output_present=True,
        useful_result_type="recording_only",
    ).eligible
    assert not first_value_decision(
        result_state="ready",
        useful_output_present=True,
        useful_result_type="summary",
        imported_or_historical=True,
    ).eligible


def test_first_milestones_dedupe_by_stable_pseudonymous_user() -> None:
    ledger = FirstMilestoneLedger()
    user_id = "graf_pseudo_user_abcdef12"

    assert ledger.record(user_id, "desktop_first_opened") is True
    assert ledger.record(user_id, "desktop_first_opened") is False
    assert ledger.record(user_id, "first_result_viewed") is True


def test_telemetry_gate_state_transitions_and_access_rules() -> None:
    record = ProductTelemetryGateRecord()
    accepted = transition_gate_state(
        record,
        "accepted",
        pseudonymous_user_id="graf_pseudo_user_abcdef12",
        accepted_surface="desktop_onboarding",
    )
    update_required = transition_gate_state(accepted, "terms_update_required")
    refused = transition_gate_state(update_required, "refused_updated_terms")
    limited = transition_gate_state(refused, "limited_to_account_legal_export_deletion")

    assert accepted.state == "accepted"
    assert is_product_use_allowed(accepted.state) is True
    assert analytics_collection_allowed(accepted.state) is True
    assert limited_access_only(limited.state) is True
    assert analytics_collection_allowed(limited.state) is False
    with pytest.raises(ValueError):
        transition_gate_state(record, "withdrawn")


def test_posthog_wrapper_is_disabled_by_default() -> None:
    client = PostHogClientWrapper.from_settings(Settings())
    event = build_activation_event("desktop_first_opened", properties={"platform": "macos"})

    result = client.capture(event)

    assert result.provider == "posthog"
    assert result.status == "disabled"


def test_no_live_product_analytics_secrets_are_committed() -> None:
    paths = [
        REPO_ROOT / "apps/server/src/twobrain_rec_server/product_analytics",
        REPO_ROOT / "specs/094-product-activation-analytics",
        REPO_ROOT / "specs/096-product-analytics-provider-rollout",
        REPO_ROOT / "docs/analytics/product-activation-analytics.md",
        REPO_ROOT / "docs/analytics/product-analytics-posthog-runbook.md",
        REPO_ROOT / "docs/analytics/product-analytics-yandex-runbook.md",
        REPO_ROOT / "docs/analytics/product-analytics-provider-rollback.md",
        REPO_ROOT / "infra/posthog",
        REPO_ROOT / "infra/scripts/cd-remote.sh",
        REPO_ROOT / "infra/env/rec.production.env.example",
    ]
    texts = []
    for path in paths:
        if path.is_dir():
            texts.extend(
                file.read_text(encoding="utf-8")
                for file in path.rglob("*")
                if file.is_file() and file.suffix in {".py", ".md", ".yaml", ".yml", ".json", ".txt"}
            )
        elif path.exists():
            texts.append(path.read_text(encoding="utf-8"))
    combined = "\n".join(texts).lower()

    secret_patterns = (
        r"sk_live_[A-Za-z0-9]{8,}",
        r"sk-proj-[A-Za-z0-9]{8,}",
        r"phc_[A-Za-z0-9]{8,}",
        r"oauth_token=[A-Za-z0-9._-]{8,}",
        r"mc\.yandex\.ru/watch/[0-9]{5,}",
        r"Authorization: Bearer [A-Za-z0-9._-]{8,}",
    )
    for pattern in secret_patterns:
        assert re.search(pattern, combined) is None
