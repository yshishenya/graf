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
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-control-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-autorecord-proof-toggle-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-transcript-proof-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-focus.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-focus-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "landing-outcome-proof-mobile.png").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "onest-cyrillic.woff2").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "onest-latin.woff2").is_file()
    assert (PUBLIC_STATIC_DIR / "fonts" / "OFL.txt").is_file()
    assert (PUBLIC_STATIC_DIR / "downloads" / "graf-local.pkg").is_file()
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
    assert "transition: all" not in content
    assert "overflow-x: hidden" not in content


def test_public_landing_asset_url_is_fingerprinted() -> None:
    url = public_static_asset_url("landing.css")

    assert url.startswith("/static/public/landing.css?v=")
    assert len(url.rsplit("?v=", 1)[1]) == 12
