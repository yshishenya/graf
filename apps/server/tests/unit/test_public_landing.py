from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app


def test_public_landing_is_self_serve_entry(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Звоните как привыкли" in response.text
    assert "Запись ведите в GRAF" in response.text
    assert "Включите автозапись для поддерживаемого приложения" in response.text
    assert "без бота в звонке" in response.text
    assert "без привязки к сервису встречи" in response.text
    assert "регистрац" not in response.text.lower()
    assert "Включили один раз — дальше GRAF сам" in response.text
    assert "GRAF сам начнёт запись" in response.text
    assert "GRAF сам завершает запись" in response.text
    assert "reference-auto-flow" in response.text
    assert "Включите автозапись" in response.text
    assert "Звонок закончился" in response.text
    assert "Запустите запись в GRAF" not in response.text
    assert "Подключитесь к звонку как обычно" not in response.text
    assert "От реплики к следующему действию" in response.text
    assert "Расшифровка сохраняет контекст" in response.text
    assert "Краткий итог и следующие действия" in response.text
    assert "данные встречи созданы для демонстрации" in response.text.lower()
    assert "Реальный интерфейс GRAF" in response.text
    assert "Российские и локально развёрнутые модели" in response.text
    assert "ничего за рубеж" not in response.text.lower()
    assert response.text.count('href="/download"') >= 2
    assert "Скачать GRAF" in response.text
    assert 'href="#how"' in response.text
    assert response.text.count('href="/login?next=/meetings"') >= 2
    assert 'href="/sign-up?next=/meetings"' not in response.text
    assert "Как идёт запись" in response.text
    assert "Посмотреть результат" in response.text
    assert response.text.count('data-analytics-cta="hero_product"') == 1
    assert response.text.count('data-analytics-target="section"') >= 1
    assert 'loading="lazy"' in response.text
    assert 'landing-recording-proof-focus.png?v=' in response.text
    assert "Панель активной записи GRAF" in response.text
    assert ">01<" in response.text
    assert ">02<" in response.text
    assert ">03<" not in response.text
    assert ">04<" not in response.text


def test_public_landing_uses_local_static_assets(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "/static/public/landing.css?v=" in response.text
    assert "/static/public/landing-recording-proof-focus.png?v=" in response.text
    assert "/static/public/landing-transcript-proof.png?v=" in response.text
    assert "/static/public/landing-transcript-proof.webp?v=" in response.text
    assert "/static/public/landing-transcript-proof-mobile.png?v=" in response.text
    assert "/static/public/landing-transcript-proof-mobile.webp?v=" in response.text
    assert "/static/public/landing-outcome-proof.png?v=" in response.text
    assert "/static/public/landing-outcome-proof.webp?v=" in response.text
    assert "/static/public/landing-outcome-proof-mobile.png?v=" in response.text
    assert "/static/public/landing-outcome-proof-mobile.webp?v=" in response.text
    assert "/static/cabinet/graf-wordmark-dark@2x.png?v=" in response.text
    assert "/static/cabinet/favicon.ico?v=" in response.text
    assert 'width="1487"' in response.text
    assert 'height="1058"' in response.text
    assert 'width="880"' in response.text
    assert 'height="180"' in response.text
    assert "/static/public/fonts/onest-cyrillic.woff2?v=" in response.text
    assert "/static/public/fonts/onest-latin.woff2?v=" in response.text
    assert "https://rec.2brain.pro/" in response.text


def test_public_landing_accepts_synthetic_utm_visit_without_reflecting_private_values(
    client,
) -> None:
    response = client.get(
        "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
        "&utm_content=customer@example.com"
    )

    assert response.status_code == 200
    assert "Звоните как привыкли" in response.text
    assert "Запись ведите в GRAF" in response.text
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
    assert 'data-analytics-cta="hero_product"' in response.text
    assert 'data-analytics-target="section"' in response.text
    assert 'href="#how"' in response.text
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
    assert "Скачать универсальный установщик GRAF" in response.text
    assert "Для Mac с Apple Silicon или Intel и macOS 14.5 или новее" in response.text
    assert "Доступно" in response.text
    assert "Скоро" in response.text
    assert "Windows" in response.text
    assert "Linux" in response.text
    assert "Developer ID" not in response.text
    assert "нотарифицировано Apple" not in response.text
    assert "Открыть всё равно" not in response.text
    assert "без подписи Developer ID" not in response.text
    assert "/static/public/downloads/graf.pkg?v=" in response.text
    assert response.text.count("/static/public/downloads/graf.pkg?v=") == 1
    assert "graf-local.pkg" not in response.text
    assert "ARM" not in response.text
    assert "Intel-версия" not in response.text
    assert response.text.count('data-platform-status="planned"') == 2
    assert 'data-platform="windows" href=' not in response.text.lower()
    assert 'data-platform="linux" href=' not in response.text.lower()
    assert 'href="/login?next=/meetings"' in response.text


def test_public_pages_do_not_publish_unapproved_price_or_checkout_claims(client) -> None:
    combined = client.get("/").text + client.get("/download").text

    assert "₽" not in combined
    assert "рублей" not in combined.lower()
    assert "цена скоро" not in combined.lower()
    # A legal/footer link may mention tariffs; public pages must not publish
    # an amount or promise an enabled checkout before catalog approval.
    assert 'class="pricing-section"' not in combined
    assert "тарифный" not in combined.lower()
    assert "юkassa" not in combined.lower()
    assert "yookassa" not in combined.lower()
    assert "оплатить" not in combined.lower()


def test_public_legal_pages_are_final_and_available_without_public_analytics_config(client) -> None:
    pages = {
        "/privacy": ("Политика обработки персональных данных", "12 августа"),
        "/cookies": ("Политика cookies", "13 августа"),
        "/terms": ("Условия использования GRAF", "12 августа"),
        "/offer": ("Условия оплаты и возврата", "12 августа"),
        "/analytics-consent": ("Согласие на аналитику", "13 августа"),
    }

    for path, (heading, revision_date) in pages.items():
        response = client.get(path)

        assert response.status_code == 200
        assert heading in response.text
        assert revision_date in response.text
        assert "Рабочая редакция" not in response.text
        assert "Phase 1" not in response.text
        assert "campaign launch" not in response.text
        assert 'href="/privacy"' in response.text
        assert 'href="/cookies"' in response.text
        assert 'href="/terms"' in response.text
        assert 'href="/analytics-consent"' in response.text
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "cookieconsent.umd.js" not in response.text


def test_public_legal_pages_explain_missing_cookie_controls_when_analytics_is_disabled(client) -> None:
    cookies = client.get("/cookies")
    consent = client.get("/analytics-consent")

    for response in (cookies, consent):
        assert response.status_code == 200
        copy = " ".join(response.text.split())
        assert "главной странице или странице скачивания" in copy
        assert "Если кнопки нет" in copy
        assert "необязательная публичная аналитика отключена" in copy

    assert "Редакция 2026-08-13.1 от 13 августа 2026 года" in " ".join(
        consent.text.split()
    )


def test_public_privacy_notice_covers_operator_product_and_current_processors(client) -> None:
    response = client.get("/privacy")

    assert response.status_code == 200
    for required in (
        "предприниматель Шишеня Ян Александрович",
        "ИНН 667803118920",
        "ОГРНИП 320665800036109",
        "записи встреч",
        "расшифровки",
        "Langfuse Cloud EU",
        "Ирланд",
        "LiteLLM",
        "Temporal",
        "MediaScribe",
        "трансгранич",
        "yan@shishenya.ru",
    ):
        assert required in response.text
    assert "всё остаётся в России" not in response.text
    assert "полное удаление у всех поставщиков" not in response.text


def test_public_terms_put_recording_lawfulness_on_the_recording_user(client) -> None:
    response = client.get("/terms")

    assert response.status_code == 200
    assert "законное основание" in response.text
    assert "проинформировать участников о записи" in response.text
    assert "охраняемой законом" in response.text


def test_public_payment_conditions_do_not_pretend_checkout_is_active(client) -> None:
    response = client.get("/offer")

    assert response.status_code == 200
    assert "Условия оплаты и возврата" in response.text
    assert "платная подписка сейчас не продаётся" in response.text.lower()
    assert "платное предложение возникает только когда интерфейс оплаты" in response.text.lower()
    assert "полная цена в рублях" in response.text.lower()
    assert "Публичная оферта GRAF" not in response.text


def test_public_download_analytics_attributes_do_not_change_handoff_destinations(client) -> None:
    response = client.get("/download")

    assert response.status_code == 200
    assert 'href="/login?next=/meetings"' in response.text
    assert 'data-analytics-cta="download_page_login"' in response.text
    assert 'data-analytics-target="login"' in response.text
    assert "/static/public/downloads/graf.pkg?v=" in response.text
    assert "download" in response.text
    assert 'data-analytics-cta="download_page_installer"' in response.text
    assert 'data-analytics-target="installer_package"' in response.text
