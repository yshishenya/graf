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
