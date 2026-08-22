from pathlib import Path

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = ROOT.parents[1]
PUBLIC_STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "static" / "public"
PUBLIC_TEMPLATE_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "templates" / "public"
PHASE2_ACTIVATION_CONTRACT = (
    REPO_ROOT / "specs" / "093-public-landing-analytics" / "contracts" / "phase2-activation-contract.md"
)
PRODUCTION_ENV_EXAMPLE = REPO_ROOT / "infra" / "env" / "rec.production.env.example"

FORBIDDEN_DEFERRED_PROVIDER_SCRIPT_MARKERS = (
    "googletagmanager.com",
    "google-analytics.com",
    "googleadservices.com",
    "googleads.g.doubleclick.net",
    "gtag(",
    "GTM-",
    "posthog.init",
    "posthog.capture(",
    "posthog-js",
    "app.posthog.com",
    "clarity(",
    "clarity.ms",
    "amplitude.getInstance",
    "amplitude.init",
    "mixpanel.init",
    "cdn.mxpnl.com",
    "matomo.js",
    "_paq.push",
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

PHASE2_ACTIVATION_EVENTS = (
    "desktop_first_opened",
    "desktop_account_connected",
    "desktop_autorecord_enabled",
    "first_recording_completed",
    "first_result_viewed",
    "first_value_session_completed",
)


def _analytics_app(database_url: str):
    return create_app(
        Settings(
            database_url=database_url,
            minio_access_key="test",
            minio_secret_key="test",
            minio_bucket="test-bucket",
            public_analytics_enabled=True,
            public_analytics_validation_mode="render_only",
            public_analytics_yandex_metrica_id="12345678",
            public_analytics_replay_enabled=True,
        )
    )


def test_public_pages_render_without_analytics_by_default(client) -> None:
    for path in ("/", "/download"):
        response = client.get(path)
        assert response.status_code == 200
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "cookieconsent" not in response.text.lower()


def test_public_pages_render_immediate_narrow_analytics_context(
    postgres_worker_database_url: str,
) -> None:
    app = _analytics_app(postgres_worker_database_url)

    with TestClient(app) as client:
        landing = client.get("/")
        download = client.get("/download")

    for response, surface in ((landing, "public_landing"), (download, "public_download")):
        assert response.status_code == 200
        assert 'id="graf-public-analytics-config"' in response.text
        assert '"yandex_metrica_id": "12345678"' in response.text
        assert f'"surface": "{surface}"' in response.text
        assert "/static/public/analytics.js?v=" in response.text
        assert "cookieconsent.umd.js" not in response.text
        assert "cookieconsent.css" not in response.text
        assert '"replay_allowed": false' in response.text


def test_public_pages_render_safe_campaign_context_without_private_values(
    postgres_worker_database_url: str,
) -> None:
    app = _analytics_app(postgres_worker_database_url)

    with TestClient(app) as client:
        response = client.get(
            "/?utm_source=Yandex_Direct&utm_medium=CPC&utm_campaign=2026q3_b2c_launch_ru"
            "&utm_content=customer@example.com&utm_term=https://private.example/signed?token=abc",
            headers={"referer": "https://yandex.ru/search/?text=graf"},
        )

    assert '"utm_source": "yandex_direct"' in response.text
    assert '"utm_medium": "cpc"' in response.text
    assert '"utm_content": null' in response.text
    assert '"utm_term": null' in response.text
    assert "customer@example.com" not in response.text
    assert "private.example" not in response.text
    assert "token=abc" not in response.text


def test_public_analytics_is_absent_from_private_and_legal_surfaces(
    postgres_worker_database_url: str,
) -> None:
    app = _analytics_app(postgres_worker_database_url)

    with TestClient(app) as client:
        responses = [
            client.get(path, follow_redirects=True)
            for path in (
                "/login", "/admin", "/cabinet/not-a-real-page", "/api/v1/health/live",
                "/privacy", "/cookies", "/terms", "/offer", "/analytics-consent",
            )
        ]

    for response in responses:
        assert response.status_code < 500
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "metrika/tag.js" not in response.text


def test_public_pages_and_controller_contain_exact_new_funnel_contract(
    postgres_worker_database_url: str,
) -> None:
    app = _analytics_app(postgres_worker_database_url)
    with TestClient(app) as client:
        landing = client.get("/")
        download = client.get("/download")

    for section in ("hero", "audience", "workflow", "faq", "final_cta"):
        assert f'data-analytics-section="{section}"' in landing.text
        assert f'"{section}"' in landing.text
    for cta in ("header_download", "hero_download", "final_download", "header_login"):
        assert f'data-analytics-cta="{cta}"' in landing.text
        assert f'"{cta}"' in landing.text
    assert 'data-analytics-cta="download_page_installer"' in download.text
    assert 'data-analytics-cta="download_page_login"' in download.text

    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")
    for goal in (
        "public_landing_viewed", "public_landing_section_seen", "public_landing_cta_clicked",
        "public_download_viewed", "public_installer_download_clicked", "public_login_intent_clicked",
        "public_product_tab_selected", "public_pricing_cycle_selected", "public_faq_opened",
    ):
        assert goal in analytics_js


def test_public_yandex_controller_is_immediate_narrow_query_safe_and_deduplicated() -> None:
    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")

    for marker in (
        "metrika/tag.js", "clickmap: false", "trackLinks: false",
        "accurateTrackBounce: false", "webvisor: false", "defer: true",
        "reachGoal", "IntersectionObserver", "sentKeys[key]", "config.page_path",
    ):
        assert marker in analytics_js
    for forbidden in (
        "window.location.href", "document.title", "CookieConsent.run", "webvisor: true",
        "clickmap: true", "googletagmanager.com",
    ):
        assert forbidden.lower() not in analytics_js.lower()


def test_public_analytics_production_example_stays_explicit_and_replay_disabled() -> None:
    env_example = PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "TWOBRAIN_PUBLIC_ANALYTICS_ENABLED=false" in env_example
    assert "# TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID=" in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_VALIDATION_MODE=disabled" in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_REPLAY_ENABLED=false" in env_example
    assert not [
        line for line in env_example.splitlines()
        if line.startswith("TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID=")
    ]
    assert "TWOBRAIN_GOOGLE_CALENDAR_CLIENT_SECRET" not in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_GOOGLE" not in env_example
    assert "GA4" not in env_example
    assert "GTM" not in env_example


def test_public_analytics_controller_is_provider_failure_and_duplicate_init_safe() -> None:
    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")

    assert "script.onerror = function" in analytics_js
    assert "api.providerBlocked = true" in analytics_js
    assert "api.providerLoaded = false" in analytics_js
    assert "providerInitStarted" in analytics_js
    assert "api.providerInitStarted = true" in analytics_js
    assert "document.querySelector('script[data-graf-provider=\"yandex-metrica\"]')" in analytics_js
    assert "!api.providerBlocked" in analytics_js
    assert "listenersBound" in analytics_js
    assert "sectionsObserved" in analytics_js


def test_public_phase1_assets_do_not_include_deferred_provider_or_activation_code() -> None:
    public_asset_paths = [
        *PUBLIC_STATIC_DIR.rglob("*.js"),
        *PUBLIC_STATIC_DIR.rglob("*.css"),
        *PUBLIC_TEMPLATE_DIR.rglob("*.html"),
    ]
    content = "\n".join(path.read_text(encoding="utf-8") for path in public_asset_paths)
    lower_content = content.lower()

    assert not [marker for marker in FORBIDDEN_DEFERRED_PROVIDER_SCRIPT_MARKERS if marker in content]
    assert not [marker for marker in FORBIDDEN_DEFERRED_PROVIDER_SCRIPT_MARKERS if marker.lower() in lower_content]
    assert not [event for event in PHASE2_ACTIVATION_EVENTS if event in content]


def test_phase2_activation_contract_defines_future_events_and_forbidden_fields() -> None:
    contract = PHASE2_ACTIVATION_CONTRACT.read_text(encoding="utf-8")

    assert "planning contract only" in contract
    assert "does not authorize Phase 1 implementation" in contract
    for event_name in PHASE2_ACTIVATION_EVENTS:
        assert event_name in contract
    for forbidden_field in (
        "email address",
        "full name",
        "organization/company name",
        "raw account ID",
        "OAuth/provider tokens",
        "meeting or calendar identifiers",
    ):
        assert forbidden_field in contract
    assert "Event Owner And Implementation Gate" in contract
    assert "Identity Decision Gate" in contract
    assert "Consent And Notice Decision Gate" in contract
    assert "Deletion And Reporting Truth" in contract


def _contains_forbidden_url(path: Path) -> bool:
    content = path.read_text(encoding="utf-8").lower()
    return any(marker in content for marker in FORBIDDEN_LIVE_PROVIDER_URLS)
