from pathlib import Path
from struct import unpack

from fastapi.testclient import TestClient

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.templates import PUBLIC_STATIC_URL, public_static_asset_url

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "static" / "public"
PUBLIC_TEMPLATE_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "templates" / "public"
REPOSITORY_ROOT = ROOT.parents[1]


def test_public_landing_assets_and_templates_are_local() -> None:
    for asset in (
        "landing.css",
        "landing.js",
        "analytics.js",
        "graf-recording-landing.png",
        "graf-transcript-landing.png",
        "graf-transcript-landing-mobile.png",
        "graf-summary-landing.png",
        "fonts/onest-cyrillic.woff2",
        "fonts/onest-latin.woff2",
        "fonts/OFL.txt",
        "downloads/graf.pkg",
    ):
        assert (PUBLIC_STATIC_DIR / asset).is_file()
    for template in ("landing.html", "download.html", "_analytics.html"):
        assert (PUBLIC_TEMPLATE_DIR / template).is_file()


def test_public_product_assets_have_expected_dimensions_and_no_metadata() -> None:
    expected = {
        "graf-recording-landing.png": (1600, 1000),
        "graf-transcript-landing.png": (1600, 1000),
        "graf-transcript-landing-mobile.png": (1200, 900),
        "graf-summary-landing.png": (1600, 1000),
    }
    for name, dimensions in expected.items():
        content = (PUBLIC_STATIC_DIR / name).read_bytes()
        assert content[:8] == b"\x89PNG\r\n\x1a\n"
        assert unpack(">II", content[16:24]) == dimensions
        assert b"tEXt" not in content
        assert b"iTXt" not in content
        assert b"zTXt" not in content
        assert b"eXIf" not in content


def test_public_static_assets_are_mounted_by_app() -> None:
    app = create_app(Settings())
    assert any(route.path == PUBLIC_STATIC_URL for route in app.routes)


def test_public_download_template_exposes_one_universal_installer() -> None:
    content = (PUBLIC_TEMPLATE_DIR / "download.html").read_text(encoding="utf-8")

    assert content.count("downloads/graf.pkg") == 1
    assert "graf-local.pkg" not in content
    assert "arm64" not in content.lower()
    assert "x86_64" not in content.lower()
    assert content.count('data-platform-status="planned"') == 2


def test_public_downloads_use_read_only_runtime_mount_outside_git() -> None:
    compose = (REPOSITORY_ROOT / "infra" / "docker-compose.yml").read_text()
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text()

    assert (
        "./runtime/public-downloads:"
        "/usr/local/lib/python3.13/site-packages/"
        "twobrain_rec_server/public/static/public/downloads:ro"
    ) in compose
    assert "infra/runtime/" in gitignore


def test_public_landing_css_and_scripts_are_local_accessible_and_progressive() -> None:
    css = (PUBLIC_STATIC_DIR / "landing.css").read_text(encoding="utf-8").lower()
    scripts = "\n".join(
        (PUBLIC_STATIC_DIR / name).read_text(encoding="utf-8").lower()
        for name in ("landing.js", "analytics.js")
    )
    forbidden = ("cdn.", "cdnjs", "jsdelivr", "googleapis", "fonts.gstatic", "tailwind", "react", "vue")

    assert not [marker for marker in forbidden if marker in css + scripts]
    assert ":focus-visible" in css
    assert "prefers-reduced-motion: reduce" in css
    assert ".reveal { opacity: 1" in css
    assert ".enhanced .walkthrough-panel:not(.active)" in css
    assert "overflow-x: hidden" in css
    assert "transition: all" not in css
    assert "cookieconsent" not in scripts


def test_public_html_security_headers_discovery_and_canonical_are_shared() -> None:
    settings = Settings(public_base_url="https://rec.2brain.pro")
    app = create_app(settings)

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

        robots = client.get("/robots.txt")
        sitemap = client.get("/sitemap.xml")

    assert robots.status_code == 200
    assert "Sitemap: https://rec.2brain.pro/sitemap.xml" in robots.text
    assert sitemap.status_code == 200
    for path in ("/", "/download", "/privacy", "/cookies", "/terms", "/offer", "/analytics-consent"):
        assert f"https://rec.2brain.pro{path}" in sitemap.text


def test_fingerprinted_public_static_assets_have_immutable_cache_only_with_version() -> None:
    app = create_app(Settings())
    with TestClient(app) as client:
        fingerprinted = client.get(public_static_asset_url("landing.css"))
        stable = client.get("/static/public/landing.css")

    assert fingerprinted.status_code == stable.status_code == 200
    assert fingerprinted.headers["cache-control"] == "public, max-age=31536000, immutable"
    assert stable.headers["cache-control"] == "no-cache"
