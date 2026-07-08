from pathlib import Path

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "static" / "public"

FORBIDDEN_PHASE1_MARKERS = (
    "googletagmanager.com",
    "google-analytics.com",
    "googleadservices.com",
    "googleads.g.doubleclick.net",
    "gtag(",
    "GTM-",
    "posthog",
    "clarity.ms",
    "amplitude",
    "mixpanel",
    "matomo",
)

FORBIDDEN_LIVE_PROVIDER_URLS = (
    "mc.yandex",
    "mc.webvisor",
    "yastatic.net",
    "googletagmanager.com",
    "google-analytics.com",
    "cdn.jsdelivr",
    "cdnjs.cloudflare",
    "unpkg.com",
    "cookieconsent.orestbida.com",
)


def test_public_pages_render_without_analytics_by_default(client) -> None:
    for path in ("/", "/download"):
        response = client.get(path)

        assert response.status_code == 200
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "cookieconsent.umd.js" not in response.text
        assert "cookieconsent.css" not in response.text
        assert not [marker for marker in FORBIDDEN_LIVE_PROVIDER_URLS if marker in response.text.lower()]
        assert not [marker for marker in FORBIDDEN_PHASE1_MARKERS if marker in response.text]


def test_public_pages_render_safe_local_analytics_assets_in_render_only_mode(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'analytics-render-only.db'}",
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
    assert 'id="graf-public-analytics-config"' in response.text
    assert '"yandex_metrica_id": "YA_TEST_COUNTER"' in response.text
    assert '"surface": "public_landing"' in response.text
    assert '"public_installer_download_clicked"' in response.text
    assert "/static/public/analytics.js?v=" in response.text
    assert "/static/public/cookieconsent.umd.js?v=" in response.text
    assert "/static/public/cookieconsent.css?v=" in response.text
    assert not [marker for marker in FORBIDDEN_LIVE_PROVIDER_URLS if marker in response.text.lower()]
    assert not [marker for marker in FORBIDDEN_PHASE1_MARKERS if marker in response.text]


def test_public_pages_render_safe_campaign_context_without_private_values(tmp_path) -> None:
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path / 'analytics-campaign.db'}",
        minio_access_key="test",
        minio_secret_key="test",
        minio_bucket="test-bucket",
        public_analytics_enabled=True,
        public_analytics_validation_mode="render_only",
        public_analytics_yandex_metrica_id="YA_TEST_COUNTER",
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        response = test_client.get(
            "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
            "&utm_content=customer@example.com&utm_term=https://private.example/signed?token=abc",
            headers={"referer": "https://yandex.ru/search/?text=graf"},
        )

    assert response.status_code == 200
    assert '"campaign_attribution"' in response.text
    assert '"utm_source": "yandex_direct"' in response.text
    assert '"utm_medium": "cpc"' in response.text
    assert '"utm_campaign": "2026q3_b2c_launch_ru"' in response.text
    assert '"utm_content": null' in response.text
    assert '"utm_term": null' in response.text
    assert '"referrer_category": "paid"' in response.text
    assert "customer@example.com" not in response.text
    assert "private.example" not in response.text
    assert "token=abc" not in response.text


def test_public_analytics_assets_are_local_pinned_and_attributed() -> None:
    analytics_js = PUBLIC_STATIC_DIR / "analytics.js"
    cookieconsent_js = PUBLIC_STATIC_DIR / "cookieconsent.umd.js"
    cookieconsent_css = PUBLIC_STATIC_DIR / "cookieconsent.css"

    assert analytics_js.is_file()
    assert cookieconsent_js.is_file()
    assert cookieconsent_css.is_file()

    assert "CookieConsent 3.1.0" in cookieconsent_js.read_text(encoding="utf-8")
    assert "Released under the MIT License" in cookieconsent_js.read_text(encoding="utf-8")
    assert "CookieConsent 3.1.0" in cookieconsent_css.read_text(encoding="utf-8")
    assert "Released under the MIT License" in cookieconsent_css.read_text(encoding="utf-8")
    assert not _contains_forbidden_url(cookieconsent_js)
    assert not _contains_forbidden_url(cookieconsent_css)


def test_public_analytics_controller_has_consent_gated_yandex_entrypoint() -> None:
    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")

    assert "ensureYandexProvider" in analytics_js
    assert "hasCategory(categories, \"analytics\")" in analytics_js
    assert "reachGoal" in analytics_js
    assert "metrika/tag.js" in analytics_js
    assert "googletagmanager.com" not in analytics_js
    assert "google-analytics.com" not in analytics_js
    assert "posthog" not in analytics_js.lower()


def _contains_forbidden_url(path: Path) -> bool:
    content = path.read_text(encoding="utf-8").lower()
    return any(marker in content for marker in FORBIDDEN_LIVE_PROVIDER_URLS)
