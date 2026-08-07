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

PHASE2_ACTIVATION_EVENTS = (
    "desktop_first_opened",
    "desktop_account_connected",
    "desktop_autorecord_enabled",
    "first_recording_completed",
    "first_result_viewed",
    "first_value_session_completed",
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


def test_public_pages_render_safe_local_analytics_assets_in_render_only_mode(
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
    assert 'id="graf-public-analytics-config"' in response.text
    assert '"yandex_metrica_id": "YA_TEST_COUNTER"' in response.text
    assert '"surface": "public_landing"' in response.text
    assert '"public_installer_download_clicked"' in response.text
    assert "/static/public/analytics.js?v=" in response.text
    assert "/static/public/cookieconsent.umd.js?v=" in response.text
    assert "/static/public/cookieconsent.css?v=" in response.text
    assert not [marker for marker in FORBIDDEN_LIVE_PROVIDER_URLS if marker in response.text.lower()]
    assert not [marker for marker in FORBIDDEN_PHASE1_MARKERS if marker in response.text]


def test_public_pages_render_safe_campaign_context_without_private_values(
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


def test_public_analytics_is_absent_from_non_public_and_legal_surfaces(
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
        responses = [
            test_client.get("/login", follow_redirects=False),
            test_client.get("/admin", follow_redirects=False),
            test_client.get("/cabinet/not-a-real-page", follow_redirects=False),
            test_client.get("/api/v1/health/live", follow_redirects=False),
            test_client.get("/privacy", follow_redirects=False),
            test_client.get("/cookies", follow_redirects=False),
            test_client.get("/terms", follow_redirects=False),
            test_client.get("/analytics-consent", follow_redirects=False),
        ]

    for response in responses:
        assert "graf-public-analytics-config" not in response.text
        assert "analytics.js" not in response.text
        assert "cookieconsent.umd.js" not in response.text
        assert "metrika/tag.js" not in response.text
        assert "data-graf-cookieconsent-version" not in response.text


def test_public_pages_render_stable_conversion_labels_in_render_only_mode(
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
    )
    app = create_app(settings)

    with TestClient(app) as test_client:
        landing = test_client.get("/")
        download = test_client.get("/download")

    assert landing.status_code == 200
    assert download.status_code == 200

    for section_id in ("hero", "platforms", "pricing", "outcomes", "trust", "final_cta"):
        assert f'data-analytics-section="{section_id}"' in landing.text
        assert f'"{section_id}"' in landing.text

    landing_cta_labels = (
        "header_download",
        "hero_download",
        "final_download",
        "hero_login",
        "final_login",
    )
    for cta_location in landing_cta_labels:
        assert f'data-analytics-cta="{cta_location}"' in landing.text
        assert f'"{cta_location}"' in landing.text

    assert 'data-analytics-cta="download_page_installer"' in download.text
    assert 'data-analytics-target="installer_package"' in download.text
    assert 'data-analytics-cta="download_page_login"' in download.text
    assert 'data-analytics-target="login"' in download.text
    assert '"download_page_installer"' in download.text
    assert '"download_page_login"' in download.text


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
    assert "hasCategory(grantedCategories, \"analytics\")" in analytics_js
    assert "reachGoal" in analytics_js
    assert "metrika/tag.js" in analytics_js
    assert "googletagmanager.com" not in analytics_js
    assert "google-analytics.com" not in analytics_js
    assert "posthog.com" not in analytics_js.lower()
    assert "initializePostHogAutocapture" in analytics_js


def test_public_analytics_controller_has_conversion_dispatch_hooks() -> None:
    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")

    assert "startGrantedTracking" in analytics_js
    assert "dispatchOnce" in analytics_js
    assert "sentKeys" in analytics_js
    assert "[data-analytics-cta]" in analytics_js
    assert "[data-analytics-section]" in analytics_js
    assert "IntersectionObserver" in analytics_js
    assert "public_landing_section_seen" in analytics_js
    assert "public_landing_cta_clicked" in analytics_js
    assert "public_download_viewed" in analytics_js
    assert "public_installer_download_clicked" in analytics_js
    assert "public_login_intent_clicked" in analytics_js


def test_public_analytics_controller_has_consent_persistence_and_safe_event_allowlists() -> None:
    analytics_js = (PUBLIC_STATIC_DIR / "analytics.js").read_text(encoding="utf-8")

    assert "CookieConsent.run" in analytics_js
    assert "graf_public_analytics_consent" in analytics_js
    assert "revisionFromCopyVersion" in analytics_js
    assert "accepted_all" in analytics_js
    assert "necessary_only" in analytics_js
    assert "customized" in analytics_js
    assert "revoked" in analytics_js
    assert "safeEventFields" in analytics_js
    assert "allowedLabel(\"section_id\"" in analytics_js
    assert "allowedLabel(\"cta_location\"" in analytics_js
    assert "allowedLabel(\"target_kind\"" in analytics_js
    assert "hasCategory(currentCategories, \"analytics\")" in analytics_js
    assert "webvisor: hasCategory(grantedCategories, \"behavior_replay\") && config.replay_allowed" in analytics_js
    assert "customer@example.com" not in analytics_js
    assert "signed" not in analytics_js.lower()
    assert "passcode" not in analytics_js.lower()


def test_public_analytics_production_env_example_is_disabled_and_redacted() -> None:
    env_example = PRODUCTION_ENV_EXAMPLE.read_text(encoding="utf-8")

    assert "TWOBRAIN_PUBLIC_ANALYTICS_ENABLED=false" in env_example
    assert "# TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID=" in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_VALIDATION_MODE=disabled" in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_REPLAY_ENABLED=false" in env_example
    assert "TWOBRAIN_PUBLIC_ANALYTICS_CONSENT_COPY_VERSION=2026-07-08.1" in env_example
    assert not [
        line
        for line in env_example.splitlines()
        if line.startswith("TWOBRAIN_PUBLIC_ANALYTICS_YANDEX_METRICA_ID=")
    ]
    assert "GOOGLE" not in env_example
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
