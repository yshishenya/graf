from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_public_landing_is_self_serve_entry(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Встреча закончится" in response.text
    assert "Главное останется" in response.text
    assert "GRAF записывает встречу без бота в звонке" in response.text
    assert "регистрац" not in response.text.lower()
    assert "Настройте один раз. Встречи запишутся сами" in response.text
    assert "GRAF распознаёт её и запускает запись" in response.text
    assert "79" in response.text
    assert "приложений в текущем" in response.text
    assert "Сервис встречи не диктует сценарий" in response.text
    assert "Любой сервис для созвонов" not in response.text
    assert "всех приложениях" not in response.text.lower()
    assert "GRAF REC" not in response.text
    assert "Yandex Telemost" in response.text
    assert "Zoom" in response.text
    assert "TrueConf" in response.text
    assert "MTS Link" in response.text
    assert "Kontur Talk" in response.text
    assert "Dion" in response.text
    assert "Google Meet и другие браузерные встречи" in response.text
    assert "с ручным запуском записи" in response.text
    assert "Контекст из календаря" in response.text
    assert "Автозапуск остаётся привязан к выбранным приложениям" in response.text
    assert "SberJazz" not in response.text
    assert "через минуты" not in response.text
    assert "Не протокол. Готовый план действий" in response.text
    assert "Запустить двухнедельный пилот в понедельник" in response.text
    assert "Продажи готовят список участников и календарь встреч" in response.text
    assert "Ручной старт и остановка всегда остаются доступны" in response.text
    assert "Как работает автозапись" not in response.text
    assert "данные встречи созданы для демонстрации" in response.text.lower()
    assert "Российские и локальные модели" in response.text
    assert "ничего за рубеж" not in response.text.lower()
    assert response.text.count('href="/download"') >= 2
    assert "Скачать GRAF" in response.text
    assert 'href="#how"' in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 2
    assert 'href="/sign-up?next=/meetings"' not in response.text
    assert "Посмотреть продукт" in response.text
    assert 'role="group"' in response.text
    assert 'aria-label="Два экрана одной демонстрационной встречи: расшифровка и итоги"' in response.text
    assert 'class="hero-proof-panel hero-proof-panel-transcript"' in response.text
    assert 'class="hero-proof-panel hero-proof-panel-outcome"' in response.text
    assert 'class="hero-proof-progress"' in response.text
    assert 'hero-proof-input' not in response.text
    assert ">01<" in response.text
    assert ">02<" in response.text
    assert ">03<" in response.text
    assert ">04<" not in response.text


def test_public_landing_uses_local_static_assets(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "/static/public/landing.css?v=" in response.text
    assert "/static/public/landing-autorecord-proof-focus.png?v=" in response.text
    assert "/static/public/landing-autorecord-proof-control-mobile.png?v=" in response.text
    assert "/static/public/landing-autorecord-proof-toggle-mobile.png?v=" in response.text
    assert "/static/public/landing-recording-proof.png?v=" not in response.text
    assert "/static/public/landing-recording-proof-focus.png?v=" not in response.text
    assert "/static/public/landing-transcript-proof.png?v=" in response.text
    assert "/static/public/landing-transcript-proof-mobile.png?v=" not in response.text
    assert "/static/public/landing-outcome-proof.png?v=" in response.text
    assert "/static/public/landing-outcome-proof-mobile.png?v=" in response.text
    assert "/static/public/landing-outcome-proof-focus.png?v=" not in response.text
    assert "/static/public/landing-hero-product.png?v=" not in response.text
    assert "/static/cabinet/graf-wordmark-dark@2x.png?v=" in response.text
    assert "/static/cabinet/favicon.ico?v=" in response.text
    assert 'width="1487"' in response.text
    assert 'height="1058"' in response.text
    assert 'width="3040"' in response.text
    assert 'height="2000"' in response.text
    assert "/static/public/fonts/onest-cyrillic.woff2?v=" in response.text
    assert "/static/public/fonts/onest-latin.woff2?v=" in response.text
    assert "https://" not in response.text


def test_public_landing_accepts_synthetic_utm_visit_without_reflecting_private_values(
    client,
) -> None:
    response = client.get(
        "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
        "&utm_content=customer@example.com"
    )

    assert response.status_code == 200
    assert "Встреча закончится" in response.text
    assert "Главное останется" in response.text
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
    postgres_worker_database_url: str,
) -> None:
    settings = Settings(
        database_url=postgres_worker_database_url,
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
    assert 'data-analytics-cta="hero_login"' in response.text
    assert 'data-analytics-target="login"' in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 1
    assert response.text.count('data-analytics-target="login"') >= 1
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
    assert "Скачать GRAF" in response.text
    assert "Скачать для macOS" in response.text
    assert "Подписано разработчиком и проверено Apple" in response.text
    assert "Доступно" in response.text
    assert "Скоро" in response.text
    assert "Windows" in response.text
    assert "Linux" in response.text
    assert "Developer ID" not in response.text
    assert "нотарифицировано Apple" not in response.text
    assert "Открыть всё равно" not in response.text
    assert "без подписи Developer ID" not in response.text
    assert "/static/public/downloads/graf-local.pkg?v=" in response.text
    assert response.text.count('data-platform-status="planned"') == 2
    assert 'data-platform="windows" href=' not in response.text.lower()
    assert 'data-platform="linux" href=' not in response.text.lower()
    assert 'href="/login?next=/meetings"' in response.text


def test_public_pages_do_not_publish_unapproved_price_or_checkout_claims(client) -> None:
    combined = client.get("/").text + client.get("/download").text

    assert "₽" not in combined
    assert "рублей" not in combined.lower()
    assert "цена скоро" not in combined.lower()
    assert "тарифы" not in combined.lower()
    assert "тарифный" not in combined.lower()
    assert "юkassa" not in combined.lower()
    assert "yookassa" not in combined.lower()
    assert "оплатить" not in combined.lower()


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
