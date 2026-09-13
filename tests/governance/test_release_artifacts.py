"""Release retry contracts with synthetic files; never use Apple/Keychain credentials."""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import plistlib
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    'release_artifacts', ROOT / 'apps/macos/Installer/Scripts/release-artifacts.py')
artifacts = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(artifacts)


def test_fingerprint_covers_bytes_modes_and_links(tmp_path):
    (tmp_path / 'file').write_text('one')
    original = artifacts.fingerprint(tmp_path)
    (tmp_path / 'file').write_text('two')
    assert artifacts.fingerprint(tmp_path) != original
    (tmp_path / 'file').write_text('one')
    assert artifacts.fingerprint(tmp_path) == original
    (tmp_path / 'file').chmod(0o755)
    assert artifacts.fingerprint(tmp_path) != original
    (tmp_path / 'link').symlink_to('file')
    linked = artifacts.fingerprint(tmp_path)
    (tmp_path / 'link').unlink()
    (tmp_path / 'link').symlink_to('other')
    assert artifacts.fingerprint(tmp_path) != linked
    os.mkfifo(tmp_path / 'pipe')
    with pytest.raises(ValueError, match='unsupported'):
        artifacts.fingerprint(tmp_path)


def test_stage_resume_is_read_only_and_binds_entire_output(tmp_path):
    stage = tmp_path / 'stage'
    stage.mkdir()
    (stage / 'app.zip').write_bytes(b'original signed bytes')
    (stage / 'proof.json').write_text('{"checkedAt":"original"}')
    identity = {'version': '2026.09.13.3', 'source': 'a' * 40}
    artifacts.save_stage(stage, identity)
    before = artifacts.fingerprint(stage)
    artifacts.check_stage(stage, identity)
    assert artifacts.fingerprint(stage) == before
    with pytest.raises(ValueError, match='identity'):
        artifacts.check_stage(stage, {**identity, 'source': 'b' * 40})
    (stage / 'app.zip').write_bytes(b'resigned')
    with pytest.raises(ValueError, match='output'):
        artifacts.check_stage(stage, identity)


def test_failed_fsync_never_acknowledges_completion(tmp_path, monkeypatch):
    state = tmp_path / 'state.json'
    calls = []
    real = os.fsync

    def fail_directory(fd):
        calls.append(fd)
        if len(calls) == 2:
            raise OSError('disk failure')
        real(fd)

    monkeypatch.setattr(artifacts.os, 'fsync', fail_directory)
    with pytest.raises(OSError):
        artifacts.atomic_json(state, {'status': 'submitting'})
    # Preserve an ambiguous intent even when directory acknowledgement failed.
    assert json.loads(state.read_text())['status'] == 'submitting'


def test_lock_refuses_second_owner_and_releases(tmp_path):
    lock = tmp_path / 'lock'
    with artifacts.locked(lock):
        with pytest.raises(ValueError, match='in progress'):
            with artifacts.locked(lock):
                pass
    assert not lock.exists()


def test_swift_cache_tracks_toolchain_not_source(tmp_path, monkeypatch):
    for name in ('Package.swift', 'Package.resolved'):
        (tmp_path / name).write_text(name)
    monkeypatch.setattr(artifacts, 'MACOS', tmp_path)
    version = ['toolchain1']
    monkeypatch.setattr(artifacts, 'command', lambda *args: version[0] + str(args))
    original = artifacts.swift_key()
    (tmp_path / 'New.swift').write_text('changed source')
    assert artifacts.swift_key() == original
    (tmp_path / 'Package.resolved').write_text('new lock')
    assert artifacts.swift_key() != original
    changed_lock = artifacts.swift_key()
    version[0] = 'toolchain2'
    assert artifacts.swift_key() != changed_lock


def test_actual_builder_calls_swift_on_cache_hit(tmp_path):
    macos = tmp_path / 'apps/macos'
    scripts = macos / 'Installer/Scripts'
    scripts.mkdir(parents=True)
    for name in ('build-local-installer.sh', 'release-artifacts.py', 'release-signing-common.sh'):
        shutil.copyfile(artifacts.SCRIPTS / name, scripts / name)
    for name in ('Package.swift', 'Package.resolved'):
        (macos / name).write_text(name)
    binaries = tmp_path / 'bin'
    binaries.mkdir()
    log = tmp_path / 'calls'
    for name, body in {
        'swift': f'if [ "$1" = --version ]; then echo Swift-test; else echo "$*" >> "{log}"; exit 1; fi',
        'xcrun': 'echo SDK-test',
        'DevToolsSecurity': 'echo disabled',
    }.items():
        path = binaries / name
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
    environment = {**os.environ, 'PATH': f'{binaries}:{os.environ["PATH"]}', 'GRAF_VERSION': '2026.09.13.3',
                   'GRAF_INSTALLER_BUILD_DIR': str(tmp_path / 'package')}
    for _ in range(2):
        result = subprocess.run(['sh', str(scripts / 'build-local-installer.sh')], env=environment, capture_output=True)
        assert result.returncode != 0  # Deliberate compiler failure, no app is built/launched.
    calls = log.read_text().splitlines()
    assert len(calls) == 2 and calls[0] == calls[1]
    assert '/installer-cache/' in calls[0]
    assert not (macos / 'RecApp/.build/GRAF.app').exists()


def upload_fixture(tmp_path, monkeypatch):
    files = [tmp_path / name for name in ('app.zip', 'feed.xml', 'checksum', 'proof')]
    for path in files:
        path.write_text(path.name)
    release = {'repository': 'owner/repo', 'tag': 'v1', 'source': 'a' * 40, 'id': 1, 'draft': True}
    rows, calls = [], []
    context = {'releases': {'candidate': release}, 'inputs': []}
    monkeypatch.setattr(artifacts, 'release_snapshot', lambda *args: (dict(release), rows))

    def add(path):
        content = artifacts.regular(path)
        rows.append({'id': len(rows) + 1, 'state': 'uploaded', 'name': path.name,
                     'size': content['size'], 'digest': 'sha256:' + content['sha256']})

    def upload(*args):
        assert args[:5] == ('gh', '--repo', 'owner/repo', 'release', 'upload')
        assert '--clobber' not in args
        calls.append(args)
        add(Path(args[-1]))
        if len(calls) == 1:
            raise ValueError('interrupted upload response')
        return ''

    monkeypatch.setattr(artifacts, 'command', upload)
    return files, context, rows, calls, add


def test_upload_all_assets_preflight_and_resume(tmp_path, monkeypatch):
    files, context, rows, calls, add = upload_fixture(tmp_path, monkeypatch)
    add(files[-1])
    rows[0]['digest'] = 'sha256:' + '0' * 64
    with pytest.raises(ValueError, match='conflict'):
        artifacts.upload_missing(context, files)
    assert not calls
    rows.clear()
    add(files[-1])
    artifacts.upload_missing(context, files)
    assert len(calls) == 3
    artifacts.upload_missing(context, files)
    assert len(calls) == 3
    rows.append(dict(rows[0]))
    with pytest.raises(ValueError, match='duplicate'):
        artifacts.upload_missing(context, files)


def test_remote_without_digest_downloads_and_compares(tmp_path, monkeypatch):
    local = tmp_path / 'local'
    local.write_bytes(b'signed')
    asset = {'id': 1, 'state': 'uploaded', 'name': 'local', 'size': 6, 'digest': None}
    monkeypatch.setattr(artifacts, 'download_asset', lambda repo, row, output: Path(output).write_bytes(b'signed'))
    assert artifacts.remote_matches('owner/repo', asset, local)
    monkeypatch.setattr(artifacts, 'download_asset', lambda repo, row, output: Path(output).write_bytes(b'change'))
    assert not artifacts.remote_matches('owner/repo', asset, local)


def test_cached_input_identity_and_corruption_block(tmp_path, monkeypatch):
    asset = {'id': 1, 'state': 'uploaded', 'name': 'input.zip', 'size': 6, 'digest': None}
    release = {'tag': 'v1'}
    calls = []

    def download(repo, row, output):
        calls.append(row['id'])
        Path(output).write_bytes(b'signed')

    monkeypatch.setattr(artifacts, 'download_asset', download)
    path = artifacts.cached_asset('owner/repo', release, asset, tmp_path)
    assert artifacts.cached_asset('owner/repo', release, asset, tmp_path) == path
    assert calls == [1]
    with pytest.raises(ValueError, match='cached input'):
        artifacts.cached_asset('owner/repo', release, {**asset, 'id': 2}, tmp_path)
    path.write_bytes(b'broken')
    with pytest.raises(ValueError, match='cached input'):
        artifacts.cached_asset('owner/repo', release, asset, tmp_path)
    assert calls == [1]


def notary_fixture(tmp_path, monkeypatch):
    for kind in ('zip', 'pkg'):
        (tmp_path / f'submitted.{kind}').write_text(kind)
    state = {'inputs': {kind: artifacts.regular(tmp_path / f'submitted.{kind}') for kind in ('zip', 'pkg')}, 'jobs': {}}
    artifacts.atomic_json(tmp_path / 'requests.json', state)
    calls = []
    ids = {kind: f'00000000-0000-0000-0000-00000000000{i}' for i, kind in enumerate(('zip', 'pkg'), 1)}

    def apple(*args):
        calls.append(args)
        action = args[2]
        current = artifacts.read_json(tmp_path / 'requests.json')
        if action == 'submit':
            kind = Path(args[3]).suffix[1:]
            assert current['jobs'][kind] == {'status': 'submitting'}
            return json.dumps({'id': ids[kind]})
        assert len(current['jobs']) == 2
        assert all(job.get('id') for job in current['jobs'].values())
        return json.dumps({'id': args[3], 'status': 'Accepted'})

    monkeypatch.setattr(artifacts, 'command', apple)
    return state, calls, ids, apple


def test_notary_submits_both_before_wait_and_never_resubmits(tmp_path, monkeypatch):
    _, calls, _, apple = notary_fixture(tmp_path, monkeypatch)
    def interrupted(*args):
        if args[2] == 'info':
            raise ValueError('network failed after both durable IDs')
        return apple(*args)
    monkeypatch.setattr(artifacts, 'command', interrupted)
    with pytest.raises(ValueError):
        artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert [c[2] for c in calls] == ['submit', 'submit']
    monkeypatch.setattr(artifacts, 'command', apple)
    result = artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert all(job['status'] == 'Accepted' for job in result['jobs'].values())
    artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert [c[2] for c in calls] == ['submit', 'submit', 'info', 'info']


def test_ambiguous_notary_requires_digest_bound_recovery(tmp_path, monkeypatch):
    state, calls, ids, apple = notary_fixture(tmp_path, monkeypatch)
    state['jobs']['zip'] = {'status': 'submitting'}
    artifacts.atomic_json(tmp_path / 'requests.json', state)
    with pytest.raises(ValueError, match='ambiguous'):
        artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert calls == []
    monkeypatch.setattr(artifacts, 'command', lambda *args: json.dumps({'jobId': ids['zip'], 'sha256': '0' * 64}))
    with pytest.raises(ValueError, match='digest'):
        artifacts.notarize_jobs(tmp_path, 'fixture-profile', {'zip': ids['zip']})
    def recovered(*args):
        if args[2] == 'log':
            return json.dumps({'jobId': ids['zip'], 'sha256': state['inputs']['zip']['sha256']})
        return apple(*args)
    monkeypatch.setattr(artifacts, 'command', recovered)
    artifacts.notarize_jobs(tmp_path, 'fixture-profile', {'zip': ids['zip']})
    assert [c[3].suffix for c in calls if c[2] == 'submit'] == ['.pkg']


@pytest.mark.parametrize('status', ['Invalid', 'Rejected', 'In Progress', None])
def test_notary_nonaccepted_never_passes(tmp_path, monkeypatch, status):
    clock = iter((0, 2701))
    monkeypatch.setattr(artifacts.time, 'monotonic', lambda: next(clock))
    _, _, _, apple = notary_fixture(tmp_path, monkeypatch)
    def rejected(*args):
        if args[2] == 'submit':
            return apple(*args)
        return json.dumps({'id': args[3], 'status': status})
    monkeypatch.setattr(artifacts, 'command', rejected)
    with pytest.raises(ValueError, match='not accepted'):
        artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert all(job['status'] == 'submitted' for job in artifacts.read_json(tmp_path / 'requests.json')['jobs'].values())


def test_notary_polling_tracks_both_requests_without_long_wait(tmp_path, monkeypatch):
    _, calls, _, apple = notary_fixture(tmp_path, monkeypatch)
    pending = [True]
    def respond(*args):
        if args[2] == 'info' and pending[0]:
            return json.dumps({'id': args[3], 'status': 'In Progress'})
        return apple(*args)
    monkeypatch.setattr(artifacts, 'command', respond)
    monkeypatch.setattr(artifacts.time, 'sleep', lambda seconds: pending.__setitem__(0, False))
    result = artifacts.notarize_jobs(tmp_path, 'fixture-profile', {})
    assert {job['status'] for job in result['jobs'].values()} == {'Accepted'}
    assert [c[2] for c in calls] == ['submit', 'submit', 'info', 'info']


def test_notary_final_resume_preserves_submitted_bytes_after_failed_sync(tmp_path, monkeypatch, capsys):
    app = tmp_path / 'GRAF.app'
    app.mkdir()
    (app / 'signed-code').write_text('original')
    pkg = tmp_path / 'GRAF.pkg'
    pkg.write_text('original-package')
    version, source = '2026.09.13.3', 'a' * 40
    receipt = {'schema': 1, 'source': source, 'tag': 'v' + version, 'version': version,
               'app': artifacts.fingerprint(app), 'pkg': artifacts.regular(pkg)}
    artifacts.atomic_json(str(pkg) + '.build.json', receipt)
    monkeypatch.setattr(artifacts, 'STATE', tmp_path / 'state')
    monkeypatch.setattr(artifacts, 'clean_source', lambda expected=None: source)
    monkeypatch.setattr(artifacts, 'validate_signed_build', lambda *args: None)
    calls = []
    def platform(*args):
        calls.append(args)
        if args[0] == 'ditto':
            if '-c' in args:
                Path(args[-1]).write_text(json.dumps(artifacts.fingerprint(args[-2])))
            else:
                shutil.copytree(args[1], args[2])
        elif args[:3] == ('xcrun', 'stapler', 'staple'):
            path = Path(args[-1])
            if path.is_dir():
                (path / 'ticket').write_text('Accepted')
            else:
                path.write_text(path.read_text() + '-ticket')
        elif args[:3] == ('xcrun', 'notarytool', 'submit'):
            kind = Path(args[3]).suffix
            return json.dumps({'id': '00000000-0000-0000-0000-00000000000' + ('1' if kind == '.zip' else '2')})
        elif args[:3] == ('xcrun', 'notarytool', 'info'):
            return json.dumps({'id': args[3], 'status': 'Accepted'})
        return ''
    monkeypatch.setattr(artifacts, 'command', platform)
    directory = artifacts.STATE / 'notary' / f'{version}-{source}'
    final = directory / 'final'
    sync = artifacts.sync_dir
    failed = []
    def fail_once(path):
        if Path(path) == directory and final.exists() and not failed:
            failed.append(True)
            raise OSError('directory fsync failed')
        sync(path)
    monkeypatch.setattr(artifacts, 'sync_dir', fail_once)
    args = SimpleNamespace(app=app, pkg=pkg, profile='fixture-profile', recover=[])
    with pytest.raises(OSError, match='fsync'):
        artifacts.notarize(args)
    assert 'notary=Accepted final=' not in capsys.readouterr().out
    originals = artifacts.fingerprint(directory / 'GRAF.app'), artifacts.regular(directory / 'submitted.pkg')
    completed = artifacts.fingerprint(final)
    mutation_calls = [c for c in calls if c[0] == 'ditto' or c[:3] in
                      (('xcrun', 'notarytool', 'submit'), ('xcrun', 'stapler', 'staple'))]
    artifacts.notarize(args)
    assert 'notary=Accepted final=' in capsys.readouterr().out
    assert artifacts.fingerprint(final) == completed
    assert originals == (artifacts.fingerprint(directory / 'GRAF.app'), artifacts.regular(directory / 'submitted.pkg'))
    assert originals[0] == receipt['app']
    assert artifacts.fingerprint(final / 'GRAF.app') != receipt['app']
    assert mutation_calls == [c for c in calls if c[0] == 'ditto' or c[:3] in
                              (('xcrun', 'notarytool', 'submit'), ('xcrun', 'stapler', 'staple'))]
    (final / 'GRAF.app/ticket').write_text('changed')
    with pytest.raises(ValueError, match='output'):
        artifacts.notarize(args)


@pytest.mark.skipif(sys.platform != 'darwin', reason='actual macOS shell/plutil staging contract')
def test_actual_prepare_resume_never_rearchives_or_resigns(tmp_path):
    macos = tmp_path / 'apps/macos'
    scripts = macos / 'Installer/Scripts'
    scripts.mkdir(parents=True)
    for name in ('prepare-app-update.sh', 'release-artifacts.py', 'release-signing-common.sh',
                 'sign-graf-app-update-local.sh', 'verify-release-signing-custody.sh',
                 'derive-sparkle-public-key.swift'):
        shutil.copy2(artifacts.SCRIPTS / name, scripts / name)
    manifest = artifacts.SCRIPTS.parent / 'UpdateSigningKey.json'
    shutil.copyfile(manifest, scripts.parent / manifest.name)
    key = json.loads(manifest.read_text())['publicKey']
    version, source = '2026.09.13.3', 'a' * 40
    notes = tmp_path / 'notes.md'
    notes.write_text('Проверка продолжения выпуска.')
    app, previous = tmp_path / 'candidate/GRAF.app', tmp_path / 'previous/GRAF.app'
    for bundle, number in ((app, version), (previous, '2026.09.13.2')):
        (bundle / 'Contents').mkdir(parents=True)
        (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps({
            'CFBundleVersion': number, 'SUPublicEDKey': key,
            'SUFeedURL': 'https://example.test/downloads/graf-appcast.xml'}))
    proof = tmp_path / 'attestation.json'
    proof.write_text(json.dumps({'schemaVersion': 1, 'keyId': json.loads(manifest.read_text())['keyId'],
        'trustGeneration': 1, 'channel': 'macos-keychain', 'state': 'ready',
        'checkedAt': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        'releaseRef': 'v' + version, 'commit': source, 'workflow': 'verify-release-signing-custody-local',
        'evidenceId': '00000000-0000-4000-8000-000000000000'}))
    binaries = tmp_path / 'bin'
    sparkle = macos / '.build/artifacts/sparkle/Sparkle/bin'
    log = tmp_path / 'calls'
    stubs = {
        binaries / 'git': 'if [ "$1" = -C ]; then shift 2; fi\ncase "$1 $2" in\n'
            f'"rev-parse --show-toplevel") echo "{tmp_path}";;\n'
            f'"rev-parse "*) echo {source};;\n'
            f'"ls-remote "*) printf "{source}\\t%s\\n" "$3";;\n'
            '"status "*) ;;\n*) exit 9;;\nesac',
        binaries / 'ditto': 'echo archive >> "$GRAF_TEST_CALL_LOG"; printf zip > "${6}"',
        sparkle / 'generate_keys': f'echo keychain >> "$GRAF_TEST_CALL_LOG"; echo "{key}"',
        sparkle / 'sign_update': 'echo verify-signature >> "$GRAF_TEST_CALL_LOG"; test "${GRAF_TEST_BAD_SIGNATURE:-0}" = 0',
        sparkle / 'generate_appcast': 'echo sign >> "$GRAF_TEST_CALL_LOG"\nwhile [ "$1" != -o ]; do shift; done\n'
            f'printf \'<rss><channel><item><version>{version}</version><enclosure edSignature="fixture"/></item></channel></rss>\' > "$2"',
        macos / 'Scripts/validate-app-updates.sh': 'echo validate >> "$GRAF_TEST_CALL_LOG"\n'
            'test "$GRAF_REQUIRE_PUBLIC_UPDATE_TRUST" = 1 && test "${GRAF_TEST_BAD_TRUST:-0}" = 0',
        macos / 'Scripts/validate-packaged-app-launch.sh': 'exit 0',
    }
    for path, body in stubs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\n' + body + '\n')
        path.chmod(0o755)
    environment = {**os.environ, 'PATH': f'{binaries}:{os.environ["PATH"]}', 'GRAF_TEST_CALL_LOG': str(log),
        'GRAF_VERSION': version, 'GRAF_UPDATE_APP_BUNDLE': str(app), 'GRAF_PREVIOUS_APP_BUNDLE': str(previous),
        'GRAF_UPDATE_RELEASE_NOTES': str(notes), 'GRAF_UPDATE_DOWNLOAD_BASE_URL': 'https://example.test/downloads',
        'GRAF_REQUIRE_RELEASE_PROVENANCE': '1', 'GRAF_RELEASE_SIGNING_MODE': 'keychain',
        'GRAF_RELEASE_SIGNING_KEYCHAIN_ATTESTATION': str(proof)}
    def run(*args, **extra):
        return subprocess.run(['sh', str(scripts / 'prepare-app-update.sh'), *args],
                              env={**environment, **extra}, capture_output=True, text=True)
    helper = scripts / 'release-artifacts.py'
    helper.write_text(helper.read_text().replace(
        'def sync_dir(path):\n',
        'def sync_dir(path):\n'
        '    if Path(path).resolve() == STATE.resolve() and (STATE / "updates").exists():\n'
        '        with (STATE / "parent-sync-attempts").open("a") as log:\n'
        '            log.write("attempt\\n")\n'
        '        if os.environ.get("GRAF_TEST_FAIL_PARENT") == "1":\n'
        '            raise OSError("synthetic parent fsync failure")\n'))
    missing = run('--verify-only')
    assert missing.returncode and 'verification cannot create' in missing.stderr
    stage = macos / '.build/updates'
    result = run(GRAF_TEST_FAIL_PARENT='1')
    assert result.returncode and 'synthetic parent fsync failure' in result.stderr
    before = artifacts.fingerprint(stage)
    result = run(GRAF_TEST_FAIL_PARENT='1')
    assert result.returncode and 'synthetic parent fsync failure' in result.stderr
    assert (stage.parent / 'parent-sync-attempts').read_text().splitlines() == ['attempt'] * 2
    assert artifacts.fingerprint(stage) == before
    result = run()
    assert result.returncode == 0, result.stdout + result.stderr
    assert artifacts.fingerprint(stage) == before
    for args in ((), ('--verify-only',)):
        result = run(*args)
        assert result.returncode == 0, result.stdout + result.stderr
        assert artifacts.fingerprint(stage) == before
    calls = log.read_text().splitlines()
    assert calls.count('archive') == calls.count('sign') == 1
    assert calls.count('keychain') == 6
    for key_name in ('GRAF_TEST_BAD_TRUST', 'GRAF_TEST_BAD_SIGNATURE'):
        result = run(**{key_name: '1'})
        assert result.returncode != 0
        assert artifacts.fingerprint(stage) == before
    notes.write_text('Другие примечания.')
    result = run()
    assert result.returncode and 'identity differs' in result.stderr
    assert artifacts.fingerprint(stage) == before
    assert log.read_text().splitlines().count('archive') == 1


@pytest.mark.parametrize('failure', [None, 'public', 'startup', 'changed-output'])
def test_direct_upload_keeps_existing_public_gates(tmp_path, monkeypatch, failure):
    version, source = '2026.09.13.3', 'a' * 40
    monkeypatch.setattr(artifacts, 'STATE', tmp_path)
    monkeypatch.setattr(artifacts, 'clean_source', lambda expected=None: source)
    stage = tmp_path / 'updates'
    stage.mkdir()
    files = [stage / name for name in (f'GRAF-{version}.zip', 'graf-appcast.xml',
             f'GRAF-{version}.sha256', f'GRAF-{version}-signing-attestation.json')]
    for path in files:
        path.write_text(path.name)
    app = tmp_path / 'GRAF.app'
    (app / 'Contents').mkdir(parents=True)
    (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'SUFeedURL': 'https://example.test/graf-appcast.xml'}))
    context = tmp_path / 'context.json'
    context.write_text(json.dumps({'releases': {'candidate': {
        'repository': 'owner/repo', 'tag': 'v' + version, 'source': source, 'draft': True}}}))
    identity = {'inputs': 'bound by real stage hashes'}
    monkeypatch.setattr(artifacts, 'stage_identity', lambda args: identity)
    artifacts.save_stage(stage, identity)
    calls = []
    def checked(*args):
        calls.append(args)
        if args[:4] == ('git', 'remote', 'get-url', 'origin'):
            return 'git@github.com:owner/repo.git'
        if args[0] == 'env':
            assert args[-1] == '--verify-only'
            assert 'GRAF_REQUIRE_PUBLIC_UPDATE_TRUST=1' in args
            assert 'GRAF_REQUIRE_RELEASE_PROVENANCE=1' in args
            assert 'GRAF_RELEASE_SIGNING_MODE=keychain' in args
            if failure == 'public':
                raise ValueError('public trust rejected')
            if failure == 'changed-output':
                files[0].write_text('replaced during validation')
        elif failure == 'startup':
            raise ValueError('startup rejected')
        return ''
    monkeypatch.setattr(artifacts, 'command', checked)
    uploads = []
    monkeypatch.setattr(artifacts, 'upload_missing', lambda context, files: uploads.append(files))
    args = SimpleNamespace(context=context, app=app, previous=app, notes=context, files=files)
    if failure:
        with pytest.raises(ValueError):
            artifacts.upload_prepared(args)
        assert not uploads
    else:
        artifacts.upload_prepared(args)
        assert uploads == [files]
        assert [c[-1] for c in calls if str(c[0]).endswith('validate-packaged-app-launch.sh')] == ['arm64', 'x86_64']
