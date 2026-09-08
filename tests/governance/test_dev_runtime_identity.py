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
    assert "Dev app is running; use dev-harness promote or rollback" in installer


def test_dev_presentation_is_fixed_and_distinct_from_production():
    builder = (ROOT / "apps/macos/Scripts/build-dev-app.sh").read_text()
    installer = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text()

    for source in (builder, installer):
        assert "CFBundleDisplayName" in source
        assert "CFBundleName" in source
        assert "GRAF_APP_CHANNEL" in source
        assert "AppIcon.icns" in source
    assert 'grep -Fxq "GRAF Dev"' in builder
    assert 'grep -Fxq "dev"' in builder
    assert "cmp -s" in builder
    assert "cmp -s" in installer


def test_retired_launchers_refuse_without_creating_an_app(tmp_path):
    import subprocess

    for script in (
        ROOT / "apps/macos/Scripts/build-local-app.sh",
        ROOT / "apps/macos/Scripts/run-local-app.sh",
        ROOT / "apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh",
        ROOT / "specs/249-notification-control-design/native-preview/build.sh",
    ):
        result = subprocess.run(
            ["sh", str(script), "--open"],
            cwd=tmp_path, capture_output=True, text=True, check=False,
        )
        assert result.returncode == 1
        assert "/Applications/GRAF Dev.app" in result.stderr
        assert "dev-harness.sh" in result.stderr
    assert list(tmp_path.iterdir()) == []


def test_retired_manual_gate_cannot_build_launch_or_terminate_apps(tmp_path):
    import os
    import subprocess

    trap = tmp_path / "unexpected-actions"
    commands = tmp_path / "bin"
    commands.mkdir()
    for command in ("swift", "open", "osascript", "pkill", "caffeinate", "sh"):
        path = commands / command
        path.write_text(f'#!/bin/sh\nprintf "%s\n" "$0" >> "{trap}"\nexit 97\n')
        path.chmod(0o755)
    script = ROOT / "apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh"
    # The only allowed sh child is the existing refusal, never an installer.
    (commands / "sh").write_text(
        '#!/bin/sh\ncase "$1" in */run-local-app.sh) exec /bin/sh "$@";; esac\n'
        f'printf "%s\n" "$*" >> "{trap}"\nexit 97\n'
    )
    for args in ([], ["--preflight"], ["--self-test"], ["--open"]):
        result = subprocess.run(
            ["/bin/sh", str(script), *args], cwd=tmp_path,
            env={**os.environ, "PATH": f"{commands}:{os.environ['PATH']}",
                 "SYSTEM_AUDIO_MANUAL_GATE_APP_BUNDLE": "/tmp/forbidden.app"},
            capture_output=True, text=True, timeout=5,
        )
        assert result.returncode == 1
        assert "/Applications/GRAF Dev.app" in result.stderr
        assert "dev-harness.sh" in result.stderr
    assert not trap.exists()
