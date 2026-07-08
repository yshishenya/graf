from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import (
    COOKIECONSENT_VERSION,
    PUBLIC_ANALYTICS_CONSENT_CATEGORIES,
    build_public_analytics_context,
    normalize_public_campaign_attribution,
    public_analytics_event_names,
    public_analytics_stable_labels,
    public_analytics_utm_fields,
)


def test_public_analytics_is_disabled_by_default() -> None:
    context = build_public_analytics_context(Settings(), "/")

    assert context["enabled"] is False
    assert context["provider"] == "yandex_metrica"
    assert context["yandex_metrica_id"] is None
    assert context["yandex_metrica_id_present"] is False
    assert context["replay_allowed"] is False
    assert context["cookieconsent_version"] == COOKIECONSENT_VERSION


def test_public_analytics_render_only_context_is_safe_and_public_scoped() -> None:
    settings = Settings(
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
        public_analytics_replay_enabled=True,
    )

    context = build_public_analytics_context(settings, "/download")

    assert context["enabled"] is True
    assert context["validation_mode"] == "render_only"
    assert context["environment_allowed"] is True
    assert context["page_path"] == "/download"
    assert context["surface"] == "public_download"
    assert context["yandex_metrica_id"] == "YA_TEST_COUNTER"
    assert context["replay_allowed"] is True
    assert context["consent_categories"] == list(PUBLIC_ANALYTICS_CONSENT_CATEGORIES)
    assert public_analytics_event_names() == (
        "public_landing_viewed",
        "public_landing_section_seen",
        "public_landing_cta_clicked",
        "public_download_viewed",
        "public_installer_download_clicked",
        "public_login_intent_clicked",
    )
    assert context["stable_labels"] == {
        key: list(values) for key, values in public_analytics_stable_labels().items()
    }


def test_public_analytics_event_catalog_has_stable_labels() -> None:
    labels = public_analytics_stable_labels()

    assert public_analytics_event_names() == (
        "public_landing_viewed",
        "public_landing_section_seen",
        "public_landing_cta_clicked",
        "public_download_viewed",
        "public_installer_download_clicked",
        "public_login_intent_clicked",
    )
    assert labels["section_id"] == ("hero", "platforms", "outcomes", "trust", "final_cta")
    assert labels["cta_location"] == (
        "header_download",
        "hero_download",
        "final_download",
        "hero_login",
        "final_login",
        "download_page_installer",
        "download_page_login",
    )
    assert labels["target_kind"] == (
        "download_page",
        "installer_package",
        "login",
        "section",
    )


def test_public_analytics_stays_disabled_outside_public_scope() -> None:
    settings = Settings(
        env="staging",
        public_analytics_enabled=True,
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
        public_analytics_replay_enabled=True,
    )

    context = build_public_analytics_context(settings, "/login")

    assert context["enabled"] is False
    assert context["page_path"] is None
    assert context["surface"] is None
    assert context["yandex_metrica_id"] is None
    assert context["replay_allowed"] is False


def test_public_analytics_requires_production_or_explicit_validation_mode() -> None:
    settings = Settings(
        env="development",
        public_analytics_enabled=True,
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
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
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_id",
        "utm_content",
        "utm_term",
    )
    assert attribution["utm_source"] == "yandex_direct"
    assert attribution["utm_medium"] == "cpc"
    assert attribution["utm_campaign"] == "2026q3_b2c_launch_ru"
    assert attribution["utm_id"] == "campaign-42"
    assert attribution["utm_content"] == "hero_a"
    assert attribution["utm_term"] == "meeting_recorder"
    assert attribution["referrer_category"] == "paid"
    assert attribution["landing_path"] == "/"
    assert attribution["normalization_status"] == "normalized"
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

    assert attribution["utm_source"] == "email"
    assert attribution["utm_medium"] == "cpc"
    assert attribution["utm_campaign"] is None
    assert attribution["utm_content"] is None
    assert attribution["utm_term"] is None
    assert attribution["referrer_category"] == "paid"
    assert attribution["landing_path"] == "/download"
    assert attribution["normalization_status"] == "unsafe_dropped"


def test_public_analytics_referrer_categories_cover_direct_referral_organic_and_unknown() -> None:
    assert normalize_public_campaign_attribution({}, landing_path="/")["referrer_category"] == "direct"
    assert (
        normalize_public_campaign_attribution({}, referrer="https://partner.example/page", landing_path="/")[
            "referrer_category"
        ]
        == "referral"
    )
    assert (
        normalize_public_campaign_attribution({}, referrer="https://yandex.ru/search/?text=graf", landing_path="/")[
            "referrer_category"
        ]
        == "organic"
    )
    assert normalize_public_campaign_attribution({}, referrer="not a url", landing_path="/")["referrer_category"] == "unknown"
