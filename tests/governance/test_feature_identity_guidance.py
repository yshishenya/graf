"""The directory-only compatibility entrypoint must not bypass allocation."""
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('flags', [[], ['--dry-run'], ['--number', '1000'], ['--number', '259'], ['--timestamp'], ['--dry-run', '--timestamp']])
@pytest.mark.parametrize('allocation_marker', ['allocator', 'policy'])
def test_legacy_entrypoint_stops_before_writes(tmp_path, flags, allocation_marker):
    scripts = tmp_path / '.specify/scripts/bash'
    scripts.mkdir(parents=True)
    for name in ('create-new-feature.sh', 'common.sh'):
        shutil.copy2(ROOT / '.specify/scripts/bash' / name, scripts / name)
    if allocation_marker == 'allocator':
        (tmp_path / 'scripts').mkdir()
        (tmp_path / 'scripts/claim-feature.py').write_text("raise AssertionError('unexpected allocator invocation')\n")
    else:
        (tmp_path / '.specify/feature-numbering.json').write_text('{"max_feature_id":999}')
    pointer = tmp_path / '.specify/feature.json'
    original = '{"feature_id":"259","owner":"existing","feature_directory":"specs/259-existing"}'
    pointer.write_text(original)
    result = subprocess.run(
        ['bash', str(scripts / 'create-new-feature.sh'), '--json', *flags, 'New feature'],
        cwd=tmp_path, text=True, capture_output=True,
        env={**os.environ, 'GRAF_SKIP_FEATURE_CLAIM': '1'},
    )
    assert result.returncode != 0
    assert 'speckit-git-feature followed by speckit-specify' in result.stderr
    assert not result.stdout
    assert pointer.read_text() == original
    assert not (tmp_path / 'specs').exists()


def test_legacy_generic_numbering_is_unchanged(tmp_path):
    scripts = tmp_path / '.specify/scripts/bash'
    scripts.mkdir(parents=True)
    for name in ('create-new-feature.sh', 'common.sh'):
        shutil.copy2(ROOT / '.specify/scripts/bash' / name, scripts / name)
    result = subprocess.run(
        ['bash', str(scripts / 'create-new-feature.sh'), '--json', '--dry-run', '--number', '1000', 'New feature'],
        cwd=tmp_path, text=True, capture_output=True,
    )
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['FEATURE_NUM'] == '1000'
    assert not (tmp_path / 'specs').exists()


def test_specify_keeps_reserved_identity_and_pointer_metadata():
    text = (ROOT / '.agents/skills/speckit-specify/SKILL.md').read_text()
    assert text.index('Repository allocator takes precedence') < text.index('next available 3-digit number')
    for requirement in (
        'do not independently scan `specs/`',
        "`feature_id` equals the hook's `FEATURE_NUM`",
        'and the current Git branch',
        'exact reserved `<FEATURE_NUM>-`',
        'reject a mismatched number',
        'Preserve every field in the existing pointer',
        'retaining unrelated owned paths and all claim metadata',
        'Write the merged object atomically',
        'directory-only object',
        'Existing historical feature updates retain their validated identity',
    ):
        assert requirement in text


@pytest.mark.parametrize('runtime', ['bash', 'python', 'powershell'])
@pytest.mark.parametrize('dry_run', [False, True])
@pytest.mark.parametrize('invalid_identity', ['number', 'timestamp', 'branch', 'padding', 'broken-policy', 'policy-directory'])
def test_branch_explicit_identity_cannot_bypass_policy(tmp_path, runtime, dry_run, invalid_identity):
    if runtime == 'powershell' and not shutil.which('pwsh'):
        pytest.skip('pwsh is not installed')
    shutil.copytree(ROOT / '.specify', tmp_path / '.specify')
    pointer = tmp_path / '.specify/feature.json'
    pointer.write_text('{"feature_id":"259","owner":"existing"}')
    policy = tmp_path / '.specify/feature-numbering.json'
    policy.write_text('{"out_of_sequence_spec_ids":[],"max_feature_id":999}')
    (tmp_path / 'scripts').mkdir()
    shutil.copy2(ROOT / 'scripts/claim-feature.py', tmp_path / 'scripts/claim-feature.py')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    env = {**os.environ, 'GRAF_SKIP_FEATURE_CLAIM': '1'}
    for key in ('GIT_BRANCH_NAME', 'SPECIFY_FEATURE', 'SPECIFY_FEATURE_DIRECTORY', 'SPECIFY_INIT_DIR'):
        env.pop(key, None)
    base = '.specify/extensions/git/scripts/'
    if runtime == 'bash':
        command = ['bash', base+'bash/create-new-feature-branch.sh', '--json']
    elif runtime == 'python':
        import sys
        command = [sys.executable, base+'python/create_new_feature_branch.py', '--json']
    else:
        command = ['pwsh', '-NoProfile', '-File', base+'powershell/create-new-feature-branch.ps1', '-Json']
    if dry_run:
        command.append('-DryRun' if runtime == 'powershell' else '--dry-run')
    if invalid_identity == 'timestamp':
        command.append('-Timestamp' if runtime == 'powershell' else '--timestamp')
    elif invalid_identity in ('branch', 'padding'):
        env['GIT_BRANCH_NAME'] = 'codex/1000-invalid' if invalid_identity == 'branch' else 'codex/0259-invalid'
    else:
        command.extend(['-Number' if runtime == 'powershell' else '--number', '1000' if invalid_identity == 'number' else '259'])
        if invalid_identity in ('broken-policy', 'policy-directory'):
            policy.unlink()
            if invalid_identity == 'broken-policy':
                policy.symlink_to('missing-policy.json')
            else:
                policy.mkdir()
    before_pointer = pointer.read_bytes()
    before_refs = subprocess.check_output(['git', 'for-each-ref'], cwd=tmp_path)
    result = subprocess.run([*command, 'New feature'], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode != 0, result.stdout
    assert pointer.read_bytes() == before_pointer
    assert subprocess.check_output(['git', 'for-each-ref'], cwd=tmp_path) == before_refs
    assert not (tmp_path / '.git/feature-claims.json').exists()
    assert not (tmp_path / 'specs').exists()


@pytest.mark.parametrize('runtime', ['bash', 'python', 'powershell'])
def test_skip_flag_cannot_skip_required_reservation(tmp_path, runtime):
    if runtime == 'powershell' and not shutil.which('pwsh'):
        pytest.skip('pwsh is not installed')
    shutil.copytree(ROOT / '.specify', tmp_path / '.specify')
    (tmp_path / '.specify/feature.json').unlink(missing_ok=True)
    (tmp_path / '.specify/feature-numbering.json').write_text('{"out_of_sequence_spec_ids":[],"max_feature_id":999}')
    (tmp_path / 'scripts').mkdir()
    (tmp_path / 'scripts/claim-feature.py').write_text('''import sys
if '--check-feature-id' in sys.argv:
    raise SystemExit(0)
if '--allocate' in sys.argv:
    raise SystemExit('required reservation reached')
raise SystemExit('unexpected operation')
''')
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    base = '.specify/extensions/git/scripts/'
    if runtime == 'bash':
        command = ['bash', base+'bash/create-new-feature-branch.sh', '--json', '--number', '259']
    elif runtime == 'python':
        import sys
        command = [sys.executable, base+'python/create_new_feature_branch.py', '--json', '--number', '259']
    else:
        command = ['pwsh', '-NoProfile', '-File', base+'powershell/create-new-feature-branch.ps1', '-Json', '-Number', '259']
    env = {**os.environ, 'GRAF_SKIP_FEATURE_CLAIM': '1'}
    for key in ('GIT_BRANCH_NAME', 'SPECIFY_FEATURE', 'SPECIFY_FEATURE_DIRECTORY', 'SPECIFY_INIT_DIR'):
        env.pop(key, None)
    result = subprocess.run([*command, 'New feature'], cwd=tmp_path, env=env, text=True, capture_output=True)
    assert result.returncode != 0
    assert 'required reservation reached' in result.stderr
    assert not subprocess.check_output(['git', 'for-each-ref'], cwd=tmp_path)
    assert not (tmp_path / '.specify/feature.json').exists()
