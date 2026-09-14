from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('release_images', ROOT / 'infra/scripts/release-images.py')
images = importlib.util.module_from_spec(spec)
spec.loader.exec_module(images)


@pytest.fixture
def docker(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
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
        ref = f'twobrain-rec-{service}' if own else old[service]['image']
        iid = 'sha256:' + f'{index:064x}'
        info = dict(Id=iid, Os='linux', Architecture='amd64', Config=dict(Labels={}, Env=[]))
        refs[ref] = refs[iid] = info
        if service not in {'rec-migrate', 'rec-db-runtime-bootstrap', 'rec-minio-init', 'rec-prompt-optimization-worker'}:
            running.append(dict(Id=f'{index:064x}', Image=iid, State=dict(Running=True),
                                Config=dict(Labels={'com.docker.compose.project': 'twobrain-rec',
                                                    'com.docker.compose.service': service})))
    new = copy.deepcopy(old)
    calls = []
    state = dict(platform='linux/x86_64', fail=None)
    def command(*args, input=None):
        calls.append(args)
        if state['fail'] and args[:len(state['fail'])] == state['fail']:
            raise ValueError('injected command failure')
        if args[:2] == ('git', 'rev-parse'):
            return str(tmp_path / '.state') if '--git-path' in args else source
        if args[:2] == ('git', 'status'):
            return ' M source' if state.get('dirty_after_build') and any(c[:2] == ('docker', 'build') for c in calls) else ''
        if args[:2] == ('git', 'show'):
            return 'old' if args[-1].startswith(previous) else 'new'
        if args[:2] == ('docker', 'compose'):
            return json.dumps(dict(name='twobrain-rec', services=old if input == 'old' else new))
        if args[:2] == ('docker', 'info'):
            return state['platform']
        if args[:2] == ('docker', 'ps'):
            return '\n'.join(row['Id'] for row in running)
        if args[:2] == ('docker', 'inspect'):
            return json.dumps(running)
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
                              attempt_id='1'*32)
    return argparse.Namespace(args=args, refs=refs, running=running, old=old, new=new, calls=calls,
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


def test_standalone_uses_completed_current_images_and_blocks_incomplete(docker):
    assert images.current_override() is None
    images.prepare(docker.args)
    with pytest.raises(OSError):
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


@pytest.mark.parametrize('outcome', ['unchanged', 'restored', 'compatibility', 'rollback-failed', 'public-failed', 'final-write-failed'])
def test_runtime_trap_only_completes_verified_recovery(tmp_path, outcome):
    import os
    import subprocess
    runtime = (ROOT / 'infra/scripts/cd-remote-runtime.sh').read_text()
    block = runtime[runtime.index('rollback_on_exit()'):runtime.index('trap rollback_on_exit EXIT')]
    helper = tmp_path / 'release-images.py'
    helper.touch()
    script = '''
set -euo pipefail
compose=(compose_stub)
runtime_mutated=1
deployment_complete=0
images_recovery_verified=0
images_result_write_failed=0
image_attempt_id=123
image_helper="$TEST_HELPER"
previous_sha=previous
backup_reference=backup
[[ "$OUTCOME" != unchanged ]] || runtime_mutated=0
[[ "$OUTCOME" != final-write-failed ]] || images_result_write_failed=1
compose_stub() { :; }
restore_public_download() { [[ "$OUTCOME" != public-failed ]]; }
restore_previous_runtime() {
  [[ "$OUTCOME" != restored && "$OUTCOME" != final-write-failed ]] || images_recovery_verified=1
  return 0
}
git() { :; }
verify_public_download() { :; }
curl() { :; }
cleanup_runtime_files() { :; }
python3() { printf 'finish:%s\n' "$*"; }
''' + block + '\nset +e\nfalse\nrollback_on_exit\n'
    result = subprocess.run(['bash', '-c', script], text=True, capture_output=True,
                            env={**os.environ, 'OUTCOME': outcome, 'TEST_HELPER': str(helper)})
    assert result.returncode == 1
    assert ('finish:' in result.stdout) == (outcome in {'unchanged', 'restored'})
    if outcome in {'unchanged', 'restored'}:
        assert f'finish {outcome} --attempt-id 123' in result.stdout


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
