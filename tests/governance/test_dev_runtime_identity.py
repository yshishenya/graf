from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_container_and_app_identity_are_sha_bound():
    compose = (ROOT / "infra/docker-compose.dev.yml").read_text()
    dockerfile = (ROOT / "infra/server/Dockerfile").read_text()
    app = (ROOT / "apps/macos/Scripts/build-dev-app.sh").read_text()
    assert "GRAF_DEV_SOURCE_SHA" in compose and "org.2brain.graf.dev.source-sha" in compose
    assert "GRAF_DEV_SOURCE_SHA" in dockerfile
    assert "pro.2brain.graf.dev" in app


def test_installer_preserves_one_stable_destination_and_identity():
    installer = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text()
    assert 'DESTINATION" = "/Applications/GRAF Dev.app"' in installer
    assert "designated_requirement drift" in installer
    assert "signing identity drift" in installer
    assert "entitlements drift" in installer
    assert "entitlements_digest()" in installer
    assert "codesign -d --entitlements :- \"$1\" > \"$TEMP_ROOT/entitlements.plist\" 2>/dev/null" in installer
