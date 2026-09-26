from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_promotion_is_lock_protected_and_pointer_written_after_smoke():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "with state_lock(root)" in source
    assert "live promotion smoke failed" in source
    assert "active-manifest.json" in source


def test_runtime_compensation_refuses_unowned_processes():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "refusing to terminate unverified Dev backend pid" in source
    assert "refusing to restore over unverified Dev backend pid" in source
    assert "deadline = time.monotonic() + RUNTIME_CLEANUP_TIMEOUT_SECONDS" in source


def test_app_swap_rechecks_lifecycle_and_allows_cleanup_grace():
    installer = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text()
    lifecycle = (ROOT / "apps/macos/Scripts/dev-app-lifecycle.swift").read_text()
    harness = (ROOT / "scripts/dev-harness.py").read_text()
    assert installer.count('assert_app_stopped') >= 2
    ditto_offset = installer.index('ditto --norsrc --noextattr --noqtn "$CANDIDATE" "$STAGED_DESTINATION"')
    assert installer.index('assert_app_stopped', ditto_offset) > ditto_offset
    assert 'LaunchServices registration failed' in installer
    assert 'swift "$APP_LIFECYCLE" swap "$STAGED_DESTINATION" "$DESTINATION"' in installer
    assert 'DESTINATION_WAS_PRESENT=false' in installer
    assert 'mv "$DESTINATION" "$STAGED_DESTINATION"' in installer
    assert 'renameatx_np' in lifecycle
    assert 'RENAME_SWAP' in lifecycle
    assert 'expectedDevDestination' in lifecycle
    assert 'app swap destination must be /Applications/GRAF Dev.app' in lifecycle
    assert 'assertDevBundle(staged' in lifecycle
    assert 'assertDevBundle(installed' in lifecycle
    registration_offset = installer.index('if ! "$LSREGISTER" -f "$DESTINATION"')
    assert 'rm -rf "$DESTINATION"' not in installer
    assert 'BACKUP_DESTINATION' not in installer
    assert installer.index('rm -rf "$STAGED_DESTINATION"', registration_offset) > registration_offset
    assert 'expectedBundleIdentifier = "pro.2brain.graf.dev"' in lifecycle
    assert 'destination must not be a symlink' in lifecycle
    assert 'application.bundleIdentifier == expectedBundleIdentifier' in lifecycle
    assert "APP_STOP_TIMEOUT_SECONDS = 30" in harness
    assert "deadline = time.monotonic() + APP_STOP_TIMEOUT_SECONDS" in harness
    assert "if not self._app_is_running(destination):" in harness
    assert harness.count("if self._app_is_running(destination):") >= 2
    assert "check=True" in harness
    assert "def _atomic_swap_dev_app" in harness
    restore = harness[harness.index("    def _restore_app("):harness.index("    def _restore_runtime(")]
    assert "shutil.rmtree(destination)" not in restore
    assert "self._atomic_swap_dev_app(restored, destination)" in restore

    promote = harness[harness.index("    def promote("):harness.index("    def rollback(")]
    rollback = harness[harness.index("    def rollback("):]
    for transaction in (promote, rollback):
        assert transaction.index("previous_app_was_running = self._app_is_running") < transaction.index(
            "app_backup = self._snapshot_app()"
        )
