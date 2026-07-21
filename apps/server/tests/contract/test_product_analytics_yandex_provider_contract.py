from datetime import UTC, datetime, timedelta
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.product_analytics.attribution import AttributionBridgeRecord
from twobrain_rec_server.product_analytics.event_catalog import YANDEX_OFFLINE_CONVERSION_EVENTS
from twobrain_rec_server.product_analytics.provider_readiness import build_provider_readiness
from twobrain_rec_server.product_analytics.retention import provider_lifecycle_records


def test_yandex_provider_reuses_093_counter_and_blocks_campaign_claims(tmp_path: Path) -> None:
    oauth_file = tmp_path / "yandex_token"
    oauth_file.write_text("synthetic-yandex-token", encoding="utf-8")
    settings = Settings(
        product_analytics_enabled=True,
        product_analytics_validation_mode="provider_smoke",
        product_analytics_provider_mode="parallel_measurement",
        product_analytics_yandex_all_pages_enabled=True,
        product_analytics_yandex_offline_enabled=True,
        product_analytics_yandex_counter_id="12345678",
        product_analytics_yandex_oauth_token_file=oauth_file,
        product_analytics_legal_approved=True,
    )

    readiness = build_provider_readiness(settings).yandex_offline.as_dict()

    assert readiness["configured"] is True
    assert readiness["metadata"]["approved_conversions"] == (
        "desktop_account_connected,first_value_session_completed"
    )
    assert build_provider_readiness(settings).yandex_all_pages.metadata["counter_strategy"] == "reuse_093_runtime_only"
    assert settings.product_analytics_campaign_readiness_approved is False


def test_yandex_lifecycle_truth_covers_page_events_offline_conversions_and_aggregates() -> None:
    records = {
        (record.provider, record.data_class): record
        for record in provider_lifecycle_records()
        if record.provider == "yandex_metrica"
    }

    assert ("yandex_metrica", "page_event") in records
    assert ("yandex_metrica", "offline_conversion") in records
    assert ("yandex_metrica", "provider_aggregate") in records
    assert records[("yandex_metrica", "offline_conversion")].deletion_scope == "not_promised"
    assert "already uploaded" in records[("yandex_metrica", "offline_conversion")].dashboard_caveat


def test_yandex_offline_conversion_contract_is_exactly_two_events() -> None:
    assert YANDEX_OFFLINE_CONVERSION_EVENTS == (
        "desktop_account_connected",
        "first_value_session_completed",
    )


def test_attribution_bridge_reports_yandex_identity_presence_without_raw_values() -> None:
    now = datetime(2026, 7, 9, tzinfo=UTC)
    record = AttributionBridgeRecord(
        graf_attribution_id="graf_attr_synthetic",
        bridge_token_hash="graf_bridge_hash_synthetic",
        created_at=now,
        expires_at=now + timedelta(hours=72),
        source_context={},
        yandex_user_id_present=True,
        yandex_client_id_present=True,
        yclid_present=True,
    )
    payload = record.as_dict()

    assert payload["yandex_identity_sources_present"] == ["UserId", "ClientId", "Yclid"]
    assert "ClientID value" not in str(payload)
    assert "Yclid value" not in str(payload)
