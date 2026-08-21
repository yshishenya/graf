import json
from datetime import UTC, datetime, timedelta
from html.parser import HTMLParser

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.billing.launch_gates import MANDATORY_BILLING_LAUNCH_GATES, shop_id_hash
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import BillingLaunchGate, BillingPlanVersion
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.offers import PublicOfferView, build_public_offer_view
from twobrain_rec_server.public.templates import render_template


class _OfferDb:
    def __init__(self, catalog_rows, gate_rows):
        self._results = iter((catalog_rows, gate_rows))

    async def scalars(self, _query):
        return next(self._results)


class _UnavailableOfferDb:
    async def scalars(self, _query):
        raise OSError("catalog database unavailable")


class _StructuredDataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.documents: list[str] = []
        self._capture = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "script" and dict(attrs).get("type") == "application/ld+json":
            self._capture = True
            self.documents.append("")

    def handle_data(self, data: str) -> None:
        if self._capture:
            self.documents[-1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._capture:
            self._capture = False


def _public_catalog_rows(*, annual_amount_minor: int = 1_000_000):
    common = {
        "plan_code": "personal",
        "version": 1,
        "currency": "RUB",
        "storage_bytes": 2_000_000_000,
        "processing_mode": "unlimited",
        "enabled_for_checkout": True,
        "policy_snapshot": {"offer_version": "personal-2026-08-21"},
        "effective_from": datetime(2026, 8, 1, tzinfo=UTC),
    }
    return [
        BillingPlanVersion(cycle="month", amount_minor=100_000, **common),
        BillingPlanVersion(cycle="year", amount_minor=annual_amount_minor, **common),
    ]


def _public_gate_rows(now: datetime, sha: str):
    return [
        BillingLaunchGate(
            environment="production",
            shop_id_hash=shop_id_hash("shop-1"),
            deployment_sha=sha,
            gate_key=key,
            version=1,
            status="approved",
            evidence_ref=f"evidence:{key}",
            owner_role=key,
            approver_ref=f"approver:{key}",
            executor_ref="release:operator",
            values_json={
                "provider_correction": {
                    "threshold_minor": 0,
                    "approver_role": "finance",
                    "executor_role": "billing_operator",
                },
                "off_provider_correction": {
                    "threshold_minor": 0,
                    "approver_role": "finance",
                    "executor_role": "billing_operator",
                },
            },
            approved_at=now - timedelta(minutes=1),
            valid_until=now + timedelta(days=1),
        )
        for key in MANDATORY_BILLING_LAUNCH_GATES
    ]


@pytest.mark.anyio
async def test_public_offer_uses_exact_catalog_and_launch_gates() -> None:
    now = datetime(2026, 8, 21, tzinfo=UTC)
    sha = "a" * 40
    settings = Settings.model_construct(
        billing_checkout_enabled=True,
        billing_emergency_stop=False,
        billing_yookassa_environment="production",
        billing_yookassa_shop_id="shop-1",
        langfuse_release=sha,
    )

    offer = await build_public_offer_view(
        _OfferDb(_public_catalog_rows(), _public_gate_rows(now, sha)),
        settings,
        now=now,
    )

    assert offer.sale_ready is True
    assert offer.monthly_label == "1 000 ₽"
    assert offer.annual_label == "10 000 ₽"
    assert offer.annual_saving_label == "2 000 ₽"
    assert offer.trial_days == 7


@pytest.mark.anyio
async def test_public_offer_fails_closed_for_wrong_price() -> None:
    settings = Settings.model_construct(billing_checkout_enabled=True)
    offer = await build_public_offer_view(
        _OfferDb(_public_catalog_rows(annual_amount_minor=999_000), []),
        settings,
        now=datetime(2026, 8, 21, tzinfo=UTC),
    )

    assert offer.catalog_ready is False
    assert offer.sale_ready is False


@pytest.mark.anyio
async def test_public_offer_keeps_landing_available_when_catalog_database_is_down() -> None:
    offer = await build_public_offer_view(
        _UnavailableOfferDb(),
        Settings.model_construct(billing_checkout_enabled=True),
    )

    assert offer.catalog_ready is False
    assert offer.sale_ready is False


def test_public_landing_explains_product_and_download_path(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    for copy in (
        "Записывайте звонки",
        "в любом приложении",
        "Без ботов",
        "Без VPN",
        "Расшифровка по спикерам и итоги",
        "Много встреч",
        "Важно не упустить главное",
        "Собственники и руководители",
        "Фрилансеры и консультанты",
        "Продажи, HR, проекты и продукты",
        "ГРАФ встраивается",
        "Итоги и действия",
        "Будьте в разговоре",
    ):
        assert copy in response.text
    assert response.text.count('href="/download"') >= 3
    assert 'href="/login?next=/meetings"' in response.text
    assert 'href="#how"' in response.text
    assert '<main id="main">' in response.text
    assert 'role="tablist"' in response.text
    assert response.text.count('role="tabpanel"') == 3
    assert 'data-panel="transcript" hidden' not in response.text
    assert 'data-panel="outcomes" hidden' not in response.text


def test_public_landing_uses_fingerprinted_local_assets(client) -> None:
    response = client.get("/")

    for asset in (
        "landing.css",
        "landing.js",
        "graf-recording-landing.png",
        "graf-transcript-landing.png",
        "graf-transcript-landing-mobile.png",
        "graf-summary-landing.png",
        "fonts/onest-cyrillic.woff2",
        "fonts/onest-latin.woff2",
    ):
        assert f"/static/public/{asset}?v=" in response.text
    assert "assets/screenshots" not in response.text
    assert "styles.css" not in response.text
    assert "script.js" not in response.text


def test_public_landing_price_is_fail_closed_without_catalog(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert 'id="price"' not in response.text
    assert "10 000 ₽" not in response.text
    assert "1 000 ₽" not in response.text


def test_sale_ready_template_renders_exact_price_and_annual_saving() -> None:
    offer = PublicOfferView(
        catalog_ready=True,
        sale_ready=True,
        monthly_amount_minor=100_000,
        annual_amount_minor=1_000_000,
        monthly_label="1 000 ₽",
        annual_label="10 000 ₽",
        annual_saving_minor=200_000,
        annual_saving_label="2 000 ₽",
        offer_version="personal-2026-08-21",
    )
    html = render_template(
        "public/landing.html",
        page_title="ГРАФ",
        canonical_url="https://rec.2brain.pro/",
        social_title="ГРАФ",
        social_description="ГРАФ",
        public_offer=offer,
        public_analytics={"enabled": False},
    )

    assert 'id="price"' in html
    assert "1 000 ₽" in html
    assert "10 000 ₽" in html
    assert "2 000 ₽ экономии" in html
    assert "−20%" not in html

    parser = _StructuredDataParser()
    parser.feed(html)
    structured_data = [json.loads(document) for document in parser.documents]
    software = next(document for document in structured_data if document["@type"] == "SoftwareApplication")
    assert software["downloadUrl"] == "https://rec.2brain.pro/download"
    assert [offer["price"] for offer in software["offers"]] == ["1000", "10000"]


def test_catalog_ready_template_publishes_tariff_before_payment_is_enabled() -> None:
    offer = PublicOfferView(
        catalog_ready=True,
        sale_ready=False,
        monthly_amount_minor=100_000,
        annual_amount_minor=1_000_000,
        monthly_label="1 000 ₽",
        annual_label="10 000 ₽",
        annual_saving_minor=200_000,
        annual_saving_label="2 000 ₽",
        offer_version="personal-2026-08-21",
    )
    html = render_template(
        "public/landing.html",
        page_title="ГРАФ",
        canonical_url="https://rec.2brain.pro/",
        social_title="ГРАФ",
        social_description="ГРАФ",
        public_offer=offer,
        public_analytics={"enabled": False},
    )

    assert 'id="price"' in html
    assert "1 000 ₽" in html
    assert "10 000 ₽" in html
    assert "Оплата откроется" in html

    parser = _StructuredDataParser()
    parser.feed(html)
    structured_data = [json.loads(document) for document in parser.documents]
    software = next(document for document in structured_data if document["@type"] == "SoftwareApplication")
    assert "offers" not in software


def test_public_landing_sanitizes_unsafe_utm_values(client) -> None:
    response = client.get(
        "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
        "&utm_content=customer@example.com"
    )

    assert response.status_code == 200
    assert "customer@example.com" not in response.text


def test_public_landing_immediate_analytics_has_no_consent_widget(
    postgres_worker_database_url: str,
) -> None:
    settings = Settings(
        database_url=postgres_worker_database_url,
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="12345678",
        public_analytics_replay_enabled=True,
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        response = test_client.get("/")

    assert response.status_code == 200
    assert "graf-public-analytics-config" in response.text
    assert "analytics.js?v=" in response.text
    assert "cookieconsent.umd.js" not in response.text
    assert "cookieconsent.css" not in response.text
    assert "show-preferencesModal" not in response.text
    assert '"replay_allowed": false' in response.text


def test_public_download_handoff_is_available(client) -> None:
    response = client.get("/download")

    assert response.status_code == 200
    assert "Скачать ГРАФ" in response.text
    assert "Скачать универсальный установщик ГРАФ" in response.text
    assert "Apple Silicon или Intel" in response.text
    assert "macOS 14.5 или новее" in response.text
    assert response.text.count("/static/public/downloads/graf.pkg?v=") == 1
    assert response.text.count('data-platform-status="planned"') == 2
    assert 'data-platform="windows" href=' not in response.text.lower()
    assert 'data-platform="linux" href=' not in response.text.lower()


def test_public_legal_and_discovery_routes_are_available(client) -> None:
    pages = {
        "/privacy": "Политика обработки персональных данных",
        "/cookies": "Политика cookies",
        "/terms": "Условия использования ГРАФ",
        "/offer": "Условия оплаты и возврата",
        "/analytics-consent": "Как ГРАФ использует аналитику",
    }
    for path, heading in pages.items():
        response = client.get(path)
        assert response.status_code == 200
        assert heading in response.text
        assert 'href="/privacy"' in response.text
        assert 'href="/cookies"' in response.text
        assert 'href="/terms"' in response.text
        assert 'href="/offer"' in response.text
        assert 'href="/analytics-consent"' in response.text
        assert "graf-public-analytics-config" not in response.text

    sitemap = client.get("/sitemap.xml")
    assert sitemap.status_code == 200
    assert "https://rec.2brain.pro/offer" in sitemap.text


def test_public_legal_copy_matches_product_and_analytics_truth(client) -> None:
    privacy = client.get("/privacy").text
    terms = client.get("/terms").text
    cookies = client.get("/cookies").text
    analytics = client.get("/analytics-consent").text
    offer = client.get("/offer").text

    for required in (
        "предприниматель Шишеня Ян Александрович",
        "ИНН 667803118920",
        "ОГРНИП 320665800036109",
        "Langfuse Cloud EU",
        "LiteLLM",
        "Temporal",
        "MediaScribe",
        "yan@shishenya.ru",
    ):
        assert required in privacy
    assert "законное основание" in terms
    assert "проинформировать участников о записи" in terms
    assert "загружается сразу" in analytics
    assert "Вебвизор" in analytics
    assert "Вебвизор" in cookies
    assert "Платёжный интерфейс временно недоступен" in offer
