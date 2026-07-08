from pydantic import ValidationError

from twobrain_rec_server.config import Settings
from twobrain_rec_server.public.analytics import (
    COOKIECONSENT_VERSION,
    PUBLIC_ANALYTICS_CONSENT_CATEGORIES,
    build_public_analytics_context,
    public_analytics_event_names,
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
