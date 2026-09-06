from pathlib import Path

from twobrain_rec_server.cabinet.templates import CABINET_STATIC_URL
from twobrain_rec_server.config import Settings
from twobrain_rec_server.main import create_app

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "src" / "twobrain_rec_server"
PROJECT_ROOT = ROOT.parents[1]


def test_cabinet_frontend_foundation_avoids_separate_client_toolchain() -> None:
    forbidden_files = [
        PROJECT_ROOT / "package.json",
        PROJECT_ROOT / "tailwind.config.js",
        PROJECT_ROOT / "vite.config.js",
        PROJECT_ROOT / "postcss.config.js",
        PROJECT_ROOT / "storybook.config.js",
    ]

    assert not [path for path in forbidden_files if path.exists()]


def test_cabinet_static_assets_are_local_to_server_package() -> None:
    static_dir = SERVER_ROOT / "cabinet" / "static" / "cabinet"

    assert (static_dir / "cabinet.css").is_file()
    assert (static_dir / "cabinet.js").is_file()
    assert (static_dir / "htmx-2.0.10.min.js").is_file()


def test_cabinet_static_assets_are_mounted_by_app() -> None:
    app = create_app(Settings())

    assert any(route.path == CABINET_STATIC_URL for route in app.routes)


def test_feature_104_main_window_has_responsive_accessible_dom_contract() -> None:
    sections = (
        SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "components" / "sections.html"
    ).read_text()
    meeting_list = (
        SERVER_ROOT
        / "cabinet"
        / "templates"
        / "cabinet"
        / "pages"
        / "meeting_list_content.html"
    ).read_text()

    assert 'mark_src=static_url ~ "/graf-icon.png"' in sections
    assert 'wordmark_src=static_url ~ "/graf-wordmark-dark.png"' in sections
    assert 'alt="{{ name }}"' in sections
    assert 'width="34" height="34" alt=""' in sections
    assert 'width="243" height="90" alt="{{ name }}"' in sections
    for marker in [
        'aria-label="Поиск встреч"',
        'placeholder="Поиск встреч"',
        'aria-label="{{ filter_label }}"',
        'aria-label="Сортировка: {{ sort_label }}"',
        'aria-label="Загрузить запись"',
        "<span>Загрузить запись</span>",
        'aria-label="Действия с выбранными встречами"',
    ]:
        assert marker in meeting_list


def test_feature_240_mobile_navigation_keeps_js_and_no_js_paths_distinct() -> None:
    sections = (
        SERVER_ROOT / "cabinet" / "templates" / "cabinet" / "components" / "sections.html"
    ).read_text()
    css = (
        SERVER_ROOT / "cabinet" / "static" / "cabinet" / "cabinet.css"
    ).read_text()

    # The existing noscript rail remains the no-JS fallback. The enhanced page
    # needs a real mobile rail because noscript content is absent after JS runs.
    assert '<nav class="cabinet-mobile-nav"' in sections
    assert 'aria-current="page"' in sections
    assert 'html[data-cabinet-js="ready"] .cabinet-mobile-nav' in css
    assert 'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.desktop-embedded) > .cabinet-main' in css
    assert 'html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.desktop-embedded) > .sidebar' in css
    assert "display: none;" in css[css.index('html[data-cabinet-js="ready"] .app-shell[data-cabinet-shell]:not(.desktop-embedded) > .sidebar') :]
