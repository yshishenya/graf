"""Contract tests for the one-command macOS app update release entrypoint.

The release entrypoint adds coordination, not trust.  These tests pin the parts
that are easy to get wrong when a manual sequence becomes one command: the
parameter surface, the safe dry-run, the mandatory gates it must still call, and
the publication order that keeps a client from seeing a feed item whose archive
does not exist yet.
"""
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / 'apps/macos/Installer/Scripts/release-app-update.sh'
SIGNER = SCRIPT.parent / 'sign-graf-app-update-local.sh'
ARTIFACTS = SCRIPT.parent / 'release-artifacts.py'


def run(*args, repo_root=None):
    command = ['sh', str(SCRIPT), *args]
    if repo_root is not None:
        command += ['--repo-root', str(repo_root)]
    return subprocess.run(command, capture_output=True, text=True)


def test_entrypoint_and_helpers_exist():
    assert SCRIPT.is_file(), 'the one-command release entrypoint must exist'
    assert SCRIPT.read_text().startswith('#!/usr/bin/env sh')
    # The entrypoint must delegate to the existing helpers, not reimplement them.
    source = SCRIPT.read_text()
    for helper in ('build-local-installer.sh', 'release-artifacts.py',
                   'sign-graf-app-update-local.sh', 'validate-app-updates.sh'):
        assert helper in source, f'{helper} must stay part of the release path'


def test_usage_failures_are_explicit():
    result = run()
    assert result.returncode == 64
    assert '--version' in result.stderr

    result = run('--version', '2026.09.18.1', '--phase', 'nonsense')
    assert result.returncode == 64
    assert '--phase' in result.stderr

    result = run('--version', '2026.09.18.1', '--unknown-flag')
    assert result.returncode == 64


def test_help_lists_every_documented_flag():
    result = run('--help')
    assert result.returncode == 0
    for flag in ('--version', '--phase', '--previous-tag', '--previous-app-asset',
                 '--candidate-app-asset', '--release-notes-asset', '--notes-file',
                 '--pkg', '--notary-profile', '--feed-url', '--app-sign-identity',
                 '--installer-identity', '--verify-feed', '--repo-root', '--dry-run'):
        assert flag in result.stderr, f'{flag} must stay documented'


def test_dry_run_plans_without_touching_anything(tmp_path):
    """A dry run may not build, call Apple, upload, or create a release."""
    result = run('--dry-run', '--version', '2026.09.18.1', repo_root=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    plan = result.stdout
    assert 'dry run' in plan
    assert '2026.09.18.1' in plan
    # The plan must state the trust steps and the publication boundary.
    for step in ('build_and_sign', 'notarize_wait_apple', 'staple_and_trust_gates',
                 'sparkle_sign_and_upload', 'feed_check'):
        assert step in plan, f'the plan must name {step}'
    assert 'never' in plan
    assert not list(tmp_path.glob('**/GRAF-*.pkg')), 'a dry run must not build'


def test_dry_run_reports_missing_prerequisites_instead_of_failing(tmp_path):
    """An operator should see every gap at once before a real run."""
    result = run('--dry-run', '--version', '2026.09.18.1', repo_root=tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'prerequisites failed' not in result.stderr
    # A bare temp directory resolves to no repository and no identities, so the
    # plan must name those gaps rather than silently promising a release.
    plan = result.stdout
    assert '<unresolved>' in plan or 'none found' in plan


def test_publish_and_all_delegate_to_the_existing_sparkle_signer():
    """The Sparkle signature must stay in the reviewed signer, never inline."""
    source = SCRIPT.read_text()
    assert 'sign-graf-app-update-local.sh' in source
    # The entrypoint passes exactly the signer's documented inputs.
    for flag in ('--release-tag', '--previous-tag', '--candidate-app-asset',
                 '--previous-app-asset', '--release-notes-asset'):
        assert flag in source, f'the signer input {flag} must be passed through'
        assert flag in SIGNER.read_text(), f'{flag} must remain a signer input'


def test_mandatory_gates_are_present_and_not_optional():
    """Every gate the owner listed must be enforced on the publication path."""
    source = SCRIPT.read_text()
    # Developer ID only, both artifacts, asserted before publication.
    assert 'Developer ID Application:' in source
    assert 'Developer ID Installer:' in source
    # Gatekeeper and stapler for the app and the package.
    assert source.count('spctl --assess') >= 4
    assert source.count('stapler validate') >= 4
    assert '--type execute' in source and '--type install' in source
    # The gates must be fatal, never advisory.
    assert 'fail "stapled app failed Gatekeeper assessment"' in source
    assert 'fail "stapled package failed Gatekeeper assessment"' in source
    # A non-notarized build may never reach publication.
    assert 'GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1' in source


def test_feed_is_never_replaced_by_this_command():
    """Replacing the public feed stays a deliberate separate owner action."""
    source = SCRIPT.read_text()
    assert 'never publishes to the public feed' in source
    assert 'production_feed=unchanged' in source
    # The canonical feed is only ever read, or named in a comment. Any copy,
    # move, install or upload of it would be an unintended publication.
    for write in ('cp ', 'mv ', 'install ', 'rsync ', 'scp ', 'gh release upload'):
        for line in source.splitlines():
            if 'graf-appcast.xml' in line and write in line:
                raise AssertionError(f'this command must not write the feed: {line.strip()}')
    assert re.search(r'curl[^\n]*"\$FEED_URL"', source), \
        'the feed must be reached read-only through curl'


def test_feed_check_asserts_version_and_reachability():
    """The closeout gate must prove the feed serves the new version."""
    source = SCRIPT.read_text()
    assert 'verify_live_feed' in source
    assert 'the live feed offers' in source
    # The archive must be reachable, not merely named.
    assert 'archive_http=200' in source
    assert 'has no HTTPS archive URL' in source
    assert "'%{http_code}'" in source or '%{http_code}' in source


def test_tag_check_runs_between_prepare_and_publish_for_all():
    """--phase all must not demand the tag before the build can start."""
    source = SCRIPT.read_text()
    # The tag gate is invoked in the main dispatch, after prepare.
    assert re.search(r'run_prepare\s*\n(.*\n)*?\s*check_published_tag', source), \
        'the published-tag gate must run after prepare in --phase all'
    # And it must not be part of the shared prerequisite block for prepare.
    assert re.search(r"case \"\$PHASE\" in\s*\n\s*publish\) check_published_tag", source)


def test_predecessor_lookup_ignores_server_only_releases():
    """A server-only tag carries no app ZIP and cannot be a signing input."""
    source = ARTIFACTS.read_text()
    assert 'def latest_app_release' in source
    # Drafts are never signing inputs.
    assert "row.get('draft')" in source
    # Only a release that actually publishes the app archive qualifies.
    assert 'f\'GRAF-{tag.removeprefix("v")}.zip\'' in source or \
        'GRAF-{tag.removeprefix("v")}.zip' in source
    assert "candidate.get('state') == 'uploaded'" in source


def test_script_is_posix_shell_clean():
    """It is run with sh, so it must not rely on bash-only syntax."""
    source = SCRIPT.read_text()
    for bashism in ('[[', 'function ', '${!', '<<<'):
        assert bashism not in source, f'POSIX sh must not use {bashism}'
    result = subprocess.run(['sh', '-n', str(SCRIPT)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
