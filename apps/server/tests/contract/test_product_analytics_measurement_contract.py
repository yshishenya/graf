"""HTTP contract of the measurement levels, the aggregate signals and label safety.

The catalogue endpoint and the public pages are the two surfaces a reviewer
reads: the first must show three disabled levels and four local signals, the
second must never echo a hostile campaign label back to the browser.
"""

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.product_analytics.anonymous_aggregate import (
    MINIMUM_AGGREGATE_BUCKET_SIZE,
)
from twobrain_rec_server.product_analytics.event_catalog import ANONYMOUS_AGGREGATE_SIGNAL_NAMES
from twobrain_rec_server.product_analytics.provider_config import MEASUREMENT_LEVEL_KEYS

ANONYMOUS_AGGREGATE_CATEGORY = "anonymous_page_aggregate"
CLIENT_ACQUISITION_CATEGORY = "client_acquisition_attribute"
VISIT_ATTRIBUTION_CATEGORY = "visit_attribution"
PRODUCT_EVENTS_CATEGORY = "posthog_product_events"


def _app(database_url: str) -> object:
    return create_app(
        Settings(
            database_url=database_url,
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
            public_analytics_enabled=True,
            public_analytics_validation_mode="render_only",
            public_analytics_yandex_metrica_id="12345678",
        )
    )


def test_catalog_reports_the_state_of_every_measurement_level(
    postgres_schema_database_url: str,
) -> None:
    with TestClient(_app(postgres_schema_database_url)) as client:
        response = client.get("/api/v1/product-analytics/catalog")

    assert response.status_code == 200
    payload = response.json()
    levels = payload["provider_config"]["measurement_levels"]

    assert [level["key"] for level in levels] == list(MEASUREMENT_LEVEL_KEYS)
    assert [level["level"] for level in levels] == [1, 2, 3]
    # Level 1 keeps no identifier, so FR-009 requires it on every public page and
    # the catalog reports it as running; the optional levels stay off and each one
    # names the reason.
    assert [level["enabled"] for level in levels] == [True, False, False]
    assert all(level["blocked_reasons"] for level in levels[1:])
    assert levels[0]["blocked_reasons"] == []
    assert [level["retention_days"] for level in levels] == [1095, 1095, 365]
    assert levels[0]["identifiers_allowed"] is False
    assert levels[0]["provider_delivery"] is False
    assert levels[1]["identifiers_allowed"] is True
    assert levels[2]["requires_consent"] is True
    assert payload["provider_config"]["campaign_launch_allowed"] is False


def test_catalog_exposes_anonymous_aggregate_signals_without_provider_delivery(
    postgres_schema_database_url: str,
) -> None:
    with TestClient(_app(postgres_schema_database_url)) as client:
        payload = client.get("/api/v1/product-analytics/catalog").json()

    assert tuple(payload["anonymous_aggregate_signal_names"]) == ANONYMOUS_AGGREGATE_SIGNAL_NAMES
    assert [signal["event_name"] for signal in payload["anonymous_aggregate_signals"]] == list(
        ANONYMOUS_AGGREGATE_SIGNAL_NAMES
    )
    for signal in payload["anonymous_aggregate_signals"]:
        assert signal["posthog_destination"] == "none"
        assert signal["yandex_destination"] == "none"
        assert signal["delivery_mode"] == "anonymous_aggregate"
        assert signal["retention_category"] == ANONYMOUS_AGGREGATE_CATEGORY
        assert "ip_address" in signal["forbidden_fields"]
        assert "user_agent" in signal["forbidden_fields"]
        assert "device_fingerprint" in signal["forbidden_fields"]
    provider_events = {event["event_name"] for event in payload["events"]}
    assert len(provider_events) == 6
    assert provider_events.isdisjoint(set(ANONYMOUS_AGGREGATE_SIGNAL_NAMES))


def test_catalog_registers_retention_for_every_new_category(
    postgres_schema_database_url: str,
) -> None:
    with TestClient(_app(postgres_schema_database_url)) as client:
        payload = client.get("/api/v1/product-analytics/catalog").json()

    retention = {rule["category"]: rule for rule in payload["retention"]}
    assert retention[ANONYMOUS_AGGREGATE_CATEGORY]["minimum_retention_days"] == 1095
    assert retention[ANONYMOUS_AGGREGATE_CATEGORY]["maximum_retention_days"] == 1095
    assert retention[CLIENT_ACQUISITION_CATEGORY]["minimum_retention_days"] == 1095
    assert retention[VISIT_ATTRIBUTION_CATEGORY]["minimum_retention_days"] == 90
    assert retention[VISIT_ATTRIBUTION_CATEGORY]["maximum_retention_days"] == 90
    assert retention[PRODUCT_EVENTS_CATEGORY]["maximum_retention_days"] == 365
    for category in (
        ANONYMOUS_AGGREGATE_CATEGORY,
        CLIENT_ACQUISITION_CATEGORY,
        VISIT_ATTRIBUTION_CATEGORY,
        PRODUCT_EVENTS_CATEGORY,
    ):
        assert retention[category]["storage"]
        assert retention[category]["enforcement"]
    assert MINIMUM_AGGREGATE_BUCKET_SIZE == 3


def test_public_page_drops_unsafe_campaign_labels_and_keeps_safe_ones(
    postgres_schema_database_url: str,
) -> None:
    hostile = (
        "?utm_source=Email&utm_medium=CPC&utm_campaign=IvanPetrov"
        "&utm_content=customer@example.com&utm_term=79991112233"
        f"&utm_id={'a' * 120}"
    )

    with TestClient(_app(postgres_schema_database_url)) as client:
        hosted = client.get(f"/{hostile}")
        clean = client.get("/download?utm_source=Yandex_Direct&utm_campaign=2026q3_b2c_launch_ru")

    assert hosted.status_code == 200
    assert "IvanPetrov" not in hosted.text
    assert "customer@example.com" not in hosted.text
    assert "79991112233" not in hosted.text
    assert "a" * 40 not in hosted.text
    assert '"utm_source": "email"' in hosted.text

    assert clean.status_code == 200
    assert '"utm_source": "yandex_direct"' in clean.text
    assert '"utm_campaign": "2026q3_b2c_launch_ru"' in clean.text


def test_public_pages_still_render_without_the_consent_widget_by_default(
    postgres_schema_database_url: str,
) -> None:
    app = create_app(
        Settings(
            database_url=postgres_schema_database_url,
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
        )
    )

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert "analytics.js" not in response.text
    assert "graf-public-analytics-config" not in response.text
