from pathlib import Path

import pytest

from twobrain_rec_server.product_analytics.provider_secrets import (
    ProviderSecretError,
    default_provider_secret_inventory,
    read_secret_file,
    redact_provider_value,
    secret_file_status,
)


def test_secret_file_status_redacts_present_values(tmp_path: Path) -> None:
    secret_file = tmp_path / "posthog_project_key"
    secret_file.write_text("synthetic-secret-value", encoding="utf-8")

    status = secret_file_status(secret_file, logical_name="POSTHOG_PROJECT_KEY")

    assert status.logical_name == "POSTHOG_PROJECT_KEY"
    assert status.present is True
    assert status.redacted_value == "configured_redacted"
    assert status.evidence_state == "redacted_recorded"
    assert "synthetic-secret-value" not in str(status.as_dict())


def test_read_secret_file_returns_value_but_never_puts_value_in_repr(tmp_path: Path) -> None:
    secret_file = tmp_path / "yandex_oauth_token"
    secret_file.write_text("synthetic-oauth-token", encoding="utf-8")

    secret = read_secret_file(secret_file, logical_name="YANDEX_OAUTH_TOKEN")

    assert secret.value == "synthetic-oauth-token"
    assert secret.redacted_value == "configured_redacted"
    assert "synthetic-oauth-token" not in repr(secret)
    assert "synthetic-oauth-token" not in str(secret.as_redacted_dict())


def test_missing_or_empty_secret_files_are_blocked(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    empty = tmp_path / "empty"
    empty.write_text("", encoding="utf-8")

    with pytest.raises(ProviderSecretError, match="missing"):
        read_secret_file(missing, logical_name="POSTHOG_PROJECT_KEY")
    with pytest.raises(ProviderSecretError, match="empty"):
        read_secret_file(empty, logical_name="POSTHOG_PROJECT_KEY")


def test_provider_value_redaction_is_stable_and_non_revealing() -> None:
    assert redact_provider_value(None) == "not_configured"
    assert redact_provider_value("") == "not_configured"
    assert redact_provider_value("12345678") == "configured_redacted"
    assert redact_provider_value("synthetic-secret-value") == "configured_redacted"


def test_secret_inventory_records_owner_rotation_and_evidence_state() -> None:
    inventory = default_provider_secret_inventory()
    posthog_project_key = next(entry for entry in inventory if entry.logical_name == "POSTHOG_PROJECT_KEY")
    yandex_oauth = next(entry for entry in inventory if entry.logical_name == "YANDEX_OAUTH_TOKEN")

    assert posthog_project_key.owner_role == "product analytics operator"
    assert "Rotate" in posthog_project_key.rotation_note
    assert yandex_oauth.owner_role == "growth analytics operator"
    assert yandex_oauth.evidence_state == "missing"
    assert all("secret value" not in entry.as_dict()["rotation_note"].lower() for entry in inventory)
