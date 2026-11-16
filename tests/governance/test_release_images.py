from __future__ import annotations

import argparse
import copy
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import shutil
import signal
import ssl
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_images', ROOT / 'infra/scripts/release-images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


@pytest.fixture
def docker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv('TWOBRAIN_STRICT_STORAGE_SCOPE', 'test-scope')
    monkeypatch.setenv('TWOBRAIN_STRICT_STORAGE_RECOVERY_ID', '37fa06b9-7f96-4d80-8bb3-fd9fba90811d')
    source, previous = 'a'*40, 'b'*40
    old = {}
    refs = {}
    running = []
    services = ['rec-api', 'rec-processing-worker', 'rec-prompt-optimization-worker',
                'rec-migrate', 'rec-db-runtime-bootstrap', 'rec-maintenance', 'rec-media-worker',
                'rec-postgres', 'rec-temporal', 'rec-minio', 'rec-minio-init']
    for index, service in enumerate(services, 1):
        own = index <= 7
        old[service] = {'build': {'context': str(tmp_path), 'dockerfile': 'infra/server/Dockerfile',
                                **({'target': 'media-runtime'} if service == 'rec-media-worker' else {})}} if own else {'image': f'vendor/{service}:1'}
        if service in images.REQUIRED_CONSUMERS | {'rec-minio-init'}:
            old[service]['environment'] = {'TWOBRAIN_MINIO_BUCKET': 'test-ingest'}
        ref = f'twobrain-rec-{service}' if own else old[service]['image']
        iid = 'sha256:' + f'{index:064x}'
        info = dict(Id=iid, Os='linux', Architecture='amd64', Config=dict(Labels={}, Env=[]))
        refs[ref] = refs[iid] = info
        if service not in {'rec-migrate', 'rec-db-runtime-bootstrap', 'rec-minio-init', 'rec-prompt-optimization-worker'}:
            running.append(dict(Id=f'{index:064x}', Image=iid,
                                State=dict(Running=True, StartedAt='2026-11-10T04:00:00.123456789Z'),
                                Config=dict(Labels={'com.docker.compose.project': 'twobrain-rec',
                                                    'com.docker.compose.service': service})))
    new = copy.deepcopy(old)
    future = copy.deepcopy(old)
    calls = []
    state = dict(platform='linux/x86_64', fail=None, schema='0108_old', recovery_mode='reconciled',
                 postgres_id='7532000000000000001', minio_id='41c77879-1c96-45aa-9842-b6d97a88d996')
    def command(*args, input=None, timeout=None):
        calls.append(args)
        if state['fail'] and args[:len(state['fail'])] == state['fail']:
            raise ValueError('injected command failure')
        if args[:2] == ('git', 'rev-parse'):
            if '--git-path' not in args:
                return state.get('head', source)
            return str(tmp_path / ('deploy.lock' if args[-1] == 'twobrain-rec-deploy.lock' else '.state'))
        if args[:2] == ('git', 'status'):
            return ' M source' if state.get('dirty_after_build') and any(c[:2] == ('docker', 'build') for c in calls) else ''
        if args[:2] == ('git', 'show'):
            return 'old' if args[-1].startswith(previous) else 'future' if args[-1].startswith('3' * 40) else 'new'
        if args[:2] == ('git', 'merge-base'):
            assert args[2] == '--is-ancestor'
            return ''
        if args[:2] == ('git', 'diff'):
            assert args[2:4] == ('--name-only', '-z')
            return state.get('tracked_deploy_change', '')
        if args[:2] == ('docker', 'compose'):
            if args[:len(images.FORWARD_COMPOSE)] == images.FORWARD_COMPOSE:
                effective = copy.deepcopy(future)
                for name, service in json.loads(input)['services'].items():
                    effective[name].update(image=service['image'], pull_policy=service['pull_policy'])
                    if 'environment' in service:
                        effective[name]['environment'].update(service['environment'])
                if state.get('unsafe_launch_configuration'):
                    effective['rec-postgres']['image'] = 'different-image'
                return json.dumps(dict(name='twobrain-rec', services=effective))
            return json.dumps(dict(name='twobrain-rec', services={'old': old, 'new': new, 'future': future}[input]))
        if args[:2] == ('docker', 'info'):
            return state['platform']
        if args[:2] == ('docker', 'ps'):
            return '\n'.join(row['Id'] for row in running)
        if args[:2] == ('docker', 'inspect'):
            return json.dumps([row for row in running if row['Id'] in args[2:]])
        if args[:3] == ('docker', 'volume', 'inspect'):
            assert args[-1] == 'twobrain-rec-storage-recovery'
            return '[]'
        if args[:2] == ('docker', 'run'):
            assert '--read-only' in args and '--pull' in args and 'never' in args
            if 'print(packaged_schema_head())' in args[-1]:
                return state['packaged_schema']
            assert any('target=/run/graf-storage-recovery,readonly,volume-nocopy' in arg for arg in args)
            if state.get('failed_candidate_image') in args:
                return 'legacy'
            return state['recovery_mode']
        if args[:2] == ('docker', 'exec'):
            if args[-1] == '/data/.minio.sys/format.json':
                assert args[2] == next(
                    row['Id'] for row in running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-minio'
                )
                return json.dumps({'format': 'xl-single', 'id': state['minio_id']})
            assert 'default_transaction_read_only=on' in args[2]
            assert args[4] == next(
                row['Id'] for row in running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-postgres'
            )
            assert 'FROM pg_control_system() CROSS JOIN alembic_version' in args[-1]
            return state['postgres_id'] + '|' + state['schema']
        if args[:3] == ('docker', 'image', 'inspect'):
            if args[-1] not in refs:
                raise ValueError('missing image')
            return json.dumps([refs[args[-1]]])
        if args[:3] == ('docker', 'image', 'tag'):
            refs[args[-1]] = refs[args[-2]]
            return ''
        if args[:2] == ('docker', 'build'):
            target = args[args.index('--target') + 1]
            iid = 'sha256:' + ('c' if target == 'runtime' else 'd')*64
            refs[iid] = dict(Id=iid, Os='linux', Architecture='amd64',
                            Config=dict(Labels={images.SOURCE_LABEL: source}, Env=[f'GRAF_DEV_SOURCE_SHA={source}']))
            Path(args[args.index('--iidfile') + 1]).write_text(iid)
            return ''
        if args[:2] == ('docker', 'pull'):
            iid = 'sha256:' + 'e'*64
            refs[args[-1]] = refs[iid] = dict(Id=iid, Os='linux', Architecture='amd64', Config={})
            return ''
        raise AssertionError(args)
    monkeypatch.setattr(images, 'command', command)
    args = argparse.Namespace(source_sha=source, previous_sha=previous, candidate_id='rc-test',
                              decision_digest='sha256:'+'1'*64, full_digest='sha256:'+'2'*64,
                              attempt_id='1'*32, previous_schema='0108_old', candidate_schema='0109_new',
                              backup_reference=tmp_path / 'backup')
    return argparse.Namespace(args=args, refs=refs, running=running, old=old, new=new, future=future, calls=calls,
                              state=state, directory=tmp_path / '.state')


def test_two_builds_exact_previous_ids_and_same_source_retry(docker):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    baseline = images.read(attempt / 'baseline.json')
    candidate = images.read(attempt / 'candidate.json')
    assert len({row['image'] for row in baseline['images'].values()}) == 11
    assert len({row['image'] for row in candidate['images'].values() if row['target']}) == 2
    assert len([call for call in docker.calls if call[:2] == ('docker', 'build')]) == 2
    assert not any(call[:2] == ('docker', 'pull') for call in docker.calls)
    assert images.validate_override(attempt / 'override.json') == images.override(candidate['images'])
    assert images.read(attempt / 'identity.json')['full_digest'] == docker.args.full_digest
    assert (attempt / 'release-images.py').read_bytes() == (ROOT / 'infra/scripts/release-images.py').read_bytes()
    # Retain each old ID before the first build can alter any image ref.
    first_build = next(i for i, call in enumerate(docker.calls) if call[:2] == ('docker', 'build'))
    held = {call[-2] for call in docker.calls[:first_build] if call[:3] == ('docker', 'image', 'tag')}
    assert held == {row['image'] for row in baseline['images'].values()}
    images.finish(docker.directory, 'unchanged', docker.args.attempt_id)
    docker.calls.clear()
    docker.args.attempt_id = '2'*32
    images.prepare(docker.args)
    assert not any(call[:2] in {('docker', 'build'), ('docker', 'pull')} for call in docker.calls)


@pytest.mark.parametrize('failure', ['missing-previous', 'build', 'pull', 'source', 'platform', 'id', 'unfinished', 'wrong-project'])
def test_preparation_failures_preserve_runtime_and_incomplete_attempt(docker, failure):
    before = copy.deepcopy(docker.running)
    if failure == 'missing-previous':
        del docker.refs['twobrain-rec-rec-migrate']
    elif failure == 'wrong-project':
        docker.running[0]['Config']['Labels']['com.docker.compose.project'] = 'another-project'
        before = copy.deepcopy(docker.running)
    elif failure in {'build', 'pull'}:
        docker.state['fail'] = ('docker', failure)
        docker.new['rec-postgres']['image'] = 'vendor/rec-postgres:2'
    else:
        images.prepare(docker.args)
        original = images.active(docker.directory)
        if failure != 'unfinished':
            images.finish(docker.directory, 'unchanged', docker.args.attempt_id)
            if failure == 'source':
                docker.refs['sha256:'+'c'*64]['Config']['Labels'][images.SOURCE_LABEL] = 'f'*40
            elif failure == 'id':
                docker.refs['sha256:'+'c'*64]['Id'] = 'sha256:'+'f'*64
            else:
                docker.refs['sha256:'+'c'*64]['Architecture'] = 'arm64'
        docker.args.attempt_id = '2'*32
    with pytest.raises(ValueError):
        images.prepare(docker.args)
    assert docker.running == before
    if failure == 'unfinished':
        assert images.active(docker.directory) == original
        with pytest.raises(ValueError, match='another deployment'):
            images.finish(docker.directory, 'unchanged', docker.args.attempt_id)
    assert not any(call[:3] in {('docker', 'compose', 'stop'), ('docker', 'compose', 'up')} for call in docker.calls)


def test_changed_third_party_ref_is_prepared_without_changing_previous(docker):
    docker.new['rec-postgres']['image'] = 'vendor/rec-postgres:2'
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    assert len([c for c in docker.calls if c[:2] == ('docker', 'pull')]) == 1
    old = images.read(attempt / 'baseline.json')['images']['rec-postgres']['image']
    new = images.read(attempt / 'candidate.json')['images']['rec-postgres']['image']
    assert old != new


def test_finish_requires_actual_runtime_and_preserves_failed_result(docker, monkeypatch):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    with pytest.raises(ValueError, match='runtime image mismatch'):
        images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert not (attempt / 'result.json').exists()
    candidate = images.read(attempt / 'candidate.json')['images']
    for row in docker.running:
        row['Image'] = candidate[row['Config']['Labels']['com.docker.compose.service']]['image']
    with pytest.raises(ValueError, match='runtime changed'):
        images.finish(docker.directory, 'unchanged', docker.args.attempt_id)
    real_fsync = images.os.fsync
    def disk_failure(fd):
        import stat
        if stat.S_ISDIR(images.os.fstat(fd).st_mode):
            raise OSError('injected persistence failure')
        return real_fsync(fd)
    monkeypatch.setattr(images.os, 'fsync', disk_failure)
    with pytest.raises(OSError):
        images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert not (attempt / 'result.json').exists()
    monkeypatch.setattr(images.os, 'fsync', real_fsync)
    images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert images.read(attempt / 'result.json')['result'] == 'deployed'


def test_disk_full_before_active_attempt_never_builds(docker, monkeypatch):
    monkeypatch.setattr(images.os, 'fsync', lambda _fd: (_ for _ in ()).throw(OSError('disk full')))
    with pytest.raises(OSError):
        images.prepare(docker.args)
    assert not (docker.directory / 'active.json').exists()
    assert not any(c[:2] in {('docker', 'build'), ('docker', 'pull')} for c in docker.calls)


@pytest.mark.parametrize('service', ['rec-processing-worker', 'rec-maintenance'])
def test_deployed_requires_consumers_that_were_already_stopped(docker, service):
    for row in docker.running:
        if row['Config']['Labels']['com.docker.compose.service'] == service:
            row['State']['Running'] = False
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    candidate = images.read(attempt / 'candidate.json')['images']
    for row in docker.running:
        row['Image'] = candidate[row['Config']['Labels']['com.docker.compose.service']]['image']
    with pytest.raises(ValueError, match='recovered runtime is incomplete'):
        images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert not (attempt / 'result.json').exists()


def test_activated_boundary_survives_restart_and_blocks_old_side(docker):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    with pytest.raises(ValueError, match='another deployment'):
        wrong_attempt = argparse.Namespace(**(vars(docker.args) | {'attempt_id': '2' * 32}))
        images.forbid_rollback(attempt, wrong_attempt)
    images.forbid_rollback(attempt, docker.args)
    binding = json.dumps(['test-scope', '37fa06b9-7f96-4d80-8bb3-fd9fba90811d']).encode()
    assert images.read(attempt / images.NO_ROLLBACK) == {
        'schema_version': 3, 'previous_schema': '0108_old', 'candidate_schema': '0109_new',
        'backup_reference': str(docker.args.backup_reference),
        'binding_sha256': hashlib.sha256(binding).hexdigest(),
        'stores_sha256': hashlib.sha256(json.dumps([docker.state['postgres_id'], docker.state['minio_id']]).encode()).hexdigest(),
        'baseline_sha256': hashlib.sha256((attempt / 'baseline.json').read_bytes()).hexdigest(),
        'candidate_sha256': hashlib.sha256((attempt / 'candidate.json').read_bytes()).hexdigest(),
        'identity_sha256': hashlib.sha256((attempt / 'identity.json').read_bytes()).hexdigest(),
    }
    with pytest.raises(ValueError, match='create-once'):
        images.forbid_rollback(attempt, docker.args)
    for outcome in ('unchanged', 'restored'):
        with pytest.raises(ValueError, match='requires forward recovery'):
            images.finish(docker.directory, outcome, docker.args.attempt_id)
    assert not (attempt / 'result.json').exists()
    candidate = images.read(attempt / 'candidate.json')['images']
    for row in docker.running:
        row['Image'] = candidate[row['Config']['Labels']['com.docker.compose.service']]['image']
    images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert images.read(attempt / 'result.json')['result'] == 'deployed'


def test_activated_boundary_refuses_to_proceed_if_attempt_directory_is_not_durable(docker, monkeypatch):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    real_sync_directory = images.sync_directory

    def sync_directory(path):
        if path == attempt.parent:
            raise OSError('attempt directory entry was not synced')
        real_sync_directory(path)

    monkeypatch.setattr(images, 'sync_directory', sync_directory)
    with pytest.raises(OSError, match='attempt directory entry'):
        images.forbid_rollback(attempt, docker.args)
    # The operation could have persisted its marker even though it failed.
    with pytest.raises(ValueError, match='requires forward recovery'):
        images.finish(docker.directory, 'unchanged', docker.args.attempt_id)


def test_standalone_uses_completed_current_images_and_blocks_incomplete(docker):
    assert images.current_override() is None
    images.prepare(docker.args)
    with pytest.raises(ValueError, match='unfinished deployment'):
        images.current_override()
    candidate = images.read(images.active(docker.directory) / 'candidate.json')['images']
    for row in docker.running:
        row['Image'] = candidate[row['Config']['Labels']['com.docker.compose.service']]['image']
    images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    path = images.current_override()
    assert path.name == 'override.json'
    docker.running[0]['Image'] = 'sha256:'+'f'*64
    with pytest.raises(ValueError, match='runtime image mismatch'):
        images.current_override()


def test_protected_predecessor_requires_live_candidate_not_just_result(docker):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    images.forbid_rollback(attempt, docker.args)
    candidate = images.read(attempt / 'candidate.json')['images']
    for row in docker.running:
        row['Image'] = candidate[row['Config']['Labels']['com.docker.compose.service']]['image']
    images.finish(docker.directory, 'deployed', docker.args.attempt_id)
    assert images.recorded_images(docker.directory, docker.args.source_sha) == candidate
    with pytest.raises(ValueError, match='source differs'):
        images.recorded_images(docker.directory, docker.args.previous_sha)
    docker.running[1]['State']['Running'] = False
    with pytest.raises(ValueError, match='runtime is incomplete'):
        images.recorded_images(docker.directory, docker.args.source_sha)
    with pytest.raises(ValueError, match='runtime is incomplete'):
        images.current_override()
    docker.running[1]['State']['Running'] = True
    storage = next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-minio')
    storage_image = storage['Image']
    storage['Image'] = 'sha256:' + 'f' * 64
    with pytest.raises(ValueError, match='runtime image mismatch'):
        images.recorded_images(docker.directory, docker.args.source_sha)
    storage['Image'] = storage_image
    identity = attempt / 'identity.json'
    images.write(identity, {**images.read(identity), 'candidate_id': 'rc-different'})
    with pytest.raises(ValueError, match='evidence does not match'):
        images.recorded_images(docker.directory, docker.args.source_sha)


def test_remote_checks_predecessor_before_reset_using_candidate_helper(tmp_path):
    def git(*args):
        return subprocess.check_output(
            ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', *args],
            cwd=tmp_path, text=True, stderr=subprocess.PIPE,
        ).strip()

    git('init', '-q')
    helper = tmp_path / 'infra/scripts/release-images.py'
    helper.parent.mkdir(parents=True)
    helper.write_text('raise SystemExit(2)\n')
    git('add', '.')
    git('commit', '-qm', 'previous')
    previous = git('rev-parse', 'HEAD')
    helper.write_bytes((ROOT / 'infra/scripts/release-images.py').read_bytes())
    git('add', '.')
    git('commit', '-qm', 'candidate')
    expected = git('rev-parse', 'HEAD')
    git('checkout', '-q', '--detach', previous)
    state = tmp_path / git('rev-parse', '--git-path', 'graf-release-images')
    attempt = state / 'attempts' / ('1' * 32)
    images.write(state / 'active.json', {'attempt': attempt.name})
    images.write(attempt / 'baseline.json', {'source_sha': previous, 'images': {}})
    script = (ROOT / 'infra/scripts/cd-remote.sh').read_text()
    start = script.index('git cat-file -e "$expected_sha^{commit}"')
    ordinary = script.index('check-predecessor --previous-sha', start)
    end = script.index('TWOBRAIN_PRODUCTION_RELEASE_GATE=1', ordinary)
    preflight = '''
set -eu
expected_sha="$1"
previous_sha="$2"
python3_bin="$3"
mode=execute
python3() {
  [ "${GRAF_FIXTURE_PREDECESSOR:-}" = "verified-env" ] || return 94
  "$python3_bin" "$@"
}
'''
    command = ['bash', '-c', preflight + script[start:end], 'release-test', expected, previous, sys.executable]
    env_path = tmp_path / '.env'
    env_path.write_text('GRAF_FIXTURE_PREDECESSOR=verified-env\n')
    blocked = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
    assert blocked.returncode == 1
    assert 'reason=release_predecessor_unverified' in blocked.stdout
    assert 'unfinished deployment' in blocked.stderr
    assert git('rev-parse', 'HEAD') == previous
    assert helper.read_text() == 'raise SystemExit(2)\n'
    images.write(attempt / 'result.json', {'result': 'unchanged'})
    for invalid in ('exit 0', 'false'):
        env_path.write_text(f'{invalid}\nGRAF_FIXTURE_PREDECESSOR=verified-env\n')
        refused = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
        assert refused.returncode == 1 and 'reason=release_predecessor_unverified' in refused.stdout
        assert git('rev-parse', 'HEAD') == previous
    env_path.write_text('GRAF_FIXTURE_PREDECESSOR=verified-env\n')
    passed = subprocess.run(command, cwd=tmp_path, text=True, capture_output=True)
    assert passed.returncode == 0, passed.stderr
    assert git('rev-parse', 'HEAD') == expected


@pytest.mark.parametrize(('case', 'error'), [
    ('old-schema', None),
    ('new-schema', None),
    ('wrong-attempt', 'not active'),
    ('wrong-source', 'not the exact clean checkout'),
    ('wrong-binding', 'binding differs'),
    ('unknown-smoke-cleanup', 'smoke cleanup is unknown'),
    ('missing-volume', 'injected command failure'),
    ('unverified-volume', 'storage recovery volume is unverified'),
    ('legacy-volume', 'activated storage recovery volume is unverified'),
    ('replacement-postgres', 'storage identity changed'),
    ('replacement-minio', 'storage identity changed'),
    ('running-consumer', 'consumers must be stopped'),
    ('oneoff', 'one-off release operation'),
    ('restarting-infra', 'restarting or paused'),
    ('paused-infra', 'restarting or paused'),
    ('wrong-image', 'unrecorded infrastructure image'),
    ('unknown-schema', 'schema was not recorded'),
    ('multiple-heads', 'schema is not unique'),
])
def test_forward_baseline_does_not_need_running_api_or_mutate_attempt(docker, monkeypatch, case, error):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    images.forbid_rollback(attempt, docker.args)
    docker.state['schema'] = {
        'old-schema': docker.args.previous_schema,
        'unknown-schema': 'unknown_head',
        'multiple-heads': 'head_one\nhead_two',
    }.get(case, docker.args.candidate_schema)
    for row in docker.running:
        service = row['Config']['Labels']['com.docker.compose.service']
        row['State']['Running'] = service in images.INFRASTRUCTURE_SERVICES
        if case == 'wrong-image' and service == 'rec-minio':
            row['Image'] = 'sha256:' + 'f' * 64
        if service == 'rec-minio' and case in ('restarting-infra', 'paused-infra'):
            row['State']['Restarting' if case == 'restarting-infra' else 'Paused'] = True
        if case in ('running-consumer', 'oneoff') and service == 'rec-api':
            row['State']['Running'] = True
            if case == 'oneoff':
                row['Config']['Labels']['com.docker.compose.oneoff'] = 'True'
    if case == 'unknown-smoke-cleanup':
        images.write(attempt / 'forward-smoke-started.json', {'run_id': 'forward-example'})
    if case == 'wrong-binding':
        monkeypatch.setenv('TWOBRAIN_STRICT_STORAGE_SCOPE', 'different-scope')
    if case == 'missing-volume':
        docker.state['fail'] = ('docker', 'volume', 'inspect')
    if case == 'unverified-volume':
        docker.state['recovery_mode'] = 'recovery_unknown'
    if case == 'legacy-volume':
        docker.state['recovery_mode'] = 'legacy'
    if case == 'replacement-postgres':
        docker.state['postgres_id'] = '7532000000000000002'
    if case == 'replacement-minio':
        docker.state['minio_id'] = '80f08a38-68ea-4925-b31c-c9157ece9aca'
    failed_id = '2' * 32 if case == 'wrong-attempt' else attempt.name
    failed_sha = docker.args.previous_sha if case == 'wrong-source' else docker.args.source_sha
    before = copy.deepcopy(docker.running)
    docker.calls.clear()
    if error:
        with pytest.raises(ValueError, match=error):
            images.check_forward_baseline(docker.directory, failed_id, failed_sha)
    else:
        assert images.check_forward_baseline(docker.directory, failed_id, failed_sha) == docker.state['schema']
    assert images.active(docker.directory) == attempt
    assert not (attempt / 'result.json').exists()
    assert docker.running == before
    assert {call[1] for call in docker.calls if call[0] == 'docker'} <= {'info', 'ps', 'inspect', 'exec', 'volume', 'run'}
    if case == 'missing-volume':
        assert not any(call[:2] == ('docker', 'run') for call in docker.calls)


@pytest.mark.parametrize(('case', 'error'), [
    ('matching', None),
    ('same-source', 'requires a new source'),
    ('unrelated-source', 'injected command failure'),
    ('wrong-image-source', 'image source mismatch'),
    ('different-schema', 'different database schema'),
    ('cannot-read-recovery-volume', 'did not verify the live storage volume'),
])
def test_forward_candidate_checks_source_schema_and_live_volume_without_adopting(docker, case, error):
    images.prepare(docker.args)
    attempt = images.active(docker.directory)
    images.forbid_rollback(attempt, docker.args)
    for row in docker.running:
        service = row['Config']['Labels']['com.docker.compose.service']
        row['State']['Running'] = service in images.INFRASTRUCTURE_SERVICES
    source = docker.args.source_sha if case == 'same-source' else '3' * 40
    image_id = 'sha256:' + '4' * 64
    labelled_source = '5' * 40 if case == 'wrong-image-source' else source
    docker.refs[image_id] = dict(
        Id=image_id, Os='linux', Architecture='amd64',
        Config=dict(Labels={images.SOURCE_LABEL: labelled_source, images.TARGET_LABEL: 'media-runtime'},
                    Env=[f'GRAF_DEV_SOURCE_SHA={labelled_source}']),
    )
    docker.state['packaged_schema'] = 'different' if case == 'different-schema' else docker.state['schema']
    if case == 'unrelated-source':
        docker.state['fail'] = ('git', 'merge-base')
    if case == 'cannot-read-recovery-volume':
        docker.state['failed_candidate_image'] = image_id
    request = argparse.Namespace(failed_attempt=attempt.name, failed_sha=docker.args.source_sha,
                                 source_sha=source, image=image_id)
    docker.calls.clear()
    if error:
        with pytest.raises(ValueError, match=error):
            images.check_forward_candidate(docker.directory, request)
    else:
        assert images.check_forward_candidate(docker.directory, request) == docker.state['schema']
    assert images.active(docker.directory) == attempt
    assert not (attempt / 'result.json').exists()
    assert not any(call[:2] in {('docker', 'build'), ('docker', 'compose'), ('git', 'reset')} for call in docker.calls)


@pytest.mark.parametrize(('case', 'error'), [
    ('matching', None),
    ('bad-decision', 'invalid forward release evidence'),
    ('wrong-lock', 'does not identify the deployment lock'),
    ('busy-lock', 'temporarily unavailable'),
    ('changed-infrastructure', 'changes infrastructure configuration'),
    ('changed-app-settings', 'changes Compose configuration'),
    ('wrong-runtime-image', 'image source mismatch'),
    ('same-sha-wrong-target', 'image build target mismatch'),
    ('tracked-env-file', 'changes tracked deployment inputs'),
    ('retain-failure', 'injected command failure'),
    ('no-stop', 'forward stop receipt is required'),
])
def test_stage_forward_pins_both_targets_without_switching_active(docker, case, error):
    images.prepare(docker.args)
    failed = images.active(docker.directory)
    images.forbid_rollback(failed, docker.args)
    for row in docker.running:
        name = row['Config']['Labels']['com.docker.compose.service']
        row['State']['Running'] = name in images.INFRASTRUCTURE_SERVICES
    source = '3' * 40
    for tag in ('4', '5'):
        image_id = 'sha256:' + tag * 64
        image_source = '6' * 40 if tag == '5' and case == 'wrong-runtime-image' else source
        target = 'media-runtime' if tag == '4' or case == 'same-sha-wrong-target' else 'runtime'
        docker.refs[image_id] = dict(
            Id=image_id, Os='linux', Architecture='amd64',
            Config=dict(Labels={images.SOURCE_LABEL: image_source, images.TARGET_LABEL: target},
                        Env=[f'GRAF_DEV_SOURCE_SHA={image_source}']),
        )
    docker.state['packaged_schema'] = docker.state['schema']
    if case == 'changed-infrastructure':
        docker.future['rec-minio']['volumes'] = [{'source': 'different-store'}]
    if case == 'changed-app-settings':
        docker.future['rec-api']['environment'] = {'TWOBRAIN_MINIO_ENDPOINT': 'other'}
    if case == 'retain-failure':
        docker.state['fail'] = ('docker', 'image', 'tag')
    if case == 'tracked-env-file':
        docker.state['tracked_deploy_change'] = 'infra/env/rec.production.env.example\0'
    request = argparse.Namespace(
        failed_attempt=failed.name, failed_sha=docker.args.source_sha, source_sha=source,
        image='sha256:' + '4' * 64, runtime_image='sha256:' + '5' * 64,
        attempt_id='2' * 32, candidate_id='rc-forward',
        decision_digest='bad' if case == 'bad-decision' else docker.args.decision_digest,
        full_digest=docker.args.full_digest,
    )
    stage = docker.directory / 'attempts' / request.attempt_id
    lock = Path.cwd() / 'deploy.lock'
    if case != 'no-stop':
        with lock.open('ab') as handle:
            images.record_start_intent(docker.directory, failed.name, handle.fileno())
            images.record_forward_stop(docker.directory, operator_stop_request(failed, handle))
    before = attempt_files(failed)
    request_lock = Path.cwd() / 'other.lock' if case == 'wrong-lock' else lock
    docker.calls.clear()
    with lock.open('ab') as holder, request_lock.open('ab') as handle:
        request.deployment_lock_fd = handle.fileno()
        if case == 'busy-lock':
            fcntl.flock(holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with pytest.raises(BlockingIOError):
                images.stage_forward(docker.directory, request)
        elif error:
            with pytest.raises(ValueError, match=error):
                images.stage_forward(docker.directory, request)
        else:
            assert images.stage_forward(docker.directory, request) == stage
            staged = images.read(stage / 'forward-stage.json')
            assert staged['failed_attempt'] == failed.name and staged['source_sha'] == source
            assert staged['images']['rec-api']['image'] == request.runtime_image
            assert staged['images']['rec-media-worker']['image'] == request.image
            assert staged['schema'] == docker.state['schema']
            assert set(staged['infrastructure']) == images.INFRASTRUCTURE_SERVICES
            assert not (stage / 'result.json').exists()
            with pytest.raises(ValueError, match='create-once'):
                images.stage_forward(docker.directory, request)
    assert stage.exists() is (error is None)
    assert images.active(docker.directory) == failed
    assert attempt_files(failed) == before
    assert not any(call[:2] in {('git', 'reset'), ('docker', 'pull'), ('docker', 'build')} for call in docker.calls)
    assert not any(call[:2] == ('docker', 'compose') and call[-3:] != ('config', '--format', 'json')
                   for call in docker.calls)


def write_backup_files(root):
    root.mkdir(mode=0o700)
    objects = root / 'minio-objects'
    objects.mkdir(mode=0o700)
    for path in [*(root / name for name in ('postgres.dump', 'schema.sql', 'inventory.jsonl', 'checksums.sha256')),
                 objects / 'synthetic-object']:
        path.write_text('synthetic content')
        path.chmod(0o600)
    inventory = root / 'minio-inventory.jsonl'
    inventory.write_text(json.dumps(dict(schema=1, bucket='test-ingest', versioning='disabled', incomplete=0)) + '\n' +
                         json.dumps(dict(key='synthetic-object', sha256=hashlib.sha256(b'synthetic content').hexdigest())) + '\n')
    inventory.chmod(0o600)


@pytest.mark.parametrize(('case', 'error'), [
    ('success', None),
    ('existing-dir', 'new canonical directory'),
    ('backup-failed', 'synthetic backup failure'),
    ('wrong-receipt', 'did not confirm this destination'),
    ('broken-inventory', 'synthetic inventory failure'),
    ('missing-artifact', 'backup is incomplete'),
    ('linked-object', 'non-regular or linked file'),
    ('db-replaced', 'forward stop receipt no longer matches'),
    ('stage-changed', 'staged release changed during backup'),
])
def test_backup_forward_verifies_fresh_copy_of_pinned_stores_before_recording(docker, monkeypatch, case, error):
    images.prepare(docker.args)
    failed = images.active(docker.directory)
    images.forbid_rollback(failed, docker.args)
    for row in docker.running:
        row['State']['Running'] = row['Config']['Labels']['com.docker.compose.service'] in images.INFRASTRUCTURE_SERVICES
    source = '3' * 40
    for tag, target in [('4', 'media-runtime'), ('5', 'runtime')]:
        identity = 'sha256:' + tag * 64
        docker.refs[identity] = dict(
            Id=identity, Os='linux', Architecture='amd64',
            Config=dict(Labels={images.SOURCE_LABEL: source, images.TARGET_LABEL: target},
                        Env=[f'GRAF_DEV_SOURCE_SHA={source}']),
        )
    docker.state['packaged_schema'] = docker.state['schema']
    args = argparse.Namespace(
        failed_attempt=failed.name, failed_sha=docker.args.source_sha, source_sha=source,
        image='sha256:' + '4' * 64, runtime_image='sha256:' + '5' * 64,
        attempt_id='2' * 32, candidate_id='rc-forward', decision_digest=docker.args.decision_digest,
        full_digest=docker.args.full_digest, backup_directory=Path.cwd() / 'fresh-backup',
    )
    command = images.command
    with (Path.cwd() / 'deploy.lock').open('ab') as descriptor:
        args.deployment_lock_fd = descriptor.fileno()
        images.record_start_intent(docker.directory, failed.name, descriptor.fileno())
        images.record_forward_stop(docker.directory, operator_stop_request(failed, descriptor))
        staged = images.stage_forward(docker.directory, args)
        stage_data = images.read(staged / 'forward-stage.json')
        if case == 'existing-dir':
            args.backup_directory.mkdir()

        def run(*argv, input=None, env=None):
            if argv[:2] == ('sh', 'infra/scripts/backup-rec-stack.sh'):
                assert argv[2:] == ('--execute', '--pinned-stores', *(
                    stage_data['infrastructure'][service]['id'] for service in ('rec-postgres', 'rec-minio')
                ), 'test-ingest')
                assert env['GRAF_RELEASE_MC_IMAGE'] == stage_data['images']['rec-minio-init']['image']
                assert env['TWOBRAIN_BACKUP_DIR'] == str(args.backup_directory)
                if case == 'backup-failed':
                    raise ValueError('synthetic backup failure')
                write_backup_files(args.backup_directory)
                if case == 'missing-artifact':
                    (args.backup_directory / 'postgres.dump').unlink()
                if case == 'linked-object':
                    (args.backup_directory / 'minio-objects' / 'linked').symlink_to(args.backup_directory / 'schema.sql')
                if case == 'db-replaced':
                    next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service']
                         == 'rec-postgres')['Id'] = 'c' * 64
                if case == 'stage-changed':
                    images.write(staged / 'forward-stage.json', {**stage_data, 'candidate_id': 'rc-other'})
                return 'backup_result=pass\nbackup_reference=' + (
                    '/old-backup' if case == 'wrong-receipt' else str(args.backup_directory)
                )
            if argv[:2] == ('python3', 'infra/scripts/rec-db-verify.py'):
                assert argv[2:] == (str(args.backup_directory), '--inventory')
                if case == 'broken-inventory':
                    raise ValueError('synthetic inventory failure')
                return ''
            return command(*argv, input=input)

        monkeypatch.setattr(images, 'command', run)
        if error:
            with pytest.raises(ValueError, match=error):
                images.backup_forward(docker.directory, args)
            assert not (staged / 'forward-backup.json').exists()
        else:
            receipt = images.read(images.backup_forward(docker.directory, args))
            assert receipt['stage_sha256'] == images.attempt_digest(staged, 'forward-stage')
            assert receipt['bucket'] == 'test-ingest'
            assert receipt['contents_sha256'] == images.backup_contents(args.backup_directory, 'test-ingest')
            manifest = args.backup_directory / 'minio-inventory.jsonl'
            args.rehearsal_copy = args.backup_directory.parent / 'rehearsal-copy'
            args.rehearsal_copy.mkdir()
            for artifact in args.backup_directory.iterdir():
                if artifact.is_file():
                    (args.rehearsal_copy / artifact.name).write_bytes(artifact.read_bytes())
            assert images.check_forward_backup(docker.directory, args) == stage_data['images']['rec-minio-init']['image']
            for artifact in ('minio-inventory.jsonl', 'postgres.dump'):
                replay = args.rehearsal_copy / artifact
                original = replay.read_bytes()
                replay.write_bytes(original + b' ')
                with pytest.raises(ValueError, match='rehearsal file differs'):
                    images.check_forward_backup(docker.directory, args)
                replay.write_bytes(original)
            for folder in (args.backup_directory, args.rehearsal_copy):
                (folder / 'postgres.dump').write_text('not the original dump')
            with pytest.raises(ValueError, match='archive does not match its receipt'):
                images.check_forward_backup(docker.directory, args)
            for folder in (args.backup_directory, args.rehearsal_copy):
                (folder / 'postgres.dump').write_text('synthetic content')
            manifest.unlink()
            with pytest.raises(ValueError, match='backup is incomplete'):
                images.check_forward_backup(docker.directory, args)
            manifest.write_bytes((args.rehearsal_copy / manifest.name).read_bytes())
            manifest.chmod(0o600)
            (args.backup_directory / 'minio-objects' / 'synthetic-object').write_text('synthetic xontent')
            with pytest.raises(ValueError, match='object differs from the pinned source'):
                images.backup_contents(args.backup_directory, 'test-ingest')
            with pytest.raises(ValueError, match='create-once'):
                images.backup_forward(docker.directory, args)
    assert images.active(docker.directory) == failed
    assert not (failed / 'result.json').exists()


def attempt_files(attempt):
    return {file.relative_to(attempt): file.read_bytes() for file in attempt.rglob('*') if file.is_file()}


def operator_stop_request(attempt, lock, *, capture=True):
    state = attempt.parent.parent
    args = argparse.Namespace(failed_attempt=attempt.name, failed_sha=images.read(attempt / 'identity.json')['source_sha'],
                              operator_record=state / 'operator-record.json', deployment_lock_fd=lock.fileno())
    proposal = images.forward_stop_snapshot(state, args)[1] if capture else {}
    if "storage_writes_quiesced" in proposal:
        proposal["storage_writes_quiesced"] = True
    images.write(args.operator_record, dict(proposal, docker_operations_quiesced=True))
    return args


@pytest.fixture
def activated_fixture(docker):
    images.prepare(docker.args)
    failed = images.active(docker.directory)
    images.forbid_rollback(failed, docker.args)
    for row in docker.running:
        row['State']['Running'] = row['Config']['Labels']['com.docker.compose.service'] in images.INFRASTRUCTURE_SERVICES
    docker.state['packaged_schema'] = docker.state['schema']
    with (Path.cwd() / 'deploy.lock').open('ab') as lock:
        yield failed, lock


@pytest.mark.parametrize(('scenario', 'error'), [
    ('intent-only', None),
    ('observed', None),
    ('seal-only', 'no recorded launch intent'),
    ('operation-unknown', 'operator reconciliation does not match'),
    ('integer-instead-of-confirmation', 'operator reconciliation does not match'),
    ('foreign-binding', 'operator reconciliation does not match'),
    ('foreign-infrastructure', 'operator reconciliation does not match'),
    ('duplicate-field', 'duplicate fields'),
    ('consumer-running', 'only infrastructure'),
    ('stale-operator-snapshot', 'operator reconciliation does not match'),
    ('damaged-observation', 'observation does not show a candidate consumer change'),
])
def test_record_forward_stop_requires_bound_operator_and_launch_evidence(docker, activated_fixture, scenario, error):
    failed, lock = activated_fixture
    if scenario != 'seal-only':
        images.record_start_intent(docker.directory, failed.name, lock.fileno())
    api = next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')
    if scenario in {'observed', 'damaged-observation'}:
        images.record_start_boundary(docker.directory, failed.name, lock.fileno())
        api.update(Id='d' * 64, Image=images.read(failed / 'candidate.json')['images']['rec-api']['image'])
        images.observe_start(docker.directory, failed.name, lock.fileno())
    args = operator_stop_request(failed, lock, capture=scenario != 'seal-only')
    if scenario == 'damaged-observation':
        observation = failed / 'start-observed.json'
        value = images.read(observation)
        value['consumers']['rec-api']['image'] = 'sha256:' + 'f' * 64
        images.write(observation, value)
    record = images.read(args.operator_record)
    if scenario in {'operation-unknown', 'integer-instead-of-confirmation'}:
        record['docker_operations_quiesced'] = False if scenario == 'operation-unknown' else 1
    elif scenario == 'foreign-binding':
        record['binding_sha256'] = 'e' * 64
    elif scenario == 'foreign-infrastructure':
        record['infrastructure']['rec-temporal'] = 'f' * 64
    elif scenario == 'consumer-running':
        api['State']['Running'] = True
    elif scenario == 'stale-operator-snapshot':
        api['State']['StartedAt'] = '2026-11-10T05:01:00Z'
    images.write(args.operator_record, record)
    if scenario == 'duplicate-field':
        args.operator_record.write_text('{"schema_version":0,' + args.operator_record.read_text()[1:])
    marker = failed / 'forward-stop.json'
    if error:
        with pytest.raises(ValueError, match=error):
            images.record_forward_stop(docker.directory, args)
        assert not marker.exists()
        return
    images.record_forward_stop(docker.directory, args)
    digest, receipt = images.read_forward_stop(failed)
    assert receipt['operator_sha256'] == hashlib.sha256(args.operator_record.read_bytes()).hexdigest()
    assert ('observation_sha256' in receipt['start']) == (scenario == 'observed')
    assert images.verify_forward_stop(failed, docker.state['schema']) == digest
    assert images.active(docker.directory) == failed and not (failed / 'result.json').exists()


@pytest.mark.parametrize('interruption', ['before-pointer', 'after-pointer'])
def test_forward_stop_rotation_preserves_history_across_interruption(docker, activated_fixture, monkeypatch, interruption):
    failed, lock = activated_fixture
    images.record_start_intent(docker.directory, failed.name, lock.fileno())
    args = operator_stop_request(failed, lock)
    images.record_forward_stop(docker.directory, args)
    first, original = images.read_forward_stop(failed)
    next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service']
         == 'rec-api')['State']['StartedAt'] = '2026-11-10T05:01:00Z'
    args = operator_stop_request(failed, lock)
    pointer = failed / 'forward-stop.json'
    write, sync_directory = images.write, images.sync_directory

    with monkeypatch.context() as patch:
        if interruption == 'before-pointer':
            def interrupt(path, value):
                if path == pointer:
                    raise OSError('pointer update interrupted')
                write(path, value)
            patch.setattr(images, 'write', interrupt)
        else:
            def interrupt(path):
                if path == failed and images.read_forward_stop(failed)[0] != first:
                    raise OSError('pointer update interrupted')
                sync_directory(path)
            patch.setattr(images, 'sync_directory', interrupt)
        with pytest.raises(OSError, match='pointer update interrupted'):
            images.record_forward_stop(docker.directory, args)

    assert (images.read_forward_stop(failed)[0] == first) is (interruption == 'before-pointer')
    assert len(list((failed / 'forward-stops').glob('*.json'))) == 2
    images.record_forward_stop(docker.directory, args)
    second, current = images.read_forward_stop(failed)
    assert second != first and current['previous_stop_sha256'] == first
    assert images.read(failed / 'forward-stops' / f'{first}.json') == original
    assert images.verify_forward_stop(failed, docker.state['schema']) == second
    assert len(list((failed / 'forward-stops').glob('*.json'))) == 2


@pytest.fixture
def claim_fixture(docker, activated_fixture):
    failed, lock = activated_fixture
    images.record_start_intent(docker.directory, failed.name, lock.fileno())
    images.record_forward_stop(docker.directory, operator_stop_request(failed, lock))
    def stage(failed, sha, number, lock):
        for digit, target in ((str(number + 2), 'media-runtime'), (str(number + 3), 'runtime')):
            iid = 'sha256:' + digit * 64
            docker.refs[iid] = dict(Id=iid, Os='linux', Architecture='amd64', Config=dict(
                Labels={images.SOURCE_LABEL: sha, images.TARGET_LABEL: target}, Env=[f'GRAF_DEV_SOURCE_SHA={sha}']))
        args = argparse.Namespace(
            failed_attempt=failed.name, failed_sha=images.read(failed / 'candidate.json')['source_sha'],
            source_sha=sha, image='sha256:' + str(number + 2) * 64, runtime_image='sha256:' + str(number + 3) * 64,
            attempt_id=str(number) * 32, candidate_id='rc-forward', decision_digest=docker.args.decision_digest,
            full_digest=docker.args.full_digest, backup_directory=Path.cwd() / f'backup-{number}',
            deployment_lock_fd=lock.fileno(),
        )
        attempt = images.stage_forward(docker.directory, args)
        write_backup_files(args.backup_directory)
        images.write(attempt / 'forward-backup.json', dict(
            schema_version=1, attempt_id=attempt.name, stage_sha256=images.attempt_digest(attempt, 'forward-stage'),
            backup_reference=str(args.backup_directory), bucket='test-ingest',
            contents_sha256=images.backup_contents(args.backup_directory, 'test-ingest'),
        ))
        docker.state['head'] = args.source_sha
        return args, attempt

    args, attempt = stage(failed, '3' * 40, 2, lock)
    yield args, failed, attempt, lambda: stage(attempt, '4' * 40, 3, lock)


@pytest.mark.parametrize('scenario', ['success', 'foreign-lock', 'lock-busy', 'before-rename',
                                      'rename-unacknowledged'])
def test_start_intent_never_reauthorizes_an_activated_launch(docker, activated_fixture, monkeypatch, scenario):
    failed, descriptor = activated_fixture
    deployment_lock_fd = descriptor.fileno()
    marker = failed / 'start-intent.json'
    next(row for row in docker.running
         if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')['State']['Running'] = True
    if scenario in {'foreign-lock', 'lock-busy'}:
        fcntl.flock(deployment_lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        filename = 'other.lock' if scenario == 'foreign-lock' else 'deploy.lock'
        error = ValueError if scenario == 'foreign-lock' else BlockingIOError
        with (Path.cwd() / filename).open('ab') as lock:
            with pytest.raises(error):
                images.record_start_intent(docker.directory, failed.name, lock.fileno())
        assert not marker.exists()
        return
    if scenario == 'before-rename':
        observed = copy.deepcopy(docker.running)
        original_seal = (failed / images.NO_ROLLBACK).read_bytes()
        def fail_replace(_temporary, target):
            assert target == marker
            raise OSError('start intent replace failed')
        with monkeypatch.context() as patch:
            patch.setattr(images.os, 'replace', fail_replace)
            with pytest.raises(OSError, match='start intent replace failed'):
                images.record_start_intent(docker.directory, failed.name, deployment_lock_fd)
        assert not marker.exists() and not (failed / 'result.json').exists()
        assert (failed / images.NO_ROLLBACK).read_bytes() == original_seal
        assert images.active(docker.directory) == failed and docker.running == observed
        return
    if scenario == 'rename-unacknowledged':
        with monkeypatch.context() as patch:
            def fail_sync(directory):
                assert directory == failed and marker.is_file()
                raise OSError('start intent sync failed')
            patch.setattr(images, 'sync_directory', fail_sync)
            with pytest.raises(OSError, match='start intent sync failed'):
                images.record_start_intent(docker.directory, failed.name, deployment_lock_fd)
    else:
        images.record_start_intent(docker.directory, failed.name, deployment_lock_fd)

    before = marker.read_bytes()
    expected_consumers = {
        row['Config']['Labels']['com.docker.compose.service']: row['Id'] for row in docker.running
        if row['Config']['Labels']['com.docker.compose.service'] in images.REQUIRED_CONSUMERS
    }
    assert images.read(marker) == dict(schema_version=1, attempt_id=failed.name,
                                       seal_sha256=images.attempt_digest(failed, 'no-rollback'),
                                       previous_consumers=expected_consumers)
    with pytest.raises(ValueError, match='create-once'):
        images.record_start_intent(docker.directory, failed.name, deployment_lock_fd)
    assert marker.read_bytes() == before
    assert images.active(docker.directory) == failed and not (failed / 'result.json').exists()


@pytest.mark.parametrize(('scenario', 'error'), [
    ('created', None),
    ('restarted', None),
    ('previous', 'no candidate consumer'),
    ('wrong-image', 'no candidate consumer'),
    ('never-started', 'no candidate consumer'),
    ('restarted-before-boundary', 'no candidate consumer'),
    ('unbound-intent', 'intent does not match'),
    ('unbound-boundary', 'boundary does not match'),
])
def test_observe_start_requires_a_change_on_the_exact_candidate_image(docker, activated_fixture, scenario, error):
    failed, lock = activated_fixture
    deployment_lock_fd = lock.fileno()
    api = next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')
    pinned = images.read(failed / 'candidate.json')['images']['rec-api']['image']
    if scenario != 'wrong-image':
        api['Image'] = pinned
    images.record_start_intent(docker.directory, failed.name, deployment_lock_fd)
    if scenario == 'restarted-before-boundary':
        api['State']['StartedAt'] = '2026-11-10T04:01:00Z'
    images.record_start_boundary(docker.directory, failed.name, deployment_lock_fd)
    if scenario in {'created', 'wrong-image'}:
        api['Id'] = 'a' * 64
        api['State']['StartedAt'] = images.DOCKER_NOT_STARTED
    elif scenario == 'restarted':
        api['State']['StartedAt'] = '2026-11-10T04:01:00Z'
    elif scenario == 'never-started':
        api['State']['StartedAt'] = images.DOCKER_NOT_STARTED
    elif scenario == 'unbound-intent':
        intent = failed / 'start-intent.json'
        images.write(intent, dict(images.read(intent), seal_sha256='a' * 64))
    elif scenario == 'unbound-boundary':
        boundary = failed / 'start-boundary.json'
        images.write(boundary, dict(images.read(boundary), intent_sha256='a' * 64))
    marker = failed / 'start-observed.json'
    if error:
        with pytest.raises(ValueError, match=error):
            images.observe_start(docker.directory, failed.name, deployment_lock_fd)
        assert not marker.exists()
        return

    images.observe_start(docker.directory, failed.name, deployment_lock_fd)
    expected = dict(id=api['Id'], image=pinned, started_at=api['State']['StartedAt'])
    assert images.read(marker) == dict(schema_version=1, attempt_id=failed.name,
                                       boundary_sha256=images.attempt_digest(failed, 'start-boundary'),
                                       consumers={'rec-api': expected})
    before = marker.read_bytes()
    with pytest.raises(ValueError, match='create-once'):
        images.observe_start(docker.directory, failed.name, deployment_lock_fd)
    assert marker.read_bytes() == before
    assert not (failed / 'result.json').exists()


def test_start_boundary_refuses_a_consumer_that_survived_stop(docker, activated_fixture):
    failed, lock = activated_fixture
    images.record_start_intent(docker.directory, failed.name, lock.fileno())
    api = next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')
    api['State']['Running'] = True
    with pytest.raises(ValueError, match='consumers are still running'):
        images.record_start_boundary(docker.directory, failed.name, lock.fileno())
    assert not (failed / 'start-boundary.json').exists()


def test_visible_start_boundary_is_not_rewritten_after_failed_sync(docker, activated_fixture, monkeypatch):
    failed, lock = activated_fixture
    images.record_start_intent(docker.directory, failed.name, lock.fileno())
    marker = failed / 'start-boundary.json'

    def fail_sync(directory):
        assert directory == failed and marker.is_file()
        raise OSError('start boundary sync failed')

    with monkeypatch.context() as patch:
        patch.setattr(images, 'sync_directory', fail_sync)
        with pytest.raises(OSError, match='boundary sync failed'):
            images.record_start_boundary(docker.directory, failed.name, lock.fileno())
    before = marker.read_bytes()
    with pytest.raises(ValueError, match='boundary is create-once'):
        images.record_start_boundary(docker.directory, failed.name, lock.fileno())
    assert marker.read_bytes() == before and not (failed / 'start-observed.json').exists()


@pytest.mark.parametrize('scenario', ['valid', 'closed', 'foreign', 'busy'])
def test_runtime_checks_inherited_deployment_lock_before_loading_environment(tmp_path, monkeypatch, scenario):
    monkeypatch.chdir(tmp_path)
    subprocess.run(['git', 'init', '-q', '-b', 'master'], check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    scripts = tmp_path / 'infra/scripts'
    scripts.mkdir(parents=True)
    (scripts / 'release-images.py').write_bytes((ROOT / 'infra/scripts/release-images.py').read_bytes())
    (tmp_path / '.env').write_text('exit 41\n')
    monkeypatch.setenv('TWOBRAIN_PRODUCTION_RELEASE_GATE', '1')
    monkeypatch.setenv('TWOBRAIN_PRODUCTION_RELEASE_LOCK_HELD', '1')
    lock_path = tmp_path / '.git/twobrain-rec-deploy.lock'
    with lock_path.open('ab') as locked, lock_path.open('ab') as busy, (tmp_path / 'other').open('ab') as foreign:
        fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        inherited = {'valid': locked, 'busy': busy, 'foreign': foreign}.get(scenario)
        fd = str(inherited.fileno()) if inherited else '-'
        result = subprocess.run(
            ['bash', '-c', 'exec 9>&"$1"; shift; exec bash "$@"', 'lock-fixture', fd,
             str(ROOT / 'infra/scripts/cd-remote-runtime.sh'), 'master', source, source,
             'rc-fixture', 'decision', 'full'],
            pass_fds=(inherited.fileno(),) if inherited else (), capture_output=True, text=True,
        )
    assert result.returncode == (41 if scenario == 'valid' else 1), result.stderr
    assert ('check-deployment-lock refused' in result.stderr) is (scenario != 'valid')


@pytest.mark.parametrize(('change', 'error'), [
    ('old-checkout', 'exact clean checkout'),
    ('wrong-decision', 'approval differs from staging'),
    ('damaged-backup', 'archive does not match its receipt'),
    ('late-damaged-backup', 'archive does not match its receipt'),
    ('consumer-running', 'consumers must be stopped'),
    ('different-runtime-schema', 'different database schema'),
    ('missing-runtime-image', 'missing image'),
    ('stop-rewritten', 'no longer matches the forward stop receipt'),
    ('consumer-restarted-after-stop', 'forward stop receipt no longer matches'),
])
def test_forward_claim_does_not_switch_on_invalid_live_or_release_evidence(docker, claim_fixture, monkeypatch, change, error):
    args, failed, attempt, _ = claim_fixture
    if change == 'old-checkout':
        docker.state['head'] = args.failed_sha
    elif change == 'wrong-decision':
        args.decision_digest = 'sha256:' + 'f' * 64
    elif change == 'damaged-backup':
        (args.backup_directory / 'postgres.dump').write_text('tampered synthetic content')
    elif change == 'late-damaged-backup':
        schema = images.packaged_schema

        def damage_archive(iid):
            (args.backup_directory / 'postgres.dump').write_text('tampered after the first check')
            return schema(iid)
        monkeypatch.setattr(images, 'packaged_schema', damage_archive)
    elif change == 'consumer-running':
        next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')['State']['Running'] = True
    elif change == 'different-runtime-schema':
        schema = images.packaged_schema
        monkeypatch.setattr(images, 'packaged_schema', lambda iid: 'other' if iid == args.runtime_image else schema(iid))
    elif change == 'missing-runtime-image':
        del docker.refs[args.runtime_image]
    elif change == 'stop-rewritten':
        old_digest, old = images.read_forward_stop(failed)
        next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service']
             == 'rec-api')['State']['StartedAt'] = '2026-11-10T05:01:00Z'
        docker.state['head'] = args.failed_sha
        operator = argparse.Namespace(failed_attempt=failed.name, failed_sha=args.failed_sha,
                                      deployment_lock_fd=args.deployment_lock_fd,
                                      operator_record=docker.directory / 'operator-record.json')
        proposal = images.forward_stop_snapshot(docker.directory, operator)[1]
        images.write(operator.operator_record, dict(proposal, docker_operations_quiesced=True))
        images.record_forward_stop(docker.directory, operator)
        new_digest, new = images.read_forward_stop(failed)
        assert new_digest != old_digest and new['previous_stop_sha256'] == old_digest
        assert images.read(failed / 'forward-stops' / f'{old_digest}.json') == old
        docker.state['head'] = args.source_sha
    elif change == 'consumer-restarted-after-stop':
        next(row for row in docker.running if row['Config']['Labels']['com.docker.compose.service']
             == 'rec-api')['State']['StartedAt'] = '2026-11-10T05:01:00Z'
    with pytest.raises(ValueError, match=error):
        images.claim_forward(docker.directory, args)
    assert images.active(docker.directory) == failed
    assert not (attempt / 'result.json').exists()
    assert (attempt / images.NO_ROLLBACK).exists() is (change == 'late-damaged-backup')


@pytest.mark.parametrize('interruption', ['before-pointer', 'after-rename', None])
def test_forward_claim_keeps_both_attempts_across_switch_and_repeat(docker, claim_fixture, monkeypatch, interruption):
    args, failed, attempt, stage_again = claim_fixture
    prior_files = attempt_files(failed)
    active_path = docker.directory / 'active.json'
    write = images.write
    sync = images.sync_directory
    with monkeypatch.context() as patch:
        if interruption == 'before-pointer':
            def interrupt(path, value):
                if path == active_path:
                    raise OSError('before pointer')
                write(path, value)
            patch.setattr(images, 'write', interrupt)
        elif interruption == 'after-rename':
            def interrupt(directory):
                if directory == docker.directory and images.active(docker.directory) == attempt:
                    raise OSError('after rename')
                sync(directory)
            patch.setattr(images, 'sync_directory', interrupt)
        if interruption:
            with pytest.raises(OSError, match='before pointer|after rename'):
                images.claim_forward(docker.directory, args)
        else:
            assert images.claim_forward(docker.directory, args) == attempt
    seal = images.sealed_receipt(attempt)
    assert seal['forward']['previous_attempt'] == seal['forward']['original_attempt'] == failed.name
    assert seal['forward']['backup_sha256'] == images.attempt_digest(attempt, 'forward-backup')
    assert not (attempt / 'previous.json').exists()
    if interruption == 'before-pointer':
        assert images.active(docker.directory) == failed
        assert images.claim_forward(docker.directory, args) == attempt
    assert images.active(docker.directory) == attempt
    # Repeat confirms the already visible pointer and checks its records without replacing them.
    assert images.claim_forward(docker.directory, args) == attempt
    candidate_path = attempt / 'candidate.json'
    candidate_bytes = candidate_path.read_bytes()
    images.write(candidate_path, dict(images.read(candidate_path), source_sha='e' * 40))
    with pytest.raises(ValueError, match='different records'):
        images.claim_forward(docker.directory, args)
    candidate_path.write_bytes(candidate_bytes)
    with pytest.raises(ValueError, match='forward recovery'):
        images.finish(docker.directory, 'restored', attempt.name)
    with pytest.raises(ValueError, match='no runtime completion path'):
        images.finish(docker.directory, 'deployed', attempt.name)
    assert images.check_forward_baseline(docker.directory, attempt.name, args.source_sha) == docker.state['schema']
    with pytest.raises(ValueError, match='cannot authorize forward recovery'):
        images.record_start_intent(docker.directory, attempt.name, args.deployment_lock_fd)
    with pytest.raises(ValueError, match='forward stop receipt is required'):
        stage_again()
    assert images.active(docker.directory) == attempt
    assert attempt_files(failed) == prior_files
    assert not any((path / 'result.json').exists() for path in (failed, attempt))
    assert not any(call[:2] == ('docker', 'compose') and call[-3:] != ('config', '--format', 'json')
                   for call in docker.calls)


def test_forward_preflight_checks_candidate_from_failed_checkout_without_adoption(docker, claim_fixture, monkeypatch):
    args, failed, attempt, _ = claim_fixture
    docker.state['head'] = args.failed_sha
    args.checkout_sha = args.failed_sha
    before = {path: attempt_files(path) for path in (failed, attempt)}
    images.check_forward_claim(docker.directory, args)
    assert images.active(docker.directory) == failed
    assert docker.state['head'] == args.failed_sha
    assert {path: attempt_files(path) for path in before} == before

    for field, value, error in (
        ('checkout_sha', args.source_sha, 'requires the failed checkout'),
        ('full_digest', 'sha256:' + 'e' * 64, 'approval differs from staging'),
    ):
        with monkeypatch.context() as patch:
            patch.setattr(args, field, value)
            with pytest.raises(ValueError, match=error):
                images.check_forward_claim(docker.directory, args)
    assert images.active(docker.directory) == failed
    assert {path: attempt_files(path) for path in before} == before
    interrupted = attempt / 'override.json'
    images.write(interrupted, {})
    with pytest.raises(ValueError, match='before adoption'):
        images.check_forward_claim(docker.directory, args)
    interrupted.unlink()

    schema = images.packaged_schema

    def restart_after_snapshot(iid):
        consumer = next(row for row in docker.running
                        if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')
        consumer['State']['StartedAt'] = '2026-11-10T05:02:00Z'
        return schema(iid)

    monkeypatch.setattr(images, 'packaged_schema', restart_after_snapshot)
    with pytest.raises(ValueError, match='forward stop receipt no longer matches'):
        images.check_forward_claim(docker.directory, args)
    assert images.active(docker.directory) == failed
    assert {path: attempt_files(path) for path in before} == before


@pytest.mark.parametrize('interruption', ['none', 'before-intent', 'intent-sync', 'boundary-sync'])
def test_forward_launch_arms_once_and_requires_reconciliation_after_ambiguous_write(
        docker, claim_fixture, monkeypatch, interruption):
    args, failed, attempt, stage_again = claim_fixture
    prior_files = attempt_files(failed)
    # The candidate had already taken ownership when the earlier process stopped.
    images.claim_forward(docker.directory, args)
    intent = attempt / 'start-intent.json'
    boundary = attempt / 'start-boundary.json'
    sync = images.sync_directory
    write = images.write

    with monkeypatch.context() as patch:
        if interruption == 'before-intent':
            def interrupt_before(path, value):
                if path == intent:
                    raise OSError('injected write failure')
                write(path, value)
            patch.setattr(images, 'write', interrupt_before)
        elif interruption != 'none':
            visible = intent if interruption == 'intent-sync' else boundary

            def interrupt_after(directory):
                if directory == attempt and visible.exists():
                    raise OSError('injected write failure')
                sync(directory)
            patch.setattr(images, 'sync_directory', interrupt_after)
        if interruption == 'none':
            armed, overlay = images.arm_forward_start(docker.directory, args)
            assert armed == attempt
            api = json.loads(overlay)['services']['rec-api']
            assert api['image'] == args.runtime_image
            assert api['environment'] == {images.NORMALIZATION_ENABLED: 'false', images.NORMALIZATION_DISPATCH: 'false'}
        else:
            with pytest.raises(OSError, match='injected write failure'):
                images.arm_forward_start(docker.directory, args)

    if interruption == 'before-intent':
        assert not intent.exists()
        assert images.arm_forward_start(docker.directory, args)[0] == attempt
    assert intent.exists()
    assert boundary.exists() is (interruption != 'intent-sync')
    evidence = images.forward_start_evidence(attempt)
    assert 'intent_sha256' in evidence
    assert ('boundary_sha256' in evidence) == boundary.exists()
    if boundary.exists():
        _, stopped = images.start_boundary_evidence(attempt, evidence['intent_sha256'])
        assert {name: row['id'] for name, row in stopped.items()} == images.read(intent)['previous_consumers']
    with pytest.raises(ValueError, match='already armed'):
        images.arm_forward_start(docker.directory, args)
    with pytest.raises(ValueError, match='forward stop receipt is required'):
        stage_again()
    with os.fdopen(os.dup(args.deployment_lock_fd), 'wb') as lock:
        images.record_forward_stop(docker.directory, operator_stop_request(attempt, lock))
    assert stage_again()[1] != attempt
    assert images.active(docker.directory) == attempt
    assert attempt_files(failed) == prior_files
    assert not (attempt / 'result.json').exists()


def test_forward_launch_refuses_runtime_change_after_adoption(docker, claim_fixture, monkeypatch):
    args, _, attempt, _ = claim_fixture
    claim = images.claim_forward

    def claim_with_restart(state, args):
        result = claim(state, args)
        consumer = next(row for row in docker.running
                        if row['Config']['Labels']['com.docker.compose.service'] == 'rec-api')
        consumer['State']['StartedAt'] = '2026-11-10T05:02:00Z'
        return result

    monkeypatch.setattr(images, 'claim_forward', claim_with_restart)
    with pytest.raises(ValueError, match='forward stop receipt no longer matches'):
        images.arm_forward_start(docker.directory, args)
    assert images.active(docker.directory) == attempt
    assert not (attempt / 'start-intent.json').exists()


def test_forward_launch_refuses_unapproved_compose_change(docker, claim_fixture):
    args, _, attempt, _ = claim_fixture
    docker.state['unsafe_launch_configuration'] = True
    with pytest.raises(ValueError, match='unapproved Compose configuration'):
        images.arm_forward_start(docker.directory, args)
    assert not (attempt / 'start-intent.json').exists()


@pytest.mark.parametrize('failure', [None, 'partial-workers', 'worker-readiness', 'api-readiness',
                                     'changed-infrastructure', 'stop-error', 'launch-timeout', 'vanished-container',
                                     'wrong-compose-context', 'worker-restarted-during-api', 'public-readiness', 'smoke',
                                     'smoke-timeout', 'post-smoke-readiness', 'result-sync', 'ack-sync', 'abandoned-result', 'result-before-rename', 'double-signal'])
def test_forward_launch_orders_phases_and_contains_failure(docker, claim_fixture, monkeypatch, capsys, failure):
    args, failed, attempt, stage_successor = claim_fixture
    args.public_channel_digest = 'sha256:' + '9' * 64
    plugin = Path.cwd() / 'docker-compose'
    plugin.touch(mode=0o700)
    base_command = images.command
    fd = args.deployment_lock_fd
    workers = images.REQUIRED_CONSUMERS - {'rec-api'}
    services = {row['Config']['Labels']['com.docker.compose.service']: row for row in docker.running}
    prior_files = attempt_files(failed)
    phases = []
    stopped = set()
    handlers = {}

    def command(*argv, input=None, pass_fds=(), timeout=None):
        if argv[0] == 'timeout':
            assert argv[1:5] == ('--kill-after=30s', '180s', 'infra/scripts/run-production-smoke.sh', '--forward')
            assert pass_fds == (fd,) and timeout == 220 and int(argv[5]) == fd
            attempt_id, run_id, origin, *ids = argv[6:]
            assert services['rec-api']['State']['Running']
            with pytest.raises(ValueError, match='container IDs changed'):
                images.check_forward_smoke(docker.directory, fd, attempt_id, run_id, origin, *ids[::-1])
            images.check_forward_smoke(docker.directory, fd, attempt_id, run_id, origin, *ids)
            with pytest.raises(ValueError, match='already started'):
                images.check_forward_smoke(docker.directory, fd, attempt_id, run_id, origin, *ids)
            phases.append('smoke-checked')
            if failure == 'smoke':
                raise ValueError('synthetic upload failed')
            if failure == 'smoke-timeout':
                raise subprocess.TimeoutExpired(argv, timeout)
            upload = dict.fromkeys(('meeting_id', 'session_id', 'media_revision_id'),
                                   '00000000-0000-4000-8000-000000000001')
            upload.update(meeting_status='ingested_pending_processing', uploaded_parts=3)
            return json.dumps(dict(run_id=run_id, upload=upload,
                                   auth_cleanup=dict(run_id=run_id, auth_cleanup_result='pass'),
                                   cleanup=dict(run_id=run_id, cleanup_result='pass', database_records_removed=5,
                                                object_keys_removed=3)))
        if argv[:2] == ('docker', 'info') and '.ClientInfo.Plugins' in argv[-1]:
            return str(plugin)
        if argv[0] == str(plugin):
            if argv[-3:] == ('config', '--format', 'json'):
                return base_command(*images.FORWARD_COMPOSE, *argv[-3:], input=input)
            if argv[-6:-3] == ('ps', '--no-trunc', '-q'):
                assert set(argv[-3:]) == images.INFRASTRUCTURE_SERVICES and timeout == 10
                return '' if failure == 'wrong-compose-context' else '\n'.join(services[name]['Id'] for name in argv[-3:])
            assert pass_fds == (fd,) and timeout == 300
            assert argv[1:len(images.FORWARD_COMPOSE)-1] == images.FORWARD_COMPOSE[2:]
            flags = ('up', '--no-deps', '--no-build', '--pull', 'never', '-d', '--wait', '--wait-timeout', '240')
            start = len(images.FORWARD_COMPOSE) - 1
            assert argv[start:start + len(flags)] == flags
            names = argv[start + len(flags):]
            phases.append(names)
            assert images.start_intent_digest(attempt)
            pinned = json.loads(input)['services']
            for name in names[:1] if failure in ('partial-workers', 'launch-timeout', 'double-signal') else names:
                services[name]['Image'] = pinned[name]['image']
                services[name]['State'].update(Running=True, StartedAt='2026-11-10T05:03:00Z')
            if failure == 'double-signal':
                handlers[signal.SIGHUP](signal.SIGHUP, None)
            if failure == 'partial-workers':
                raise ValueError('compose response lost after partial startup')
            if failure == 'launch-timeout':
                raise subprocess.TimeoutExpired(argv, timeout)
            if failure == 'changed-infrastructure':
                services['rec-postgres']['Id'] = 'e' * 64
            if failure == 'worker-restarted-during-api' and names == ('rec-api',):
                services['rec-processing-worker']['State']['StartedAt'] = '2026-11-10T05:04:00Z'
            return ''
        if argv[:2] == ('docker', 'stop'):
            assert pass_fds == (fd,) and timeout == 20
            name = next(name for name, row in services.items() if row['Id'] == argv[-1])
            assert name in images.REQUIRED_CONSUMERS
            stopped.add(name)
            if failure == 'double-signal':
                handlers[signal.SIGTERM](signal.SIGTERM, None)
            if failure == 'stop-error' and name == images.MEDIA_WORKER:
                raise ValueError('synthetic stop failure')
            services[name]['State']['Running'] = False
            return ''
        if (failure == 'vanished-container' and argv[:2] == ('docker', 'inspect')
                and argv[2:] == (services['rec-processing-worker']['Id'],)):
            docker.running.remove(services['rec-processing-worker'])
            raise ValueError('worker disappeared before its stop')
        return base_command(*argv, input=input, timeout=timeout)

    def verify_workers(observed, lock_fd):
        assert lock_fd == fd
        assert observed['rec-api']['running'] == ('smoke-checked' in phases)
        phases.append('workers-checked')
        if failure in ('worker-readiness', 'vanished-container') or (
            failure == 'post-smoke-readiness' and 'smoke-checked' in phases
        ):
            raise ValueError('worker readiness failed')

    def verify_running(observed, lock_fd):
        assert lock_fd == fd
        assert observed['rec-api']['running']
        phases.append('api-checked')
        if failure in ('api-readiness', 'stop-error'):
            raise ValueError('API readiness failed')

    monkeypatch.setattr(images, 'command', command)
    monkeypatch.setattr(images, 'verify_forward_workers', verify_workers)
    monkeypatch.setattr(images, 'verify_forward_api', verify_running)
    channel = {"origin": "https://rec.2brain.pro"}
    monkeypatch.setattr(images, 'approved_forward_channel', lambda _args: channel)
    monkeypatch.setattr(images, 'verify_forward_release_approval', lambda _args: None)

    def verify_public(approved, lock_fd):
        assert approved is channel and lock_fd == fd
        phases.append('public-checked')
        if failure == 'public-readiness':
            raise ValueError('public readiness failed')

    monkeypatch.setattr(images, 'verify_forward_public_process', verify_public)

    if failure == 'result-before-rename':
        original_replace = os.replace

        def refuse_result_rename(source, target):
            if target == attempt / 'result.json':
                raise OSError('injected failure before result rename')
            original_replace(source, target)

        monkeypatch.setattr(os, 'replace', refuse_result_rename)

    if failure in (None, 'result-sync', 'ack-sync', 'abandoned-result'):
        if failure:
            original_sync = images.sync_directory
            with monkeypatch.context() as patch:
                def refuse_result_sync(directory):
                    marker = 'result.json' if failure == 'result-sync' else 'forward-result-confirmed.json'
                    if directory == attempt and (attempt / marker).exists():
                        raise OSError('injected unacknowledged result')
                    original_sync(directory)
                patch.setattr(images, 'sync_directory', refuse_result_sync)
                with pytest.raises(OSError, match='unacknowledged result'):
                    images.start_forward(docker.directory, args)
            assert 'forward_result=confirmation_required' in capsys.readouterr().err
            with pytest.raises(ValueError, match='needs locked confirmation'):
                images.completed_side(attempt)
        else:
            assert images.start_forward(docker.directory, args) == attempt
        assert phases == [tuple(sorted(workers)), 'workers-checked', ('rec-api',), 'api-checked',
                          'public-checked', 'smoke-checked', 'workers-checked', 'api-checked']
        assert images.read(attempt / 'forward-smoke.json')['upload'] == 'finalized'
        record = (attempt / 'result.json').read_bytes()
        assert images.read(attempt / 'result.json')['result'] == 'deployed'
        with pytest.raises(ValueError, match='does not match the approved recovery'):
            images.start_forward(docker.directory, argparse.Namespace(**(vars(args) | {'failed_attempt': 'f' * 32})))
        assert not stopped
        with monkeypatch.context() as patch:
            with pytest.raises(ValueError, match='differs from its result'):
                patch.setitem(services['rec-api']['State'], 'StartedAt', '2026-11-10T05:11:00Z')
                images.start_forward(docker.directory, args)
        if failure == 'abandoned-result':
            for name in images.REQUIRED_CONSUMERS:
                services[name]['State']['Running'] = False
            with os.fdopen(os.dup(fd), 'wb') as lock:
                with monkeypatch.context() as patch:
                    patch.setitem(services['rec-temporal'], 'Id', 'e' * 64)
                    with pytest.raises(ValueError, match='infrastructure containers changed'):
                        operator_stop_request(attempt, lock)
                operator = operator_stop_request(attempt, lock)
                request = images.read(operator.operator_record)
                assert request['abandon_unconfirmed_result'] is False
                assert request['abandoned_result_sha256'] == hashlib.sha256(record).hexdigest()
                with pytest.raises(ValueError, match='forward stop receipt is required'):
                    images.check_forward_baseline(docker.directory, attempt.name, args.source_sha)
                with pytest.raises(ValueError, match='operator reconciliation does not match'):
                    images.record_forward_stop(docker.directory, operator)
                images.write(operator.operator_record, dict(request, abandon_unconfirmed_result=True))
                images.record_forward_stop(docker.directory, operator)
                assert images.check_forward_baseline(docker.directory, attempt.name, args.source_sha) == docker.state['schema']
                with monkeypatch.context() as patch:
                    patch.setitem(services['rec-temporal'], 'Id', 'e' * 64)
                    with pytest.raises(ValueError, match='infrastructure containers changed'):
                        images.check_forward_baseline(docker.directory, attempt.name, args.source_sha)
            with pytest.raises(ValueError, match='was abandoned after verified stop'):
                images.confirm_forward_result(docker.directory, attempt, args, channel)
            next_args, successor = stage_successor()
            assert next_args.failed_attempt == attempt.name
            assert images.read(successor / 'forward-stage.json')['stop_sha256'] == images.read_forward_stop(attempt)[0]
            assert images.active(docker.directory) == attempt
            assert (attempt / 'result.json').read_bytes() == record
            assert not (attempt / 'forward-result-confirmed.json').exists()
            return
        images.check_forward_execution(docker.directory, argparse.Namespace(**(vars(args) | {'checkout_sha': args.source_sha})))
        assert images.start_forward(docker.directory, args) == attempt
        assert phases[-3:] == ['workers-checked', 'api-checked', 'public-checked']
        assert (attempt / 'result.json').read_bytes() == record
        assert images.completed_side(attempt) == 'candidate'
        with monkeypatch.context() as patch:
            patch.setitem(services['rec-api']['State'], 'StartedAt', '2026-11-10T05:11:00Z')
            assert images.completed_side(attempt) == 'candidate'
            patch.setitem(services['rec-api'], 'Id', 'e' * 64)
            with pytest.raises(ValueError, match='differs from its result'):
                images.completed_side(attempt)
        assert (attempt / 'result.json').read_bytes() == record
        proof = attempt / 'forward-smoke-intent.json'
        proof.write_bytes(proof.read_bytes() + b' ')
        with pytest.raises(ValueError, match='does not match its launch and smoke evidence'):
            images.completed_side(attempt)
        with pytest.raises(ValueError, match='does not match its launch and smoke evidence'):
            images.start_forward(docker.directory, args)
        assert not stopped
        assert attempt_files(failed) == prior_files
        return
    elif failure == 'double-signal':
        monkeypatch.setattr(signal, 'signal', handlers.__setitem__)
        monkeypatch.setattr(images, 'state_dir', lambda: docker.directory)
        monkeypatch.setenv('TWOBRAIN_PRODUCTION_RELEASE_GATE', '1')
        cli = ['release-images.py', 'start-forward']
        for key in ('failed_attempt', 'source_sha', 'attempt_id', 'candidate_id', 'decision_digest',
                    'full_digest', 'public_channel_digest', 'backup_directory', 'deployment_lock_fd'):
            cli.extend(('--' + key.replace('_', '-'), str(getattr(args, key))))
        for key in ('public-channel', 'release-decision', 'full-evidence'):
            cli.extend(('--' + key, '/isolated/fixture.json'))
        monkeypatch.setattr(sys, 'argv', cli)
        assert images.main() == 1
        stderr = capsys.readouterr().err
        assert 'forward launch interrupted' in stderr and 'forward_consumers=stopped_observed' in stderr
        assert len(stopped) == 1 and not (attempt / 'result.json').exists()
        assert not any(services[name]['State']['Running'] for name in images.REQUIRED_CONSUMERS)
        return
    elif failure == 'wrong-compose-context':
        with pytest.raises(ValueError, match='does not see the verified infrastructure'):
            images.start_forward(docker.directory, args)
        assert not phases and not stopped
    else:
        error = (subprocess.TimeoutExpired if failure in ('launch-timeout', 'smoke-timeout') else
                 OSError if failure == 'result-before-rename' else ValueError)
        with pytest.raises(error):
            images.start_forward(docker.directory, args)
        assert (attempt / 'start-observed.json').exists()
        diagnostics = capsys.readouterr().err
        assert 'forward_docker_quiescence=operator_reconciliation_required' in diagnostics
        if failure in ('changed-infrastructure', 'stop-error', 'vanished-container'):
            assert 'forward_consumers=stop_unconfirmed' in diagnostics
        else:
            assert 'forward_consumers=stopped_observed' in diagnostics
        started = set(phases[0][:1] if failure in ('partial-workers', 'launch-timeout') else phases[0])
        if failure in ('api-readiness', 'stop-error', 'worker-restarted-during-api', 'public-readiness', 'smoke',
                       'smoke-timeout', 'post-smoke-readiness', 'result-before-rename'):
            started.add('rec-api')
            if failure == 'worker-restarted-during-api':
                assert 'api-checked' not in phases
        else:
            assert ('rec-api',) not in phases
        if failure == 'vanished-container':
            started.discard('rec-processing-worker')
            assert services['rec-processing-worker'] not in docker.running
        assert stopped == started
        assert {name for name in images.REQUIRED_CONSUMERS
                if services[name] in docker.running and services[name]['State']['Running']} == (
            {images.MEDIA_WORKER} if failure == 'stop-error' else set())
    with pytest.raises(ValueError, match='already armed'):
        images.start_forward(docker.directory, args)
    assert attempt_files(failed) == prior_files
    assert not (attempt / 'result.json').exists()
    assert (attempt / 'forward-smoke.json').exists() == (failure in ('post-smoke-readiness', 'result-before-rename'))


def test_forward_execution_entry_preserves_stopped_runtime_until_first_armed_start(docker, claim_fixture, monkeypatch):
    args, failed, attempt, _ = claim_fixture
    monkeypatch.setattr(images, 'approved_forward_channel', lambda _args: {})
    monkeypatch.setattr(images, 'verify_forward_release_approval', lambda _args: None)
    before = attempt_files(attempt)
    for checkout in (args.failed_sha, args.source_sha):
        docker.state['head'] = checkout
        args.checkout_sha = checkout
        images.check_forward_execution(docker.directory, args)
        assert images.active(docker.directory) == failed and attempt_files(attempt) == before
    with pytest.raises(ValueError, match='not the active attempt'):
        images.confirm_forward_result(docker.directory, attempt, args, {})
    assert images.active(docker.directory) == failed and attempt_files(attempt) == before
    images.arm_forward_start(docker.directory, args)
    with pytest.raises(FileNotFoundError, match='result.json'):
        images.confirm_forward_result(docker.directory, attempt, args, {})
    with pytest.raises(ValueError, match='already armed'):
        images.check_forward_execution(docker.directory, args)


@pytest.mark.parametrize('fault', [None, 'timeout', 'residue', 'wrong-run'])
def test_reconcile_forward_smoke_is_bound_to_fresh_quiescence_and_exact_run(docker, claim_fixture, monkeypatch, fault):
    args, failed, attempt, _ = claim_fixture
    images.arm_forward_start(docker.directory, args)
    run_id = 'forward-' + 'a' * 32
    images.write(attempt / 'forward-smoke-started.json', {'run_id': run_id})
    images.write(attempt / 'forward-smoke-intent.json', {'run_id': run_id, 'origin': 'https://rec.2brain.pro'})
    stop_args = argparse.Namespace(failed_attempt=attempt.name, failed_sha=args.source_sha,
                                   deployment_lock_fd=args.deployment_lock_fd)
    with pytest.raises(ValueError, match='smoke cleanup is unknown'):
        images.check_forward_baseline(docker.directory, attempt.name, args.source_sha)
    with pytest.raises(ValueError, match='forward stop receipt is required'):
        images.reconcile_forward_smoke(docker.directory, stop_args)

    base = images.command
    invoked = []
    plugin = '/fake/docker-compose'
    configuration = dict(name=images.PROJECT, services={
        'rec-maintenance': dict(image=args.runtime_image, build={}, depends_on={'rec-postgres': {}},
                                volumes=[dict(type='volume', source='recovery', target='/proof', read_only=True)],
                                networks={'private': {}}, secrets=[{'source': 'role-password'}]),
        'rec-postgres': {'image': 'never-start-this'},
    }, networks={'private': {'name': 'runtime-private'}, 'unused': {'name': 'never-create-this'}},
       volumes={'recovery': {'name': 'runtime-recovery'}, 'unused': {'name': 'never-create-this'}},
       secrets={'role-password': {'file': '/synthetic/password'}, 'unused': {}})
    monkeypatch.setattr(images, 'direct_forward_compose', lambda: (plugin,))
    monkeypatch.setattr(images, 'forward_launch_configuration', lambda *a, **kw: ('', copy.deepcopy(configuration)))
    docker.refs[args.runtime_image]['Config']['Labels'][images.TARGET_LABEL] = 'runtime'

    def command(*argv, input=None, timeout=None, pass_fds=()):
        if argv[0] != plugin:
            return base(*argv, input=input, timeout=timeout)
        assert pass_fds == (args.deployment_lock_fd,) and timeout == 180
        assert argv[1:9] == ('-f', '-', 'run', '--no-deps', '--pull', 'never', '--rm', '-T')
        assert argv[-1] == run_id and 'verify_runtime_database_identity.py' in argv[-3]
        assert '--reconcile-interrupted' in argv[-3]
        assert argv[argv.index('--name') + 1].endswith(images.read_forward_stop(attempt)[0][:12])
        config = json.loads(input)
        service, = config['services'].values()
        assert service['image'] == args.runtime_image and service['restart'] == 'no'
        assert 'build' not in service and 'depends_on' not in service
        assert config['networks'] == {'private': {'name': 'runtime-private', 'external': True}}
        assert config['volumes'] == {'recovery': {'name': 'runtime-recovery', 'external': True}}
        assert set(config['secrets']) == {'role-password'}
        intent = images.read(attempt / 'forward-smoke-cleanup-intent.json')
        assert intent['stop_sha256'] == images.read_forward_stop(attempt)[0]
        invoked.append(intent['stop_sha256'])
        if len(invoked) == 1 and fault == 'timeout':
            raise subprocess.TimeoutExpired(argv, timeout)
        return json.dumps(dict(run_id='other' if len(invoked) == 1 and fault == 'wrong-run' else run_id,
                               cleanup_result='pass', residue_records=['unexpected'] if
                               len(invoked) == 1 and fault == 'residue' else []))

    monkeypatch.setattr(images, 'command', command)
    with os.fdopen(os.dup(args.deployment_lock_fd), 'wb') as lock:
        operator = operator_stop_request(attempt, lock)
        confirmed = images.read(operator.operator_record)
        images.write(operator.operator_record, dict(confirmed, storage_writes_quiesced=False))
        with pytest.raises(ValueError, match='operator reconciliation does not match'):
            images.record_forward_stop(docker.directory, operator)
        images.write(operator.operator_record, confirmed)
        images.record_forward_stop(docker.directory, operator)
        if fault:
            with pytest.raises(subprocess.TimeoutExpired if fault == 'timeout' else ValueError):
                images.reconcile_forward_smoke(docker.directory, stop_args)
            with pytest.raises(ValueError, match='fresh operator stop receipt'):
                images.reconcile_forward_smoke(docker.directory, stop_args)
            with pytest.raises(ValueError, match='smoke cleanup is unknown'):
                images.check_forward_baseline(docker.directory, attempt.name, args.source_sha)
            images.record_forward_stop(docker.directory, operator_stop_request(attempt, lock))
        images.reconcile_forward_smoke(docker.directory, stop_args)
        images.reconcile_forward_smoke(docker.directory, stop_args)
    assert len(set(invoked)) == len(invoked) == (2 if fault else 1)
    assert images.check_forward_baseline(docker.directory, attempt.name, args.source_sha) == docker.state['schema']
    assert images.active(docker.directory) == attempt and not (attempt / 'result.json').exists()


@pytest.mark.parametrize('fault', [None, 'other-run', 'unfinalized', 'bad-uuid', 'cleanup-failed', 'cleanup-empty', 'auth-other-run'])
def test_forward_smoke_accepts_only_finalized_upload_and_same_run_cleanup(fault):
    run_id = 'forward-example'
    upload = dict.fromkeys(('meeting_id', 'session_id', 'media_revision_id'),
                           '00000000-0000-4000-8000-000000000001')
    upload.update(meeting_status='ingested_pending_processing', uploaded_parts=3)
    proof = dict(run_id=run_id, upload=upload, auth_cleanup=dict(run_id=run_id, auth_cleanup_result='pass'),
                 cleanup=dict(run_id=run_id, cleanup_result='pass', database_records_removed=5, object_keys_removed=3))
    if fault == 'other-run':
        proof['run_id'] = 'another'
    elif fault == 'unfinalized':
        upload['meeting_status'] = 'uploading'
    elif fault == 'bad-uuid':
        upload['media_revision_id'] = 'not-a-uuid'
    elif fault == 'cleanup-failed':
        proof['cleanup']['cleanup_result'] = 'residue_recorded'
    elif fault == 'cleanup-empty':
        proof['cleanup']['object_keys_removed'] = 0
    elif fault == 'auth-other-run':
        proof['auth_cleanup']['run_id'] = 'another'
    raw = json.dumps(proof)
    if fault:
        with pytest.raises(ValueError):
            images.forward_smoke_result(raw, run_id)
    else:
        assert images.forward_smoke_result(raw, run_id) == {
            'run_id': run_id, 'upload': 'finalized', 'auth_cleanup': 'pass', 'artifact_cleanup': 'pass',
        }


@pytest.mark.parametrize(('fault', 'error'), [
    (None, None),
    ('media-network', 'media worker runtime boundary'),
    ('wrong-role', 'database role proof'),
    ('poller-only', 'queue readiness proof'),
    ('wrong-profile', 'queue readiness proof'),
    ('duplicate-poller', 'duplicate fields'),
    ('worker-restarted', 'container is not ready'),
    ('api-open', 'environment does not match'),
    ('api-not-ready', 'API readiness proof'),
])
def test_forward_readiness_uses_real_probe_contracts_on_exact_containers(monkeypatch, fault, error):
    monkeypatch.setenv('TWOBRAIN_RUNTIME_SECRET_GID', '1999')
    rows, observed, calls = {}, {}, []
    for index, name in enumerate(sorted(images.REQUIRED_CONSUMERS | {'rec-temporal'}), 1):
        container, image = f'{index:064x}', f'sha256:{index:064x}'
        status = dict(Status='running', Paused=False, Restarting=False,
                      StartedAt='2026-11-10T05:03:00Z', Health={'Status': 'healthy'})
        networks = {'twobrain-rec-media-private': {}}
        if name == 'rec-temporal':
            networks['twobrain-rec-private'] = {}
        env = [f'{images.NORMALIZATION_DISPATCH}=false']
        if name == 'rec-api':
            env.append(f'{images.NORMALIZATION_ENABLED}={"true" if fault == "api-open" else "false"}')
        if name == images.MEDIA_WORKER:
            if fault == 'media-network':
                networks['unexpected'] = {}
            env += [
                'TWOBRAIN_PLAYBACK_NORMALIZATION_TASK_QUEUE=twobrain-rec-playback-normalization',
                'TWOBRAIN_PLAYBACK_NORMALIZATION_WORKER_CONCURRENCY=1',
                'TWOBRAIN_MINIO_ACCESS_KEY_FILE=/run/secrets/twobrain_minio_media_access_key',
                'TWOBRAIN_MINIO_SECRET_KEY_FILE=/run/secrets/twobrain_minio_media_secret_key',
                'TWOBRAIN_WEB_RUNTIME_ENABLED=false',
            ]
        rows[container] = dict(Id=container, Image=image, State=status,
                               RestartCount=int(name == 'rec-processing-worker' and fault == 'worker-restarted'),
                               NetworkSettings={'Networks': networks}, Config=dict(User='twobrain', Env=env),
                               HostConfig=dict(IpcMode='private', GroupAdd=['1999'], ReadonlyRootfs=True, NanoCpus=1_000_000_000,
                                               Memory=1_073_741_824, PidsLimit=128, CapDrop=['ALL'],
                                               SecurityOpt=['no-new-privileges:true']))
        observed[name] = dict(id=container, image=image, started_at=status['StartedAt'])

    roles = {'rec-api': 'twobrain_rec_app', 'rec-processing-worker': 'twobrain_rec_app',
             'rec-maintenance': 'twobrain_rec_maintenance', images.MEDIA_WORKER: 'twobrain_rec_media'}

    def command(*argv, pass_fds=(), timeout):
        container = argv[2]
        assert container in rows
        if argv[:2] == ('docker', 'inspect'):
            assert timeout == 10
            return json.dumps([rows[container]])
        assert argv[:2] == ('docker', 'exec') and timeout == 45 and pass_fds == (9,)
        name = next(name for name, record in observed.items() if record['id'] == container)
        calls.append((name, argv[3:]))
        if argv[-1] == '/app/scripts/verify_runtime_database_identity.py':
            role = roles[name]
            assert argv[3:6] == ('env', f'TWOBRAIN_EXPECTED_DATABASE_ROLE={role}', 'python')
            return '\n'.join((
                'runtime_database_identity_result=pass', f'runtime_database_role={role}',
                'scheduler_function_access=' + ('allowed' if name == images.MEDIA_WORKER or fault == 'wrong-role'
                                                else 'denied'),
                'legacy_maintenance_access=' + ('allowed' if name == 'rec-maintenance' else 'denied'),
            ))
        if name == 'rec-api':
            assert argv[3:5] == ('python', '-c') and "HTTPConnection('127.0.0.1', 8080" in argv[-1]
            assert "connection.request('GET', '/api/v1/health/ready')" in argv[-1]
            return '{"status":"not_ready"}' if fault == 'api-not-ready' else '{"status":"ready"}'
        receipt = '{"result":"pass","workflow_poller":"ready","activity_poller":"ready"'
        if name == images.MEDIA_WORKER:
            assert argv[3:] == ('python', '/app/scripts/verify_playback_normalization_worker_ready.py', '--control')
            receipt += ',"mode":"pollers"' if fault == 'poller-only' else ',"mode":"control"'
            receipt += ',"profile_version":"review_m4a_aac_lc_48k_mono_64k_v1"'
            receipt += ',"validation_version":"legacy"' if fault == 'wrong-profile' else (
                ',"validation_version":"playback_validator_v1"')
        else:
            assert argv[3:] == ('python', '/app/scripts/verify_processing_worker_ready.py')
        if fault == 'duplicate-poller':
            receipt += ',"activity_poller":"ready"'
        return receipt + '}'

    monkeypatch.setattr(images, 'command', command)
    if error:
        with pytest.raises(ValueError, match=error):
            images.verify_forward_workers(observed, 9)
            images.verify_forward_api(observed, 9)
    else:
        images.verify_forward_workers(observed, 9)
        assert {name for name, _ in calls} == set(roles) - {'rec-api'}
        images.verify_forward_api(observed, 9)
        assert [name for name, _ in calls[-2:]] == ['rec-api', 'rec-api']


@pytest.fixture
def forward_public_channel():
    pkg, archive = b'approved pkg fixture', b'approved update fixture'
    origin = 'https://fixture.invalid'
    version = '2026.11.10.1'
    base = '/static/public/downloads/'
    archive_path = f'{base}GRAF-{version}.zip'
    feed = ('<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"><channel><item>'
            f'<enclosure url="{origin}{archive_path}" length="{len(archive)}" sparkle:edSignature="fixture"/>'
            '</item></channel></rss>').encode()
    record = dict(schema_version=1, source_sha='a' * 40, candidate_id='rc-forward', decision_digest='sha256:' + 'a' * 64,
                  origin=origin, version=version, pkg_sha256=hashlib.sha256(pkg).hexdigest(),
                  pkg_bytes=len(pkg), appcast_sha256=hashlib.sha256(feed).hexdigest(),
                  archive_sha256=hashlib.sha256(archive).hexdigest(), archive_bytes=len(archive))
    pkg_path = f'{base}graf.pkg?v={record["pkg_sha256"][:12]}'
    return record, {
        '/api/v1/health/live': b'{"status":"ok"}',
        '/api/v1/health/ready': b'{"status":"ready"}',
        '/download': f'<a href="{pkg_path}">macOS</a>'.encode(),
        pkg_path: pkg, f'{base}graf-appcast.xml': feed, archive_path: archive,
    }


def test_forward_public_process_rejects_untrusted_tls_and_tampered_package(tmp_path, monkeypatch, forward_public_channel):
    channel, served = forward_public_channel
    cert, key = tmp_path / 'localhost.pem', tmp_path / 'key.pem'
    subprocess.run(
        ['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes', '-days', '1',
         '-subj', '/CN=localhost', '-addext', 'subjectAltName=IP:127.0.0.1',
         '-keyout', key, '-out', cert],
        check=True, capture_output=True, timeout=15,
    )
    requested = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def do_GET(self):
            requested.append(self.path)
            body = served.get(self.path)
            if body is None:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Length', str(len(body)))
            if self.path == package:
                self.send_header('Cache-Control', 'public, max-age=31536000, immutable')
            self.end_headers()
            self.wfile.write(body)

    with ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
        origin = f'https://127.0.0.1:{server.server_port}'
        package, appcast, _ = tuple(served)[-3:]
        served[appcast] = served[appcast].replace(channel['origin'].encode(), origin.encode())
        channel.update(origin=origin, appcast_sha256=hashlib.sha256(served[appcast]).hexdigest())
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert, key)
        server.socket = context.wrap_socket(server.socket, server_side=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            monkeypatch.setenv('TWOBRAIN_PUBLIC_BASE_URL', origin)
            monkeypatch.delenv('SSL_CERT_FILE', raising=False)
            monkeypatch.delenv('SSL_CERT_DIR', raising=False)
            with (tmp_path / 'deploy.lock').open('ab') as lock:
                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                argv = [sys.executable, str(ROOT / 'infra/scripts/release-images.py'), 'verify-public-channel']
                rejected = subprocess.run(argv, input=json.dumps(channel), capture_output=True, text=True,
                                          pass_fds=(lock.fileno(),), timeout=10)
                assert rejected.returncode == 1 and 'CERTIFICATE_VERIFY_FAILED' in rejected.stderr
                assert requested == []
                monkeypatch.setenv('SSL_CERT_FILE', str(cert))
                images.verify_forward_public_process(channel, lock.fileno())
                assert requested == list(served)
                requested.clear()
                served[package] = b'X' + served[package][1:]
                rejected = subprocess.run(argv, input=json.dumps(channel), capture_output=True, text=True,
                                          pass_fds=(lock.fileno(),), timeout=10)
                assert rejected.returncode == 1 and 'differs from its approved bytes' in rejected.stderr
                assert requested == list(served)[:4]
        finally:
            server.shutdown()
            thread.join(timeout=5)


@pytest.mark.parametrize(('fault', 'reason'), [
    (None, None), ('digest', 'digest is invalid'), ('wrong-candidate', 'match the release decision'),
    ('foreign-origin', 'configured public address'), ('symlink', None),
])
def test_forward_public_approval_is_bound_to_exact_decision(tmp_path, monkeypatch, forward_public_channel, fault, reason):
    record, _ = forward_public_channel
    record_path = tmp_path / 'approved.json'
    record_path.write_text(json.dumps(record))
    args = argparse.Namespace(public_channel=record_path,
                              public_channel_digest='sha256:' + hashlib.sha256(record_path.read_bytes()).hexdigest(),
                              source_sha=record['source_sha'], candidate_id=record['candidate_id'],
                              decision_digest=record['decision_digest'])
    monkeypatch.setenv('TWOBRAIN_PUBLIC_BASE_URL', record['origin'])
    if fault == 'digest':
        record_path.write_bytes(record_path.read_bytes() + b' ')
    elif fault == 'wrong-candidate':
        args.decision_digest = 'sha256:' + 'b' * 64
    elif fault == 'foreign-origin':
        monkeypatch.setenv('TWOBRAIN_PUBLIC_BASE_URL', 'https://other.invalid')
    elif fault == 'symlink':
        args.public_channel = tmp_path / 'link.json'
        args.public_channel.symlink_to(record_path)
        with pytest.raises(OSError):
            images.approved_forward_channel(args)
        return
    if reason:
        with pytest.raises(ValueError, match=reason):
            images.approved_forward_channel(args)
    else:
        assert images.approved_forward_channel(args) == record


@pytest.mark.parametrize(('fault', 'error'), [
    (None, None), ('unready', 'public ready check failed'), ('redirect', 'direct HTTP 200'),
    ('wrong-link', 'does not link the approved'), ('package', 'differs from its approved bytes'),
    ('foreign-base', 'changes the link base'), ('duplicate-link', 'link is ambiguous'),
    ('cache', 'cache policy differs'), ('feed', 'feed differs from approval'),
    ('foreign-archive', 'archive link differs from approval'), ('archive', 'differs from its approved bytes'),
    ('oversize', 'exceeds its approved size'), ('short-response', 'ended before its declared size'),
])
def test_forward_public_checks_served_bytes_and_never_follows_redirects(monkeypatch, forward_public_channel, fault, error):
    record, bodies = forward_public_channel
    paths = list(bodies)
    pkg_path, feed_path, archive_path = paths[-3:]
    served = dict(bodies)
    if fault == 'unready':
        served[paths[1]] = b'{"status":"not_ready"}'
    elif fault == 'wrong-link':
        served['/download'] = b'<!-- ' + served['/download'] + b' -->'
    elif fault == 'foreign-base':
        served['/download'] = b'<base href="https://foreign.invalid/">' + served['/download']
    elif fault == 'duplicate-link':
        served['/download'] = served['/download'].replace(b'<a ', b'<a href="https://foreign.invalid/" ')
    elif fault == 'package':
        served[pkg_path] = b'X' + served[pkg_path][1:]
    elif fault == 'feed':
        served[feed_path] += b' '
    elif fault == 'foreign-archive':
        served[feed_path] = served[feed_path].replace(b'fixture.invalid', b'foreign.invalid')
        record['appcast_sha256'] = hashlib.sha256(served[feed_path]).hexdigest()
    elif fault == 'archive':
        served[archive_path] = b'X' + served[archive_path][1:]
    elif fault == 'oversize':
        served[archive_path] += b' '
    called = []

    class Connection:
        def __init__(self, host, port, timeout):
            assert (host, port, timeout) == ('fixture.invalid', None, 8)

        def request(self, method, path, *, headers):
            assert method == 'GET' and headers == {'Accept-Encoding': 'identity'}
            called.append(path)

        def getresponse(self):
            path = called[-1]
            response = io.BytesIO(served[path])
            response.status = 302 if fault == 'redirect' and path == '/download' else 200
            cache = 'public, max-age=31536000, immutable' if fault != 'cache' else 'private'
            headers = {'Cache-Control': cache, 'Location': 'https://foreign.invalid/'}
            if fault == 'short-response' and path == '/download':
                headers['Content-Length'] = str(len(served[path]) + 1)
            response.getheader = headers.get
            return response

        def close(self):
            pass

    monkeypatch.setattr(images, 'HTTPSConnection', Connection)
    if error:
        with pytest.raises(ValueError, match=error):
            images.verify_forward_public(record)
        if fault in ('redirect', 'wrong-link', 'foreign-base', 'duplicate-link'):
            assert called == paths[:3]
        if fault == 'foreign-archive':
            assert called == paths[:-1]
    else:
        images.verify_forward_public(record)
        assert called == paths


def test_forward_public_deadline_interrupts_wait_for_headers(monkeypatch):
    class SlowConnection:
        def __init__(self, *args, **kwargs):
            pass

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            time.sleep(2)
            pytest.fail('slow response exceeded the deadline')

        def close(self):
            pass

    handler = signal.getsignal(signal.SIGALRM)
    monkeypatch.setattr(images, 'PUBLIC_GET_DEADLINE', 0.05)
    monkeypatch.setattr(images, 'HTTPSConnection', SlowConnection)
    with pytest.raises(ValueError, match='public response deadline'):
        images.forward_public_get('https://fixture.invalid', '/download', 1024)
    assert signal.getsignal(signal.SIGALRM) == handler
    assert signal.getitimer(signal.ITIMER_REAL) == (0, 0)


def test_forward_public_parent_deadline_terminates_stuck_child(tmp_path, monkeypatch, forward_public_channel):
    channel, _ = forward_public_channel
    stuck = tmp_path / 'stuck.py'
    stuck.write_text('import time\ntime.sleep(30)\n')
    monkeypatch.setattr(images, '__file__', str(stuck))
    monkeypatch.setattr(images, 'PUBLIC_PROOF_DEADLINE', 0.15)
    with (tmp_path / 'lock').open('ab') as lock, pytest.raises(subprocess.TimeoutExpired):
        images.verify_forward_public_process(channel, lock.fileno())


@pytest.mark.parametrize(('fault', 'error'), [
    (None, None),
    ('digest', 'bytes differ'),
    ('no-go', 'lacks an exact go decision'),
    ('failed', 'Full CI evidence was refused'),
    ('stale', 'Full CI evidence was refused'),
    ('wrong-observed-sha', 'Full CI evidence was refused'),
    ('symlink', None),
])
def test_forward_remote_approval_checks_exact_bytes_with_candidate_validator(tmp_path, monkeypatch, fault, error):
    source = 'a' * 40
    candidate = 'rc-20260831T000000Z-aaaaaaaaaaaa'
    decision, full = tmp_path / 'decision.json', tmp_path / 'full.json'
    evidence = dict(
        run_id='run-1', lane='full', requested_sha=source, observed_sha_start=source,
        observed_sha_end='b' * 40 if fault == 'wrong-observed-sha' else source,
        status=fault if fault in ('failed', 'stale') else 'passed',
        started_at='2026-08-31T00:00:00Z', finished_at='2026-08-31T00:01:00Z',
        commands=['infra/scripts/ci-local.sh --full'], skipped_gates=[], scope='release candidate',
        artifact_digests={'full-log': 'sha256:' + 'b' * 64}, candidate_id=candidate,
        authoritative_full=True, component_shas={'server': source, 'macos': source},
    )
    if evidence['status'] != 'passed':
        evidence['reason'] = 'fixture run did not pass'
    full.write_text(json.dumps(evidence))
    full_digest = 'sha256:' + hashlib.sha256(full.read_bytes()).hexdigest()
    decision.write_text(json.dumps(dict(
        status='no-go' if fault == 'no-go' else 'go', candidate_id=candidate, source_sha=source,
        full_evidence_digest=full_digest,
    )))
    args = argparse.Namespace(source_sha=source, candidate_id=candidate, release_decision=decision, full_evidence=full,
                              full_digest=full_digest,
                              decision_digest='sha256:' + hashlib.sha256(decision.read_bytes()).hexdigest())
    calls = []

    def git(*argv, timeout):
        assert argv == ('git', 'show', f'{source}:scripts/validate-ci-evidence.py') and timeout == 10
        calls.append(argv)
        return (ROOT / 'scripts/validate-ci-evidence.py').read_text()

    monkeypatch.setattr(images, 'command', git)
    if fault == 'digest':
        full.write_bytes(full.read_bytes() + b' ')
    if fault == 'symlink':
        target = full.with_name('target.json')
        full.rename(target)
        full.symlink_to(target)
        with pytest.raises(OSError):
            images.verify_forward_release_approval(args)
    elif error:
        with pytest.raises(ValueError, match=error):
            images.verify_forward_release_approval(args)
    else:
        images.verify_forward_release_approval(args)
    assert len(calls) == int(fault in (None, 'failed', 'stale', 'wrong-observed-sha'))


@pytest.mark.parametrize(('extra', 'error'), [
    (['--branch', 'feature', '--candidate', 'decision.json'], 'forward_preflight_requires_master_candidate_and_full_ci'),
    (['--branch', 'master'], 'forward_preflight_requires_master_candidate_and_full_ci'),
    (['--branch', 'master', '--candidate', 'decision.json', '--skip-local-ci'],
     'forward_preflight_requires_master_candidate_and_full_ci'),
    (['--execute'], 'conflicting_release_modes'),
])
def test_forward_preflight_cannot_fall_through_to_another_release_mode(extra, error):
    result = subprocess.run(
        ['bash', str(ROOT / 'infra/scripts/cd-remote.sh'), '--forward-preflight',
         '1' * 32, '2' * 32, '/test/archive', *extra],
        cwd=ROOT, text=True, capture_output=True,
    )
    assert result.returncode != 0
    assert f'reason={error}' in result.stdout + result.stderr


@pytest.mark.parametrize("mode", ["forward-preflight", "forward-execute"])
def test_forward_wrapper_uses_release_gate_and_verified_candidate_code(tmp_path, mode):
    local, remote, tools = (tmp_path / name for name in ('local', 'remote', 'tools'))
    local.mkdir()
    tools.mkdir()
    # The desktop python3 shim starts an extra process; use the actual interpreter.
    (tools / 'python3').symlink_to(Path(sys.executable).resolve())

    def git(*args, cwd=local):
        return subprocess.check_output(
            ['git', '-c', 'user.name=Test', '-c', 'user.email=test@example.invalid', *args],
            cwd=cwd, text=True, stderr=subprocess.PIPE,
        ).strip()

    def executable(path, contents):
        path.write_text(contents)
        path.chmod(0o755)

    git('init', '-qb', 'master')
    script = local / 'infra/scripts/cd-remote.sh'
    script.parent.mkdir(parents=True)
    helper = script.with_name('release-images.py')
    helper.write_text('raise SystemExit(2)\n')
    (local / '.gitignore').write_text('/.env\n')
    git('add', '.')
    git('commit', '-qm', 'failed release')
    failed = git('rev-parse', 'HEAD')
    git('clone', '-q', str(local), str(remote))
    script.write_bytes((ROOT / 'infra/scripts/cd-remote.sh').read_bytes())
    executable(script.with_name('release-candidate.sh'), '#!/bin/sh\n[ "$1" = validate ] && [ "$3" = --current ]\n')
    validator = local / 'scripts/validate-ci-evidence.py'
    validator.parent.mkdir()
    validator.write_text('def validate(evidence):\n    return []\n')
    archive = str(tmp_path / 'archive with spaces')
    public_approval = str(tmp_path / 'approval with spaces')
    channel_digest = "sha256:" + "9" * 64
    helper.write_text(f'''import fcntl, os, signal, subprocess, sys, time
assert os.fstat(9).st_ino == os.stat(".git/twobrain-rec-deploy.lock").st_ino
if sys.argv[1] == "check-deployment-lock":
    assert sys.argv[2:] == ["--deployment-lock-fd", "9"]
    assert "GRAF_TEST_SCOPE" not in os.environ
elif sys.argv[1] in {{"check-forward-claim", "check-forward-execution", "start-forward", "confirm-forward"}}:
    assert os.environ["GRAF_TEST_SCOPE"] == "isolated"
    args = dict(zip(sys.argv[2::2], sys.argv[3::2], strict=True))
    assert args["--deployment-lock-fd"] == "9"
    checkout = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    if sys.argv[1] == "check-forward-claim":
        assert args["--checkout-sha"] == checkout == {failed!r}
    else:
        assert args["--public-channel"] == {public_approval!r}
        assert args["--public-channel-digest"] == {channel_digest!r}
        assert os.path.isabs(args["--release-decision"]) and os.path.isabs(args["--full-evidence"])
        if sys.argv[1] == "check-forward-execution":
            assert args["--checkout-sha"] == checkout
        else:
            assert __file__.endswith("infra/scripts/release-images.py")
            assert checkout == os.environ["GRAF_TEST_CANDIDATE_SHA"]
            assert os.environ["TWOBRAIN_PRODUCTION_RELEASE_GATE"] == "1"
            if os.environ.get("GRAF_TEST_TERMINATE"):
                def terminated(_signum, _frame):
                    print("fixture_forward_child_received_term", file=sys.stderr)
                    raise SystemExit(41)
                signal.signal(signal.SIGTERM, terminated)
                with open(".git/twobrain-rec-deploy.lock", "rb") as separate_lock:
                    try:
                        fcntl.flock(separate_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        pass
                    else:
                        raise SystemExit("deployment lock was not held")
                os.kill(os.getppid(), signal.SIGTERM)
                time.sleep(5)
                raise SystemExit(42)
    assert args["--failed-attempt"] == {"1" * 32!r} and args["--attempt-id"] == {"2" * 32!r}
    assert args["--backup-directory"] == {archive!r}
    assert args["--candidate-id"] == "rc-fixture"
    assert args["--decision-digest"] == os.environ["GRAF_TEST_DECISION_DIGEST"]
    assert args["--full-digest"] == os.environ["GRAF_TEST_FULL_DIGEST"]
    assert args["--source-sha"] == os.environ["GRAF_TEST_CANDIDATE_SHA"]
    if os.environ.get("GRAF_TEST_REFUSE"):
        sys.exit(1)
    print({{"check-forward-claim": "forward_claim_verified", "check-forward-execution": "forward_execution_verified",
            "start-forward": "forward_execute_result=pass", "confirm-forward": "forward_confirm_result=pass"}}[sys.argv[1]])
else:
    sys.exit(99)
''')
    git('add', '.')
    git('commit', '-qm', 'candidate')
    source = git('rev-parse', 'HEAD')
    git('remote', 'add', 'origin', str(local))
    (remote / '.env').write_text('GRAF_TEST_SCOPE=isolated\n')

    full = tmp_path / 'full.json'
    full.write_text(json.dumps(dict(candidate_id='rc-fixture', requested_sha=source,
                                    lane='full', authoritative_full=True)))
    full_digest = 'sha256:' + hashlib.sha256(full.read_bytes()).hexdigest()
    decision = tmp_path / 'decision.json'
    decision.write_text(json.dumps(dict(candidate_id='rc-fixture', source_sha=source, status='go',
                                        full_evidence_digest=full_digest)))
    executable(tools / 'ssh', '#!/bin/sh\n[ "$1" = fixture-host ] || exit 93\nexec /bin/bash -c "$2"\n')
    if not Path('/usr/bin/flock').exists():  # macOS: exercise the same inherited FD with fcntl.
        executable(tools / 'lock9', '#!/usr/bin/env python3\nimport fcntl\nfcntl.flock(9, fcntl.LOCK_EX | fcntl.LOCK_NB)\n')
        executable(tools / 'bash', '#!/bin/sh\n'
                   'sed "s|/usr/bin/flock -n 9|lock9|" "$1" > "$1.fixture" || exit 1\n'
                   'mv "$1.fixture" "$1" || exit 1\nexec /bin/bash "$@"\n')

    env = dict(os.environ, PATH=f'{tools}{os.pathsep}{os.environ["PATH"]}',
               TWOBRAIN_DEPLOY_HOST='fixture-host', TWOBRAIN_DEPLOY_PATH=str(remote),
               TWOBRAIN_DEPLOY_BRANCH='master', PYTHONDONTWRITEBYTECODE='1', GRAF_TEST_CANDIDATE_SHA=source,
               GRAF_TEST_DECISION_DIGEST='sha256:' + hashlib.sha256(decision.read_bytes()).hexdigest(),
               GRAF_TEST_FULL_DIGEST=full_digest)
    command = ['/bin/bash', str(script), f'--{mode}', '1' * 32, '2' * 32, archive]
    if mode == "forward-execute":
        command += [public_approval, channel_digest, str(decision), str(full)]
    command += ['--candidate', str(decision), '--evidence', str(full)]
    verdict = mode.replace("-", "_") + "_result"
    for refuse in (True, False, False):
        result = subprocess.run(command, cwd=local, env={**env, 'GRAF_TEST_REFUSE': '1' if refuse else ''},
                                text=True, capture_output=True)
        assert result.returncode == int(refuse), result.stdout + result.stderr
        assert f'{verdict}={"blocked" if refuse else "pass"}' in result.stdout
        assert 'deploy_result=pass' not in result.stdout
        moved = not refuse and mode == "forward-execute"
        assert git('rev-parse', 'HEAD', cwd=remote) == (source if moved else failed)
        assert (helper.read_bytes() == (remote / 'infra/scripts/release-images.py').read_bytes()) == moved
    if mode == "forward-execute":
        result = subprocess.run(command, cwd=local, env={**env, 'GRAF_TEST_TERMINATE': '1'},
                                text=True, capture_output=True, timeout=15)
        assert result.returncode == 1
        assert 'fixture_forward_child_received_term' in result.stdout
        assert 'reason=forward_execution_interrupted' in result.stdout
        assert f'{verdict}=pass' not in result.stdout
        upstream = tmp_path / 'upstream'
        git('clone', '-q', str(local), str(upstream))
        git('commit', '--allow-empty', '-qm', 'master advanced', cwd=upstream)
        for repo in (local, remote):
            git('remote', 'set-url', 'origin', str(upstream), cwd=repo)
            git('fetch', '-q', 'origin', 'master', cwd=repo)
        result = subprocess.run(command, cwd=local, env=env, text=True, capture_output=True, timeout=15)
        assert result.returncode == 1 and 'reason=origin_sha_mismatch' in result.stdout
        command[2] = '--forward-confirm'
        git('checkout', '--detach', source)
        result = subprocess.run(command, cwd=local, env=env, text=True, capture_output=True, timeout=15)
        assert result.returncode == 0 and 'forward_confirm_result=pass' in result.stdout, result.stdout + result.stderr
        assert git('rev-parse', 'HEAD', cwd=remote) == source
        assert git('rev-parse', 'origin/master', cwd=remote) != source
    with (remote / '.git/twobrain-rec-deploy.lock').open('ab') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(command, cwd=local, env=env, text=True, capture_output=True)
        assert result.returncode == 1 and 'reason=deploy_already_running' in result.stdout
    for invalid_env in ('printf "forward_claim_verified\\n"; exit 0\n', 'false\nGRAF_TEST_SCOPE=isolated\n'):
        (remote / '.env').write_text(invalid_env)
        result = subprocess.run(command, cwd=local, env=env, text=True, capture_output=True)
        reason = ('remote_forward_confirm_result_missing' if mode == 'forward-execute' and 'exit 0' in invalid_env
                  else 'forward_evidence_unverified')
        assert result.returncode == 1 and f'reason={reason}' in result.stdout
        assert f'{verdict}=pass' not in result.stdout
    full.write_text('{}')
    result = subprocess.run(command, cwd=local, env=env, text=True, capture_output=True)
    assert result.returncode == 1 and 'reason=authoritative_full_evidence_invalid' in result.stdout


@pytest.mark.parametrize('outcome', ['unchanged', 'restored', 'compatibility', 'rollback-failed', 'public-failed',
                                     'final-write-failed', 'sealed-before-mutation', 'observed', 'observe-failed',
                                     'observe-timeout',
                                     'failed-before-up'])
def test_runtime_trap_only_completes_verified_recovery(tmp_path, outcome):
    import os
    import subprocess
    runtime = (ROOT / 'infra/scripts/cd-remote-runtime.sh').read_text()
    block = runtime[runtime.index('rollback_on_exit()'):runtime.index('trap rollback_on_exit EXIT')]
    helper = tmp_path / 'release-images.py'
    helper.touch()
    if outcome == 'sealed-before-mutation':
        (tmp_path / images.NO_ROLLBACK).touch()
    script = '''
set -euo pipefail
compose=(compose_stub)
runtime_mutated=1
deployment_complete=0
images_recovery_verified=0
images_result_write_failed=0
image_attempt_id=123
runtime_release_lock_fd=9
image_helper="$TEST_HELPER"
image_attempt="${image_helper%/*}"
previous_sha=previous
backup_reference=backup
[[ "$OUTCOME" != unchanged && "$OUTCOME" != sealed-before-mutation ]] || runtime_mutated=0
[[ "$OUTCOME" != final-write-failed ]] || images_result_write_failed=1
case "$OUTCOME" in
  observed|observe-failed|observe-timeout) storage_recovery_start_mode=reconciled; runtime_up_attempted=1 ;;
  failed-before-up) storage_recovery_start_mode=reconciled; runtime_up_attempted=0 ;;
esac
compose_stub() { printf 'compose:%s\n' "$*" >>"$image_attempt/failure-trace"; }
restore_public_download() { [[ "$OUTCOME" != public-failed ]]; }
restore_previous_runtime() {
  [[ "$OUTCOME" != restored && "$OUTCOME" != final-write-failed ]] || images_recovery_verified=1
  return 0
}
git() { touch "$image_attempt/source-reset"; }
verify_public_download() { :; }
curl() { :; }
cleanup_runtime_files() { :; }
timeout() {
  [[ "$1 $2" == "--kill-after=1s 5s" ]] || return 9
  shift 2
  if [[ "$OUTCOME" == observe-timeout ]]; then
    printf 'observe:timeout\n' >>"$image_attempt/failure-trace"
    return 124
  fi
  "$@"
}
python3() {
  if [[ "$2" == observe-start ]]; then
    printf 'observe:%s\n' "$*" >>"$image_attempt/failure-trace"
    [[ "$OUTCOME" != observe-failed ]]
  else
    printf 'finish:%s\n' "$*"
  fi
}
''' + block + '\nset +e\nfalse\nrollback_on_exit\n'
    result = subprocess.run(['bash', '-c', script], text=True, capture_output=True,
                            env={**os.environ, 'OUTCOME': outcome, 'TEST_HELPER': str(helper)})
    assert result.returncode == 1
    assert ('finish:' in result.stdout) == (outcome in {'unchanged', 'restored'})
    if outcome in {'unchanged', 'restored'}:
        assert f'finish {outcome} --attempt-id 123' in result.stdout
    if outcome == 'sealed-before-mutation':
        assert 'rollback_target=forward_fix_required' in result.stdout
        assert not (tmp_path / 'source-reset').exists()
    if outcome in {'observed', 'observe-failed', 'observe-timeout'}:
        trace = (tmp_path / 'failure-trace').read_text()
        assert trace.index('observe:') < trace.index('compose:stop')
        assert ('runtime_start_observation=unconfirmed' in result.stdout) == (outcome != 'observed')
    else:
        trace = tmp_path / 'failure-trace'
        assert not trace.exists() or 'observe:' not in trace.read_text()


@pytest.mark.parametrize('succeed', [True, False])
def test_terminal_record_cannot_be_followed_by_signal_rollback(succeed):
    import subprocess
    runtime = (ROOT / 'infra/scripts/cd-remote-runtime.sh').read_text()
    start = runtime.index("trap '' INT TERM")
    block = runtime[start:runtime.index('if [[ -n "$public_download_backup" ]]', start)]
    script = '''
set -euo pipefail
image_helper=/private-helper
image_attempt_id=123
images_result_write_failed=0
trap 'echo rollback:exit' EXIT
trap 'echo rollback:signal; exit 143' TERM
python3() { kill -TERM $$; return ''' + ('0' if succeed else '1') + '''; }
''' + block + '\necho finalized\n'
    result = subprocess.run(['bash', '-c', script], text=True, capture_output=True)
    assert result.returncode == (0 if succeed else 1), result.stderr
    assert 'rollback:signal' not in result.stdout
    assert ('rollback:exit' in result.stdout) is not succeed
    assert ('finalized' in result.stdout) is succeed


def test_source_drift_during_build_cannot_publish_reusable_cache(docker):
    docker.state['dirty_after_build'] = True
    with pytest.raises(ValueError, match='source changed during preparation'):
        images.prepare(docker.args)
    assert not list(docker.directory.glob('images/*.json'))
    assert not (images.active(docker.directory) / 'result.json').exists()


def test_active_pointer_is_retained_after_directory_persistence_error(tmp_path, monkeypatch):
    path = tmp_path / 'active.json'
    images.write(path, {'attempt': '1'*32})
    real_fsync = images.os.fsync
    def fail_directory(fd):
        import stat
        if stat.S_ISDIR(images.os.fstat(fd).st_mode):
            raise OSError('disk failure')
        return real_fsync(fd)
    monkeypatch.setattr(images.os, 'fsync', fail_directory)
    with pytest.raises(OSError):
        images.write(path, {'attempt': '2'*32})
    assert images.read(path)['attempt'] == '2'*32

@pytest.mark.parametrize(('revision', 'db_exit', 'reason'), [
    ('0110_calendar_upload_pin', 0, 'unpublished_f200_schema_revision'),
    ('0111_strict_upload_journal', 0, 'unpublished_f200_schema_revision'),
    ('0112_f200_calendar_upload_pin', 0, 'unpublished_f200_schema_revision'),
    ('0113_f200_strict_upload_journal', 0, 'unpublished_f200_schema_revision'),
    ('0113_f200_calendar_upload_pin', 0, 'unpublished_f200_schema_revision'),
    ('0114_f200_strict_upload_journal', 0, 'unpublished_f200_schema_revision'),
    ('unknown_revision', 0, 'previous_schema_head_unavailable'),
    ('0113_fair_use_operator_history', 0, 'runtime_secret_group_unsafe'),
    ('', 0, 'previous_schema_head_unavailable'),
    ('0111_receipt_observation_deltas\nother_head', 0, 'previous_schema_head_unavailable'),
    ('0111_receipt_observation_deltas', 3, 'previous_schema_head_unavailable'),
    ('0111_receipt_observation_deltas', 0, 'runtime_secret_group_unsafe'),
])
def test_runtime_rejects_incompatible_f200_schema_before_release_mutations(
    tmp_path, monkeypatch, revision, db_exit, reason,
):
    monkeypatch.chdir(tmp_path)
    subprocess.run(['git', 'init', '-q', '-b', 'master'], check=True)
    subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                    'commit', '-q', '--allow-empty', '-m', 'fixture'], check=True)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
    scripts = tmp_path / 'infra/scripts'
    scripts.mkdir(parents=True)
    (scripts / 'release-images.py').write_bytes((ROOT / 'infra/scripts/release-images.py').read_bytes())
    versions = Path('apps/server/src/twobrain_rec_server/db/migrations/versions')
    shutil.copytree(ROOT / versions, tmp_path / versions)
    (tmp_path / '.env').write_text('TWOBRAIN_RUNTIME_SECRET_GID=0\n')
    tools = tmp_path / 'bin'
    tools.mkdir()
    docker = tools / 'docker'
    docker.write_text(
        '#!/bin/sh\nprintf "%s\\n" "$*" >> "$TRACE"\n'
        '[ "$*" = "compose --profile operations -f infra/docker-compose.yml exec -T rec-postgres '
        'psql -U twobrain_rec -d twobrain_rec -Atc select version_num from alembic_version" ] || exit 97\n'
        'printf "%s\\n" "$SCHEMA_REVISION"\nexit "$DB_EXIT"\n'
    )
    docker.chmod(0o755)
    cleanup = tools / 'rm'
    cleanup.write_text('#!/bin/sh\nexit 0\n')
    cleanup.chmod(0o755)
    trace = tmp_path / 'docker-trace'
    monkeypatch.setenv('PATH', str(tools) + os.pathsep + os.environ['PATH'])
    monkeypatch.setenv('TRACE', str(trace))
    monkeypatch.setenv('SCHEMA_REVISION', revision)
    monkeypatch.setenv('DB_EXIT', str(db_exit))
    monkeypatch.setenv('TWOBRAIN_PRODUCTION_RELEASE_GATE', '1')
    monkeypatch.setenv('TWOBRAIN_PRODUCTION_RELEASE_LOCK_HELD', '1')
    lock_path = tmp_path / '.git/twobrain-rec-deploy.lock'
    with lock_path.open('ab') as locked:
        fcntl.flock(locked, fcntl.LOCK_EX | fcntl.LOCK_NB)
        result = subprocess.run(
            ['bash', '-c', 'exec 9>&"$1"; shift; exec bash "$@"', 'schema-fixture', str(locked.fileno()),
             str(ROOT / 'infra/scripts/cd-remote-runtime.sh'), 'master', source, source,
             'rc-fixture', 'decision', 'full'],
            pass_fds=(locked.fileno(),), capture_output=True, text=True,
        )
    assert result.returncode == 1 and f'reason={reason}' in result.stdout, result
    assert len(trace.read_text().splitlines()) == 1
    assert not (tmp_path / '.git/graf-release-images').exists()
    assert not (tmp_path / 'secrets').exists()
