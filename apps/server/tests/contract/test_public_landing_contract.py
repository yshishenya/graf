import json
from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.templates import PUBLIC_STATIC_URL, public_static_asset_url
from twobrain_rec_server.public.web import LANDING_AUTORECORD_PRIORITY, landing_autorecord_apps

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "static" / "public"
PUBLIC_TEMPLATE_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "templates" / "public"
MEETING_TARGET_REGISTRY = (
    ROOT
    / "src"
    / "twobrain_rec_server"
    / "db"
    / "migrations"
    / "data"
    / "0030_meeting_target_registry.json"
)
REPOSITORY_ROOT = ROOT.parents[1]


def test_public_landing_static_assets_are_local_to_server_package() -> None:
    assert (PUBLIC_STATIC_DIR / "landing.css").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-atmosphere.jpg").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-recording-proof.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-recording-proof-focus.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-focus.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-focus.webp").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-control-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-toggle-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof.webp").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof-mobile.webp").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof.webp").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-focus.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-focus-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-mobile.webp").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "onest-cyrillic.woff2").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "onest-latin.woff2").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "OFL.txt").is_file()
    assert (PUBLIC_STATIC_DIR / "downloads" / "graf.pkg").is_file()
    assert (PUBLIC_STATIC_DIR / "analytics.js").is_file()
    assert (PUBLIC_STATIC_DIR / "cookieconsent.umd.js").is_file()
    assert (PUBLIC_STATIC_DIR / "cookieconsent.css").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "landing.html").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "download.html").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "_analytics.html").is_file()


def test_public_landing_autorecord_count_matches_current_registry() -> None:
    registry = json.loads(MEETING_TARGET_REGISTRY.read_text(encoding="utf-8"))
    prompt_enabled_macos = sum(
        target["platform"] == "macos" and target["mode"] == "prompt_enabled"
        for target in registry["targets"]
    )
    expected_names = {
        target["displayName"]
        for target in registry["targets"]
        if target["platform"] == "macos" and target["mode"] == "prompt_enabled"
    }
    rendered_names = landing_autorecord_apps()

    assert prompt_enabled_macos == len(expected_names)
    assert len(rendered_names) == len(set(rendered_names)) == len(expected_names)
    assert set(rendered_names) == expected_names
    assert rendered_names[: len(LANDING_AUTORECORD_PRIORITY)] == LANDING_AUTORECORD_PRIORITY


def test_public_landing_static_assets_are_mounted_by_app() -> None:
    app = create_app(Settings())

    assert any(route.path == PUBLIC_STATIC_URL for route in app.routes)


def test_public_download_template_exposes_one_universal_installer() -> None:
    content = (PUBLIC_TEMPLATE_DIR / "download.html").read_text(encoding="utf-8")

    assert content.count("downloads/graf.pkg") == 1
    assert "graf-local.pkg" not in content
    assert "arm64" not in content.lower()
    assert "x86_64" not in content.lower()
    assert "Intel-версия" not in content


def test_public_downloads_use_a_read_only_runtime_mount_outside_git() -> None:
    compose = (REPOSITORY_ROOT / "infra" / "docker-compose.yml").read_text()
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text()

    assert (
        "./runtime/public-downloads:"
        "/usr/local/lib/python3.13/site-packages/"
        "twobrain_rec_server/public/static/public/downloads:ro"
    ) in compose
    assert "infra/runtime/" in gitignore


def test_public_landing_css_avoids_runtime_cdns_or_client_toolchain() -> None:
    content = "\n".join(
        [
            (PUBLIC_STATIC_DIR / "landing.css").read_text().lower(),
            (PUBLIC_STATIC_DIR / "analytics.js").read_text().lower(),
            (PUBLIC_STATIC_DIR / "cookieconsent.umd.js").read_text().lower(),
            (PUBLIC_STATIC_DIR / "cookieconsent.css").read_text().lower(),
        ]
    )
    forbidden = (
        "cdn.",
        "cdnjs",
        "jsdelivr",
        "googleapis",
        "fonts.gstatic",
        "tailwind",
        "daisyui",
        "flowbite",
        "shadcn",
        "react",
        "vue",
        "svelte",
        "webpack",
        "vite",
    )

    assert not [marker for marker in forbidden if marker in content]


def test_public_landing_cookieconsent_assets_are_pinned_and_attributed() -> None:
    cookieconsent_js = (PUBLIC_STATIC_DIR / "cookieconsent.umd.js").read_text(encoding="utf-8")
    cookieconsent_css = (PUBLIC_STATIC_DIR / "cookieconsent.css").read_text(encoding="utf-8")

    assert "CookieConsent 3.1.0" in cookieconsent_js
    assert "Released under the MIT License" in cookieconsent_js
    assert "CookieConsent 3.1.0" in cookieconsent_css
    assert "Released under the MIT License" in cookieconsent_css


def test_public_landing_css_keeps_accessible_focus_and_stable_motion() -> None:
    content = (PUBLIC_STATIC_DIR / "landing.css").read_text().lower()

    assert ":focus-visible" in content
    assert "prefers-reduced-motion: reduce" in content
    assert "animation-timeline: view()" in content
    assert 'url("landing-atmosphere.jpg")' in content
    assert "hero-proof-track" in content
    assert "animation: hero-proof-track 9s infinite alternate" in content
    assert "hero-proof-progress-transcript" in content
    assert "animation: hero-proof-progress-transcript 9s infinite alternate" in content
    assert "hero-proof-progress" in content
    assert "pause-hero-proof" in content
    assert "animation-play-state: paused" in content
    assert "hero-proof-toggle" in content
    assert "aspect-ratio: 390 / 620" in content
    assert "object-position: top center" in content
    assert "#pause-platform-rail" in content
    assert "display: none" in content
    assert "hero-proof-tabs" not in content
    assert "transition: all" not in content
    assert "overflow-x: hidden" not in content
    assert "inset: -24% -6% -22% 6%" in content
    assert "margin: 0 -16px" not in content
    assert ".legal-page h1" in content
    assert ".legal-section code" in content
    assert "overflow-wrap: anywhere" in content


def test_public_landing_hero_product_cta_uses_allowlisted_section_target() -> None:
    content = (PUBLIC_TEMPLATE_DIR / "landing.html").read_text(encoding="utf-8")

    assert 'data-analytics-cta="hero_product"' in content
    assert 'data-analytics-target="section"' in content
    assert 'data-analytics-target="hero_product"' not in content


def test_public_cookie_preferences_use_dark_contrast_tokens() -> None:
    content = (PUBLIC_STATIC_DIR / "landing.css").read_text(encoding="utf-8")

    for token in (
        "--cc-cookie-category-block-bg: #1b1822",
        "--cc-cookie-category-block-hover-bg: #241f2e",
        "--cc-cookie-category-block-border: rgba(232, 226, 242, 0.14)",
        "--cc-footer-bg: #0d0b11",
        "--cc-footer-color: #d2ccd8",
    ):
        assert token in content


def test_public_html_security_headers_discovery_and_canonical_are_shared() -> None:
    settings = Settings(public_base_url="https://rec.2brain.pro")
    app = create_app(settings)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        for path in ("/", "/download", "/privacy", "/cookies", "/terms", "/offer", "/analytics-consent"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["x-content-type-options"] == "nosniff"
            assert response.headers["x-frame-options"] == "DENY"
            assert response.headers["referrer-policy"] == "strict-origin-when-cross-origin"
            assert response.headers["permissions-policy"] == "camera=(), microphone=(), geolocation=()"
            assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
            assert f'<link rel="canonical" href="https://rec.2brain.pro{path}">' in response.text
            assert 'property="og:title"' in response.text
            assert 'property="og:locale" content="ru_RU"' in response.text
            assert 'name="twitter:title"' in response.text
            assert 'name="twitter:description"' in response.text

        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Sitemap: https://rec.2brain.pro/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    assert sitemap.headers["content-type"].startswith("application/xml")
    for path in ("/", "/download", "/privacy", "/cookies", "/terms", "/analytics-consent"):
        assert f"https://rec.2brain.pro{path}" in sitemap.text


def test_fingerprinted_public_static_assets_are_immutable_only_with_version() -> None:
    app = create_app(Settings())

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        fingerprinted = client.get(public_static_asset_url("landing.css"))
        stable = client.get("/static/public/landing.css")

    assert fingerprinted.status_code == stable.status_code == 200
    assert fingerprinted.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert stable.headers["cache-control"] == "no-cache"


def test_public_landing_asset_url_is_fingerprinted() -> None:
    url = public_static_asset_url("landing.css")

    assert url.startswith("/static/public/landing.css?v=")
    assert len(url.rsplit("?v=", 1)[1]) == 12
