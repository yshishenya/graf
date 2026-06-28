from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = ROOT / "src" / "twobrain_rec_server" / "cabinet" / "static" / "cabinet"


def test_local_htmx_asset_is_pinned_with_source_and_license() -> None:
    htmx = (STATIC_DIR / "htmx-2.0.10.min.js").read_text()
    source = (STATIC_DIR / "htmx-2.0.10.source.txt").read_text()

    assert 'version:"2.0.10"' in htmx
    assert "selfRequestsOnly:true" in htmx
    assert "source: https://unpkg.com/htmx.org@2.0.10/dist/htmx.min.js" in source
    assert "package: https://www.npmjs.com/package/htmx.org/v/2.0.10" in source
    assert "license: 0BSD" in source


def test_cabinet_static_assets_do_not_reference_runtime_cdns_or_build_outputs() -> None:
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
    checked = [
        STATIC_DIR / "cabinet.css",
        STATIC_DIR / "cabinet.js",
    ]

    for path in checked:
        content = path.read_text().lower()
        assert not [marker for marker in forbidden if marker in content]


def test_cabinet_brand_assets_are_local_and_nonempty() -> None:
    for filename in [
        "graf-icon.png",
        "graf-icon@2x.png",
        "favicon.ico",
        "favicon-16.png",
        "favicon-32.png",
        "apple-touch-icon.png",
        "graf-wordmark-dark.png",
        "graf-wordmark-dark@2x.png",
        "graf-wordmark-light.png",
        "graf-wordmark-light@2x.png",
    ]:
        path = STATIC_DIR / filename
        assert path.is_file()
        assert path.stat().st_size > 0


def test_cabinet_js_wires_csrf_header_for_unsafe_htmx_requests() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert 'meta[name="csrf-token"]' in script
    assert "htmx:configRequest" in script
    assert "X-CSRF-Token" in script
    assert "POST" in script
    assert "DELETE" in script


def test_cabinet_js_keeps_fragment_state_ephemeral() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    assert "htmx:afterSwap" in script
    assert "meeting-list-region" in script
    assert "localStorage" not in script
    assert "sessionStorage" not in script


def test_cabinet_js_owns_component_dom_behavior() -> None:
    script = (STATIC_DIR / "cabinet.js").read_text()

    for marker in [
        "data-code-form",
        "auth-leaving",
        "data-delete-dialog",
        "activateDetailTab",
        "data-playback-player",
        "new FormData(form)",
    ]:
        assert marker in script
