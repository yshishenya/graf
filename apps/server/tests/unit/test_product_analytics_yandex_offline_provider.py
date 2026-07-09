from datetime import UTC, datetime
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.events import build_activation_event
from twobrain_rec_server.product_analytics.posthog_client import ProviderTransportResponse
from twobrain_rec_server.product_analytics.yandex_offline import (
    YandexOfflineConversionExporter,
    build_yandex_offline_conversion,
    is_yandex_offline_event_allowed,
)


def _approved_event(name: str = "desktop_account_connected"):
    return build_activation_event(
        name,
        stable_pseudonymous_user_id="graf_pseudo_user_yandex",
        occurred_at=datetime(2026, 7, 9, 10, 0, tzinfo=UTC),
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
            "yandex_client_id_present": True,
            "yandex_user_id_present": True,
            "yclid_present": False,
            "attribution_reliability": "campaign_linked_reliable",
        },
    )


def test_yandex_offline_subset_rejects_unapproved_product_events() -> None:
    assert is_yandex_offline_event_allowed("desktop_account_connected") is True
    assert is_yandex_offline_event_allowed("first_value_session_completed") is True
    assert is_yandex_offline_event_allowed("desktop_first_opened") is False


def test_yandex_offline_row_uses_redacted_identity_source_and_dedupe_key() -> None:
    row = build_yandex_offline_conversion(_approved_event())
    payload = row.as_dict()

    assert payload["event_name"] == "desktop_account_connected"
    assert payload["identity_kind"] == "UserId"
    assert payload["identity_value_source"] == "graf_pseudonymous_user_redacted"
    assert payload["conversion_unix_time"] == "1783591200"
    assert payload["upload_state"] == "queued"
    assert payload["dedupe_key"].startswith("graf_yandex_dedupe_")
    assert payload["upload_batch_id"].startswith("graf_yandex_batch_")
    assert "graf_pseudo_user_yandex" not in str(payload)


def test_yandex_offline_exporter_returns_redacted_dry_run_status(tmp_path: Path) -> None:
    oauth_file = tmp_path / "yandex_oauth_token"
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")
    exporter = YandexOfflineConversionExporter.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="provider_smoke",
            product_analytics_provider_mode="parallel_measurement",
            product_analytics_yandex_offline_enabled=True,
            product_analytics_yandex_counter_id="12345678",
            product_analytics_yandex_oauth_token_file=oauth_file,
        )
    )

    result = exporter.export(_approved_event())

    assert result.status == "dry_run"
    assert result.provider == "yandex_offline"
    assert result.retryable is False
    assert "synthetic-yandex-token" not in str(result.as_dict())
    assert "12345678" not in str(result.as_dict())


def test_yandex_offline_duplicate_key_is_stable_for_same_event() -> None:
    first = build_yandex_offline_conversion(_approved_event())
    second = build_yandex_offline_conversion(_approved_event())

    assert first.dedupe_key == second.dedupe_key


def test_yandex_offline_does_not_treat_stable_user_id_as_yandex_userid_without_page_binding() -> None:
    event = build_activation_event(
        "desktop_account_connected",
        stable_pseudonymous_user_id="graf_pseudo_user_yandex",
        occurred_at=datetime(2026, 7, 9, 10, 0, tzinfo=UTC),
        properties={
            "auth_method_category": "oauth_provider",
            "account_connection_state": "connected",
            "bridge_present": True,
            "yandex_client_id_present": True,
            "yclid_present": False,
            "attribution_reliability": "needs_runtime_client_id_resolver",
        },
    )

    row = build_yandex_offline_conversion(event)

    assert row.identity_kind == "ClientId"
    assert row.identity_value_source == "runtime_yandex_client_id_redacted"


def test_yandex_live_safe_upload_uses_multipart_without_result_value_leak(tmp_path: Path) -> None:
    oauth_file = tmp_path / "yandex_oauth_token"
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")
    calls: list[tuple[str, dict, bytes]] = []

    def fake_transport(url: str, headers: dict, body: bytes, timeout: float) -> ProviderTransportResponse:
        calls.append((url, dict(headers), body))
        return ProviderTransportResponse(status_code=200, body='{"uploading":{"id":1}}')

    exporter = YandexOfflineConversionExporter.from_settings(
        Settings(
            product_analytics_enabled=True,
            product_analytics_validation_mode="live_safe",
            product_analytics_provider_mode="parallel_measurement",
            product_analytics_yandex_offline_enabled=True,
            product_analytics_yandex_counter_id="12345678",
            product_analytics_yandex_oauth_token_file=oauth_file,
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
    exporter.transport = fake_transport

    result = exporter.export(_approved_event())

    assert result.status == "live_safe_uploaded"
    assert "/management/v1/counter/12345678/offline_conversions/upload" in calls[0][0]
    assert "type=BASIC" in calls[0][0]
    assert calls[0][1]["Authorization"] == "OAuth synthetic-yandex-token"
    assert calls[0][1]["Content-Type"].startswith("multipart/form-data")
    assert b"Target,DateTime,UserId,PurchaseId" in calls[0][2]
    assert b"desktop_account_connected" in calls[0][2]
    assert b"graf_pseudo_user_yandex" in calls[0][2]
    result_body = result.as_dict()
    assert "synthetic-yandex-token" not in str(result_body)
    assert "12345678" not in str(result_body)
    assert "graf_pseudo_user_yandex" not in str(result_body)
