from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import (
    PUBLIC_ANALYTICS_EVENT_CATALOG,
    PUBLIC_ANALYTICS_TARGET_KINDS,
    build_public_analytics_context,
    normalize_public_analytics_consent,
    normalize_public_campaign_attribution,
    public_analytics_consent_revision,
    public_analytics_event_names,
    public_analytics_stable_labels,
    public_analytics_utm_fields,
)


def test_public_analytics_is_disabled_by_default() -> None:
    context = build_public_analytics_context(Settings(), "/")

    assert context["enabled"] is False
    assert context["provider"] == "yandex_metrica"
    assert context["yandex_metrica_id"] is None
    assert context["replay_allowed"] is False


def test_public_analytics_immediate_context_is_narrow_and_public_scoped() -> None:
    settings = Settings(
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_replay_enabled=True,
    )

    context = build_public_analytics_context(settings, "/download")

    assert context["enabled"] is True
    assert context["validation_mode"] == "render_only"
    assert context["page_path"] == "/download"
    assert context["surface"] == "public_download"
    assert context["yandex_metrica_id"] == "12345678"
    assert context["replay_allowed"] is True
    assert context["event_catalog"]


def test_public_consent_categories_are_strict_and_unknown_is_fail_closed() -> None:
    valid = {
        "copy_version": "2026-09-15.1",
        "categories": ["necessary", "analytics"],
        "state": "customized",
    }

    assert normalize_public_analytics_consent(valid)["state"] == "customized"
    assert normalize_public_analytics_consent(
        {**valid, "categories": ["necessary", "analytics", "unknown"]}
    )["state"] == "unknown"
    assert normalize_public_analytics_consent(
        {**valid, "copy_version": "2026-08-21.1"}
    )["state"] == "unknown"
    assert normalize_public_analytics_consent(
        {**valid, "categories": ["analytics"]}
    )["state"] == "unknown"
    assert normalize_public_analytics_consent(None)["state"] == "unknown"


def test_public_consent_states_include_acceptance_and_revoke_transitions() -> None:
    base = {"copy_version": "2026-09-15.1"}

    assert normalize_public_analytics_consent(
        {**base, "categories": ["necessary", "analytics", "advertising_attribution", "behavior_replay"]}
    )["state"] == "accepted_all"
    assert normalize_public_analytics_consent(
        {**base, "categories": ["necessary"]}
    )["state"] == "necessary_only"
    assert normalize_public_analytics_consent(
        {**base, "categories": ["necessary"], "state": "revoked"},
        previous={**base, "categories": ["necessary", "analytics"]},
    )["state"] == "revoked"


def test_public_analytics_consent_revision_follows_copy_version() -> None:
    assert public_analytics_consent_revision("2026-09-20.7") == 202609207

    settings = Settings(
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_consent_copy_version="2026-09-20.7",
    )
    context = build_public_analytics_context(settings, "/")

    assert context["consent_copy_version"] == "2026-09-20.7"
    assert context["consent_revision"] == 202609207


def test_public_analytics_event_catalog_and_labels_match_new_funnel() -> None:
    assert public_analytics_event_names() == (
        "public_landing_viewed",
        "public_landing_section_seen",
        "public_landing_cta_clicked",
        "public_download_viewed",
        "public_signup_viewed",
        "public_login_viewed",
        "public_installer_download_clicked",
        "public_login_intent_clicked",
        "public_product_tab_selected",
        "public_pricing_cycle_selected",
        "public_faq_opened",
    )
    assert public_analytics_stable_labels() == {
        "section_id": ("hero", "audience", "workflow", "pricing", "faq", "final_cta"),
        "cta_location": (
            "header_download",
            "hero_download",
            "pricing_download",
            "final_download",
            "header_login",
            "final_login",
            "download_page_installer",
            "download_page_login",
        ),
        "target_kind": ("download_page", "installer_package", "login", "section"),
        "product_tab": ("recording", "transcript", "outcomes"),
        "pricing_cycle": ("month", "year"),
        "faq_item": (
            "google_calendar",
            "recognition",
            "calling_apps",
            "upload",
            "results",
            "platforms",
            "offline",
            "storage",
        ),
    }
    assert all(
        item["target_kind"] in PUBLIC_ANALYTICS_TARGET_KINDS
        for item in PUBLIC_ANALYTICS_EVENT_CATALOG
        if item["target_kind"]
    )


def test_public_analytics_covers_the_auth_pages_and_stays_disabled_outside_public_scope() -> None:
    """FR-027: sign-up and login are public pages, so consent covers them too."""
    settings = Settings(
        env="staging",
        public_analytics_enabled=True,
        public_analytics_yandex_metrica_id="12345678",
    )

    for path, surface in (("/login", "public_login"), ("/sign-up", "public_signup")):
        context = build_public_analytics_context(settings, path)

        assert context["enabled"] is True, path
        assert context["consent_ui_enabled"] is True, path
        assert context["page_path"] == path
        assert context["surface"] == surface
        # The pages carry a credential form, so the external counter stays off
        # them and only the first-party relay may carry a consented event.
        assert context["external_counter_allowed"] is False, path
        assert context["external_counter_scope"] == ["public_landing", "public_download"]
        assert context["replay_allowed"] is False, path
        assert context["webvisor_allowed"] is False, path
        assert context["click_map_allowed"] is False, path
        assert context["scroll_map_allowed"] is False, path
        assert context["form_analytics_allowed"] is False, path

    private = build_public_analytics_context(settings, "/cabinet")

    assert private["enabled"] is False
    assert private["consent_ui_enabled"] is False
    assert private["page_path"] is None
    assert private["surface"] is None
    assert private["yandex_metrica_id"] is None
    assert private["external_counter_allowed"] is False


def test_public_analytics_requires_production_or_explicit_validation_mode() -> None:
    settings = Settings(
        env="development",
        public_analytics_enabled=True,
        public_analytics_yandex_metrica_id="12345678",
    )

    context = build_public_analytics_context(settings, "/")

    assert context["enabled"] is False
    assert context["environment_allowed"] is False
    assert context["yandex_metrica_id_present"] is True


def test_public_analytics_validation_mode_rejects_unknown_values() -> None:
    try:
        Settings(public_analytics_validation_mode="live")
    except ValidationError as exc:
        assert "public_analytics_validation_mode" in str(exc)
    else:
        raise AssertionError("unknown public analytics validation mode was accepted")


def test_public_analytics_utm_fields_are_allowlisted_and_normalized() -> None:
    attribution = normalize_public_campaign_attribution(
        {
            "utm_source": "Yandex_Direct",
            "utm_medium": "CPC",
            "utm_campaign": "2026q3_b2c_launch_ru",
            "utm_id": "campaign-42",
            "utm_content": "hero_a",
            "utm_term": "meeting_recorder",
            "ignored": "not-sent",
        },
        landing_path="/",
    )

    assert public_analytics_utm_fields() == (
        "utm_source", "utm_medium", "utm_campaign", "utm_id", "utm_content", "utm_term"
    )
    assert attribution["utm_source"] == "yandex_direct"
    assert attribution["utm_medium"] == "cpc"
    assert attribution["referrer_category"] == "paid"
    assert attribution["landing_path"] == "/"
    assert "ignored" not in attribution


def test_public_analytics_unsafe_campaign_values_are_dropped() -> None:
    attribution = normalize_public_campaign_attribution(
        {
            "utm_source": "Email",
            "utm_medium": "CPC",
            "utm_campaign": "customer@example.com",
            "utm_content": "https://private.example/signed?token=abc",
            "utm_term": "+7 999 111 22 33",
        },
        landing_path="/download",
    )

    assert attribution["utm_campaign"] is None
    assert attribution["utm_content"] is None
    assert attribution["utm_term"] is None
    assert attribution["normalization_status"] == "unsafe_dropped"


def test_public_analytics_production_config_accepts_numeric_yandex_counter() -> None:
    settings = _production_public_analytics_settings(
        public_analytics_enabled=True,
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_validation_mode="provider_smoke",
        public_analytics_replay_enabled=True,
    )

    assert settings.public_analytics_enabled is True
    assert settings.public_analytics_yandex_metrica_id == "12345678"
    assert settings.public_analytics_validation_mode == "provider_smoke"
    assert settings.public_analytics_replay_enabled is True


def test_public_analytics_production_config_rejects_placeholder_counter_ids() -> None:
    for counter_id in (None, "YA_TEST_COUNTER", "replace-me", "G-123456", "123abc"):
        try:
            _production_public_analytics_settings(
                public_analytics_enabled=True,
                public_analytics_yandex_metrica_id=counter_id,
            )
        except ValidationError as exc:
            assert "public_analytics_yandex_metrica_id" in str(exc)
        else:
            raise AssertionError(f"invalid analytics counter was accepted: {counter_id!r}")


def _production_public_analytics_settings(**overrides: object) -> Settings:
    values = {
        "env": "production",
        "database_url": "postgresql+asyncpg://twobrain_rec:secret@rec-postgres:5432/twobrain_rec",
        "minio_endpoint": "rec-minio:9000",
        "minio_access_key": "twobrain_rec_api",
        "minio_secret_key": "prod-api-secret",
        "minio_bucket": "twobrain-rec-ingest",
        "web_csrf_secret": "prod-web-csrf-secret-32-bytes-minimum",
        "auth_ru_local_storage_attested": True,
        "playback_normalization_enabled": True,
        "temporal_address": "rec-temporal:7233",
    }
    values.update(overrides)
    return Settings(**values)
