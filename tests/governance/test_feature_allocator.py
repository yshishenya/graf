from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
from concurrent.futures import ThreadPoolExecutor

import pytest

ROOT = Path(__file__).resolve().parents[2]


def allocator():
    spec = importlib.util.spec_from_file_location('feature_allocator', ROOT / 'scripts/claim-feature.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('ref', [
    'refs/tags/graf-release/6785-final-synthetic',
    'refs/codex/turn-diffs/captures/27656752-session/base',
    'refs/heads/codex/turn-diffs/captures/27656752-session',
    'origin/codex/captures/27656752-session',
    'refs/heads/graf-release/6784-synthetic',
    'refs/heads/codex/54321-capture/base',
    'refs/heads/codex/20260908-123456-check',
])
def test_service_refs_and_nested_numbers_are_not_feature_ids(ref):
    assert allocator()._ids_from_refs([ref]) == set()


def test_real_branch_ids_including_four_digits_remain_occupied():
    assert allocator()._ids_from_refs([
        'refs/heads/codex/258-meeting-progress-recovery',
        'refs/remotes/upstream/alice/app/1024-real-feature',
        'origin/codex/259-audit-remediation',
    ]) == {258, 259, 1024}


def test_sequence_starts_after_specs_and_skips_local_and_remote_claims(tmp_path, monkeypatch):
    module = allocator()
    (tmp_path / 'specs/258-current').mkdir(parents=True)
    (tmp_path / 'specs/20260908-123456-draft').mkdir()
    calls = []

    def github(_root, **kwargs):
        assert kwargs['strict'] is True
        calls.append(kwargs['candidates'])
        return {260, 6788} if kwargs['candidates'] == {260} else set()

    monkeypatch.setattr(module, '_github_ids', github)
    assert module._next_feature_id(tmp_path, {258, 259, 6788, 27656752}) == 261
    assert calls == [{260}, {261}]
    monkeypatch.setattr(module, '_github_ids', lambda *_a, **_k: pytest.fail('offline used network'))
    assert module._next_feature_id(tmp_path, {258, 6788}, offline=True) == 259


def test_spec_sequence_can_reach_1000(tmp_path):
    (tmp_path / 'specs/999-current').mkdir(parents=True)
    assert allocator()._next_feature_id(tmp_path, {999, 1000, 6788}, offline=True) == 1001


@pytest.mark.parametrize('response', [
    {'items': [], 'total_count': 1},
    {'items': [], 'total_count': 0, 'incomplete_results': True},
])
def test_incomplete_github_search_fails_closed(tmp_path, monkeypatch, response):
    module = allocator()

    def run(args, **kwargs):
        output = 'https://github.com/example/project.git' if args[:2] == ['git', 'config'] else json.dumps(response)
        return subprocess.CompletedProcess(args, 0, stdout=output)

    monkeypatch.setattr(module.subprocess, 'run', run)
    with pytest.raises(SystemExit, match='cannot inspect complete GitHub'):
        module._github_ids(tmp_path, strict=True, candidates={259})


def test_online_suggestion_does_not_ignore_github_failure(tmp_path, monkeypatch):
    module = allocator()
    monkeypatch.setattr(module, '_git_refs', lambda *_a, **_k: [])
    monkeypatch.setattr(module, '_local_claim_ids', lambda *_a: set())

    def github(_root, **kwargs):
        assert kwargs['strict'] is True
        raise SystemExit('GitHub unavailable')

    monkeypatch.setattr(module, '_github_ids', github)
    with pytest.raises(SystemExit, match='GitHub unavailable'):
        module.main(['--root', str(tmp_path), '--json'])
    assert not (tmp_path / '.specify/feature.json').exists()


@pytest.mark.parametrize('created,existing,success', [
    (0, [], True), (1, [{'name': 'feature:259'}], True),
    (1, [{'name': 'feature:2590'}], False),
])
def test_label_creation_is_exact_and_does_not_overwrite(tmp_path, monkeypatch, created, existing, success):
    module = allocator()
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        assert '--force' not in args
        return subprocess.CompletedProcess(args, created if args[2] == 'create' else 0, stdout=json.dumps(existing))

    monkeypatch.setattr(module.subprocess, 'run', run)
    if success:
        module._ensure_feature_label(tmp_path, 259)
    else:
        with pytest.raises(SystemExit, match='cannot prepare label'):
            module._ensure_feature_label(tmp_path, 259)
    assert len(calls) == (1 if created == 0 else 2)


def test_padded_feature_marker_is_validated(tmp_path, monkeypatch):
    module = allocator()
    monkeypatch.setattr(module.subprocess, 'run', lambda args, **_kwargs: subprocess.CompletedProcess(
        args, 0, stdout=json.dumps({'number': 42, 'state': 'OPEN', 'title': '[002] Feature',
                                  'body': '', 'labels': [{'name': 'feature:002'}]})))
    module._github_umbrella(tmp_path, 42, 2)


@pytest.fixture
def git_project(tmp_path):
    project = tmp_path / 'project'
    project.mkdir()
    subprocess.run(['git', 'init', '-q', str(project)], check=True)
    for key, value in [('user.email', 'test@example.invalid'), ('user.name', 'Allocator Test')]:
        subprocess.run(['git', 'config', key, value], cwd=project, check=True)
    (project / 'specs/258-current').mkdir(parents=True)
    (project / 'specs/258-current/spec.md').write_text('Test specification\n')
    (project / '.gitignore').write_text('.specify/feature.json\n')
    subprocess.run(['git', 'add', '.'], cwd=project, check=True)
    subprocess.run(['git', 'commit', '-qm', 'fixture'], cwd=project, check=True)
    return project


def test_real_git_inventory_ignores_tags_and_internal_refs(git_project):
    for ref in ['refs/tags/graf-release/6785-final-synthetic',
                'refs/codex/turn-diffs/captures/27656752-session/base',
                'refs/heads/codex/259-next', 'refs/remotes/origin/codex/1024-real']:
        subprocess.run(['git', 'update-ref', ref, 'HEAD'], cwd=git_project, check=True)
    module = allocator()
    assert module._ids_from_refs(module._git_refs(git_project, strict=True)) == {259, 1024}


@pytest.mark.parametrize('slug', ['fix_v2', 'fix.v2'])
@pytest.mark.parametrize('source', ['specs', 'refs/heads/codex', 'refs/remotes/origin/codex'])
def test_existing_slug_characters_keep_feature_number_occupied(git_project, slug, source):
    module = allocator()
    name = f'259-{slug}'
    if source == 'specs':
        (git_project / source / name).mkdir()
    else:
        subprocess.run(['git', 'update-ref', f'{source}/{name}', 'HEAD'], cwd=git_project, check=True)
    occupied = module._ids_from_specs(git_project) | module._ids_from_refs(module._git_refs(git_project))
    assert occupied == {258, 259}
    assert module._next_feature_id(git_project, occupied, offline=True) == 260


def test_concurrent_stale_allocations_create_only_one_umbrella(git_project, monkeypatch):
    module = allocator()
    monkeypatch.setattr(module, '_github_ids', lambda *_a, **_k: set())
    created = []
    monkeypatch.setattr(module, '_create_github_umbrella', lambda *_a: created.append(777) or 777)

    def allocate():
        try:
            return module.main(['--root', str(git_project), '--allocate', '--branch',
                                'codex/259-next', '--slug', 'next', '--json'])
        except SystemExit as exc:
            return str(exc)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: allocate(), range(2)))
    assert created == [777]
    assert results.count(0) == 1
    assert any('next collision-free Feature 260' in str(r) for r in results)
    assert set(module._local_claim_records(git_project)) == {'259'}


@pytest.mark.parametrize('shell', ['bash', 'python', 'powershell'])
@pytest.mark.parametrize('dry_run', [True, False])
def test_branch_entrypoints_use_allocator_not_largest_ref(git_project, tmp_path, monkeypatch, shell, dry_run):
    if shell == 'powershell' and not shutil.which('pwsh'):
        pytest.skip('pwsh is not installed')
    project = git_project
    shutil.copytree(ROOT / '.specify', project / '.specify')
    (project / '.specify/feature.json').unlink(missing_ok=True)
    (project / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/claim-feature.py', project / 'scripts/claim-feature.py')
    subprocess.run(['git', 'add', '.'], cwd=project, check=True)
    subprocess.run(['git', 'commit', '-qm', 'tooling fixture'], cwd=project, check=True)
    subprocess.run(['git', 'branch', 'codex/6788-existing'], cwd=project, check=True)
    subprocess.run(['git', 'config', 'remote.origin.url', 'https://github.com/example/project.git'], cwd=project, check=True)
    bin_dir = tmp_path / 'bin'
    bin_dir.mkdir()
    real_git = shutil.which('git')
    (bin_dir / 'git').write_text('#!/usr/bin/env python3\nimport os,sys\n'
                                'if sys.argv[1] in ("ls-remote", "fetch"): sys.exit(0)\n'
                                f'os.execv({real_git!r}, [{real_git!r}, *sys.argv[1:]])\n')
    (bin_dir / 'gh').write_text('''#!/usr/bin/env python3
import json,sys
args=sys.argv[1:]
if args[:2]==['api','-X']: print(json.dumps({'items':[], 'total_count':0}))
elif args[:2]==['label','create']: pass
elif args[:2]==['issue','create']: print('https://github.com/example/project/issues/777')
elif args[:2]==['issue','view']: print(json.dumps({'number':777,'state':'OPEN','title':'[259] Test','body':'','labels':[{'name':'feature:259'}]}))
else: raise SystemExit('unexpected gh command: '+str(args))
''')
    for p in bin_dir.iterdir():
        p.chmod(0o755)
    monkeypatch.setenv('PATH', str(bin_dir) + os.pathsep + os.environ['PATH'])
    for key in ('GRAF_SKIP_FEATURE_CLAIM', 'GRAF_UMBRELLA_ISSUE', 'GIT_BRANCH_NAME', 'SPECIFY_INIT_DIR', 'SPECIFY_FEATURE'):
        monkeypatch.delenv(key, raising=False)
    base = '.specify/extensions/git/scripts/'
    if shell == 'bash':
        args = ['bash', base+'bash/create-new-feature-branch.sh', '--json', '--short-name', 'next']
    elif shell == 'python':
        args = ['python3', base+'python/create_new_feature_branch.py', '--json', '--short-name', 'next']
    else:
        args = ['pwsh', '-NoProfile', '-File', base+'powershell/create-new-feature-branch.ps1', '-Json', '-ShortName', 'next']
    if dry_run:
        args += ['-DryRun' if shell == 'powershell' else '--dry-run']
    args += ['Next feature']
    result = subprocess.run(args, cwd=project, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['FEATURE_NUM'] == '259'
    pointer = project / '.specify/feature.json'
    assert pointer.exists() is not dry_run
    if not dry_run:
        assert json.loads(pointer.read_text())['feature_id'] == '259'
        assert subprocess.check_output(['git', 'branch', '--show-current'], cwd=project, text=True).strip() == '259-next'


def test_remote_heads_are_checked_without_fetch(tmp_path, monkeypatch):
    module = allocator()
    calls = []

    def run(args, **kwargs):
        calls.append(args)
        if args[1] == 'remote':
            return subprocess.CompletedProcess(args, 0, stdout='upstream\n')
        if args[1] == 'ls-remote':
            return subprocess.CompletedProcess(args, 0, stdout='a'*40+'\trefs/heads/codex/260-remote-only\n')
        return subprocess.CompletedProcess(args, 0, stdout='')

    monkeypatch.setattr(module.subprocess, 'run', run)
    assert module._ids_from_refs(module._git_refs(tmp_path, strict=True)) == {260}
    assert not any('fetch' in command for command in calls)
    calls.clear()
    module._git_refs(tmp_path, strict=False)
    assert len(calls) == 1  # offline inventory never contacts remotes


def test_suggestion_preserves_and_validates_existing_umbrella(tmp_path, monkeypatch, capsys):
    module = allocator()
    (tmp_path / 'specs/258-current').mkdir(parents=True)
    monkeypatch.setenv('GRAF_UMBRELLA_ISSUE', '42')
    monkeypatch.setattr(module, '_git_refs', lambda *_a, **_k: [])
    monkeypatch.setattr(module, '_local_claim_ids', lambda *_a: set())
    validated = []
    def github(_root, **kwargs):
        assert kwargs['exclude_issue'] == 42
        return set()
    monkeypatch.setattr(module, '_github_ids', github)
    monkeypatch.setattr(module, '_github_umbrella', lambda root, issue, feature: validated.append((issue, feature)))
    assert module.main(['--root', str(tmp_path), '--json']) == 0
    assert json.loads(capsys.readouterr().out)['next_available'] == '259'
    assert validated == [(42, 259)]
    def invalid(*_args):
        raise SystemExit('wrong umbrella')
    monkeypatch.setattr(module, '_github_umbrella', invalid)
    with pytest.raises(SystemExit, match='wrong umbrella'):
        module.main(['--root', str(tmp_path), '--json'])


def test_windows_lock_releases_on_error_and_import_does_not_need_fcntl(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, 'fcntl', None)
    module = allocator()
    calls = []
    native = SimpleNamespace(LK_LOCK=1, LK_UNLCK=2, locking=lambda fd, mode, count: calls.append((mode, count)))
    monkeypatch.setitem(sys.modules, 'msvcrt', native)
    monkeypatch.setattr(module, 'os', SimpleNamespace(name='nt'))
    path = tmp_path / 'claim.lock'
    with pytest.raises(ValueError):
        with module._claim_lock(path):
            raise ValueError('synthetic failure')
    assert calls == [(1, 1), (2, 1)]
