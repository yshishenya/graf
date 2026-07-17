from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_public_landing_is_self_serve_entry(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Встреча останется с вами" in response.text
    assert "GRAF сам записывает звонок" in response.text
    assert "регистрац" not in response.text.lower()
    assert "Любой сервис для созвонов" in response.text
    assert "GRAF записывает встречу там, где вы уже созваниваетесь" in response.text
    assert "GRAF REC" not in response.text
    assert "Примеры поддерживаемых платформ" not in response.text
    assert "Яндекс Телемост" in response.text
    assert "SberJazz" in response.text
    assert "TrueConf" in response.text
    assert "МТС Линк" in response.text
    assert "Контур.Толк" in response.text
    assert "DION" in response.text
    assert "Без бота в звонке" in response.text
    assert "через минуты" not in response.text
    assert "Транскрипт" in response.text
    assert "Запуск в Q3" in response.text
    assert response.text.count('href="/download"') >= 2
    assert "Скачать GRAF" in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 2
    assert 'href="/sign-up?next=/meetings"' not in response.text
    assert "Посмотреть" not in response.text
    assert "демо" not in response.text
    assert "пилот" not in response.text
    assert ">01<" not in response.text
    assert ">02<" not in response.text
    assert ">03<" not in response.text
    assert ">04<" not in response.text


def test_public_landing_uses_local_static_assets(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "/static/public/landing.css?v=" in response.text
    assert "/static/public/landing-hero-product.png?v=" in response.text
    assert "/static/cabinet/favicon.ico?v=" in response.text
    assert 'width="940"' in response.text
    assert 'height="710"' in response.text
    assert "landing-tools-strip.png" not in response.text
    assert "https://" not in response.text


def test_public_landing_accepts_synthetic_utm_visit_without_reflecting_private_values(client) -> None:
    response = client.get(
        "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
        "&utm_content=customer@example.com"
    )

    assert response.status_code == 200
    assert "Встреча останется с вами" in response.text
    assert response.text.count('href="/download"') >= 2
    assert "customer@example.com" not in response.text
    assert "graf-public-analytics-config" not in response.text


def test_public_landing_footer_links_to_legal_pages_without_analytics_by_default(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'aria-label="Юридическая информация"' in response.text
    assert 'href="/privacy"' in response.text
    assert 'href="/cookies"' in response.text
    assert 'href="/terms"' in response.text
    assert 'href="/analytics-consent"' in response.text
    assert 'data-cc="show-preferencesModal"' not in response.text


def test_public_landing_render_only_consent_markup_is_accessible_and_category_scoped(
    postgres_test_database_url: str,
) -> None:
    settings = Settings(
        database_url=postgres_test_database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
        public_analytics_replay_enabled=True,
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert '<a class="skip-link" href="#main">' in response.text
    assert 'type="button" data-cc="show-preferencesModal"' in response.text
    assert 'href="/privacy"' in response.text
    assert 'href="/cookies"' in response.text
    assert 'href="/terms"' in response.text
    assert 'href="/analytics-consent"' in response.text
    assert (
        '"consent_categories": ["necessary", "analytics", "advertising_attribution", "behavior_replay"]'
        in response.text
    )
    assert (
        '"consent_states": ["unknown", "accepted_all", "necessary_only", "customized", "revoked"]'
        in response.text
    )


def test_public_landing_analytics_attributes_do_not_change_cta_destinations(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.text.count('href="/download"') >= 3
    assert response.text.count('data-analytics-target="download_page"') == 3
    assert 'href="/download"' in response.text
    assert 'data-analytics-cta="header_download"' in response.text
    assert 'data-analytics-cta="hero_download"' in response.text
    assert 'data-analytics-cta="final_download"' in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 2
    assert response.text.count('data-analytics-target="login"') == 2
    assert 'data-analytics-cta="hero_login"' in response.text
    assert 'data-analytics-cta="final_login"' in response.text
    assert 'data-analytics-section="hero"' in response.text
    assert 'data-analytics-section="platforms"' in response.text
    assert 'data-analytics-section="outcomes"' in response.text
    assert 'data-analytics-section="trust"' in response.text
    assert 'data-analytics-section="final_cta"' in response.text


def test_public_landing_has_keyboard_entry_points(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert '<a class="skip-link" href="#main">' in response.text
    assert '<main id="main">' in response.text


def test_public_download_handoff_is_available(client) -> None:
    response = client.get("/download")

    assert response.status_code == 200
    assert "Установите GRAF" in response.text
    assert "Скачать GRAF" in response.text
    assert "Текущий установщик" in response.text
    assert "Скачайте пакет и откройте GRAF." in response.text
    assert "/static/public/downloads/graf-local.pkg?v=" in response.text
    assert "Как только установщик будет готов" not in response.text
    assert 'href="/login?next=/meetings"' in response.text


def test_public_legal_pages_are_available_without_public_analytics_config(client) -> None:
    pages = {
        "/privacy": "Политика конфиденциальности",
        "/cookies": "Политика cookies",
        "/terms": "Условия публичного сайта",
        "/analytics-consent": "Согласие на аналитику",
    }

    for path, heading in pages.items():
        response = client.get(path)

        assert response.status_code == 200
        assert heading in response.text
        assert "Рабочая редакция" in response.text or "Редакция:" in response.text
        assert 'href="/privacy"' in response.text
        assert 'href="/cookies"' in response.text
        assert 'href="/terms"' in response.text
        assert 'href="/analytics-consent"' in response.text
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "cookieconsent.umd.js" not in response.text


def test_public_download_analytics_attributes_do_not_change_handoff_destinations(client) -> None:
    response = client.get("/download")

    assert response.status_code == 200
    assert 'href="/login?next=/meetings"' in response.text
    assert 'data-analytics-cta="download_page_login"' in response.text
    assert 'data-analytics-target="login"' in response.text
    assert "/static/public/downloads/graf-local.pkg?v=" in response.text
    assert "download" in response.text
    assert 'data-analytics-cta="download_page_installer"' in response.text
    assert 'data-analytics-target="installer_package"' in response.text
