from pathlib import Path

from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app
from twobrain_rec_server.public.templates import PUBLIC_STATIC_URL, public_static_asset_url

ROOT = Path(__file__).resolve().parents[2]
PUBLIC_STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "static" / "public"
PUBLIC_TEMPLATE_DIR = ROOT / "src" / "twobrain_rec_server" / "public" / "templates" / "public"


def test_public_landing_static_assets_are_local_to_server_package() -> None:
    assert (PUBLIC_STATIC_DIR / "landing.css").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-hero-product.png").is_file()
    assert (PUBLIC_STATIC_DIR / "downloads" / "graf.pkg").is_file()
    assert (PUBLIC_STATIC_DIR / "analytics.js").is_file()
    assert (PUBLIC_STATIC_DIR / "cookieconsent.umd.js").is_file()
    assert (PUBLIC_STATIC_DIR / "cookieconsent.css").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "landing.html").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "download.html").is_file()
    assert (PUBLIC_TEMPLATE_DIR / "_analytics.html").is_file()


def test_public_download_template_exposes_one_universal_installer() -> None:
    content = (PUBLIC_TEMPLATE_DIR / "download.html").read_text(encoding="utf-8")

    assert content.count("downloads/graf.pkg") == 1
    assert "graf-local.pkg" not in content
    assert "arm64" not in content.lower()
    assert "x86_64" not in content.lower()
    assert "Intel-версия" not in content


def test_public_landing_static_assets_are_mounted_by_app() -> None:
    app = create_app(Settings())

    assert any(route.path == PUBLIC_STATIC_URL for route in app.routes)


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
    assert "transition: all" not in content


def test_public_landing_asset_url_is_fingerprinted() -> None:
    url = public_static_asset_url("landing.css")

    assert url.startswith("/static/public/landing.css?v=")
    assert len(url.rsplit("?v=", 1)[1]) == 12
