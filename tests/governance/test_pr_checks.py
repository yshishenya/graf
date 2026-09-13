from __future__ import annotations

import copy
import importlib.util
import io
import json
from pathlib import Path
import re
import sys
import zipfile

import pytest

from test_pr_metadata_event import git, snapshot as snapshot, trusted_pr

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('pr_checks', ROOT / 'scripts/validate-pr-checks.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


@pytest.fixture
def bundle(snapshot, monkeypatch):
    root, _, pr = snapshot
    monkeypatch.chdir(root)
    pr = trusted_pr(pr)
    pr['merged_at'] = None
    git(root, 'update-ref', 'refs/remotes/origin/master', pr['base']['sha'])
    head, base = pr['head']['sha'], pr['base']['sha']
    policy = dict(schema_version=1, repository='owner/repo', foundation_pr=1,
                  foundation_sha=base, activated_at='2026-09-01T00:00:00Z')
    pr['base']['repo']['full_name'] = 'owner/repo'
    pr['head']['repo']['full_name'] = 'owner/repo'
    pr['head']['ref'] = 'feature'
    code = dict(schema_version=1, status='passed', event_name='pull_request', workflow='governance-fast',
                run_id='11', run_attempt=1, workflow_url='https://github.com/owner/repo/actions/runs/11',
                target_sha=head, base_sha=base, pull_request_numbers=[7], merge_group_id=None,
                requested_sha=head, observed_sha_start=head, observed_sha_end=head,
                final_cleanliness='pass', local_evidence_digest='sha256:' + 'a' * 64,
                started_at='2026-09-13T00:00:00Z', finished_at='2026-09-13T00:01:00Z')
    native = dict(repository='owner/repo', event_name='pull_request', pull_request_numbers=[7],
                  target_sha=head, base_sha=base, text_only=False, native_required=True,
                  paths_digest='b'*64, run_id=12, run_attempt=1)
    metadata = dict(checks.metadata.metadata_snapshot(pr, 'owner/repo'), schema_version=1,
                    base_sha=base, policy_sha=base, run_id=13, run_attempt=1, result='pass')
    bundles = {}
    for name, proof in [('governance-fast', code), ('macos-pr', native), ('pr-metadata', metadata)]:
        run = dict(id=int(proof['run_id']), run_attempt=1, name=name, run_started_at='2026-09-13T00:00:00Z',
                   path=f'.github/workflows/{name}.yml', status='completed', conclusion='success',
                   head_sha=head,
                   repository=dict(full_name='owner/repo'), pull_requests=[dict(number=7)],
                   event='pull_request_target' if name == 'pr-metadata' else 'pull_request')
        run['jobs'] = [dict(name=name, conclusion='success')]
        if name == 'macos-pr':
            run['jobs'] = [dict(name=n, conclusion='success') for n in
                           ('macos-pr', 'Determine native scope', 'Swift build and tests')]
        bundles[name] = run, proof
    return pr, policy, base, bundles


def validate(bundle):
    pr, policy, base, bundles = bundle
    return checks.validate_bundle(pr, 'owner/repo', policy, base, bundles)


def test_current_complete_set_and_historical_boundary(bundle):
    assert validate(bundle)['policy'] == 'separate'
    pr, policy, base, bundles = bundle
    pr.update(merged=True, state='closed', merged_at=policy['activated_at'], merge_commit_sha=pr['head']['sha'])
    assert validate(bundle)['policy'] == 'separate'
    pr['merged_at'] = '2026-08-31T23:59:59Z'
    assert checks.historical(pr, policy)
    old = {key: value for key, value in bundles.items() if key == 'governance-fast'}
    assert checks.validate_bundle(pr, 'owner/repo', policy, base, old)['policy'] == 'combined'
    pr.update(merged=False, state='open', merge_commit_sha=None)
    with pytest.raises(ValueError, match='incomplete'):
        checks.validate_bundle(pr, 'owner/repo', policy, base, old)
    with pytest.raises(ValueError, match='boundary'):
        checks.historical(pr, {})


@pytest.mark.parametrize('workflow', ['governance-fast', 'macos-pr', 'pr-metadata'])
@pytest.mark.parametrize('mutation', ['head', 'base', 'attempt', 'run', 'failure', 'path', 'event', 'missing'])
def test_mixed_stale_or_unsuccessful_proof_fails(bundle, workflow, mutation):
    run, proof = bundle[3][workflow]
    if mutation in {'head', 'base'}:
        proof['target_sha' if mutation == 'head' else 'base_sha'] = 'f'*40
    elif mutation == 'attempt':
        proof['run_attempt'] = 2
    elif mutation == 'run':
        proof['run_id'] = 99
    elif mutation == 'failure':
        run['conclusion'] = 'cancelled'
    elif mutation == 'path':
        run['path'] = '.github/workflows/other.yml'
    elif mutation == 'event':
        run['event'] = 'workflow_dispatch'
    else:
        del bundle[3][workflow]
    with pytest.raises((ValueError, checks.subprocess.CalledProcessError)):
        validate(bundle)


@pytest.mark.parametrize('change', ['body', 'native-skipped', 'text-only', 'policy-sha'])
def test_fresh_text_cannot_replace_code_or_required_native(bundle, change):
    pr, _, _, bundles = bundle
    if change == 'body':
        pr['body'] += '\nChanged description\n'
    elif change == 'native-skipped':
        bundles['macos-pr'][0]['jobs'][-1]['conclusion'] = 'skipped'
    elif change == 'text-only':
        bundles['macos-pr'][1]['text_only'] = True
    else:
        bundles['pr-metadata'][1]['policy_sha'] = 'f'*40
    with pytest.raises((ValueError, checks.subprocess.CalledProcessError)):
        validate(bundle)


def test_latest_text_event_does_not_hide_failed_code(github):
    github['runs']['governance-fast'][0]['conclusion'] = 'failure'
    github['text']('governance-fast', status='completed')
    with pytest.raises(ValueError, match='latest code run'):
        checks.current_run('owner/repo', 'governance-fast', github['pr'], github['base'])


def test_expired_or_missing_artifact_is_not_reused(bundle, monkeypatch):
    run = bundle[3]['macos-pr'][0]
    for artifacts in [[], [dict(name='graf-native-scope-12-1', expired=True)]]:
        monkeypatch.setattr(checks, 'api', lambda *_a, **_k: artifacts)
        with pytest.raises(ValueError, match='missing/expired'):
            checks.artifact('owner/repo', run, 'macos-pr')


@pytest.mark.parametrize('case', ['retry', 'legacy', 'mixed', 'expired', 'duplicate',
                                 'legacy-mixed', 'legacy-expired', 'legacy-duplicate'])
def test_governance_artifact_selects_exact_attempt_without_losing_legacy_proof(bundle, monkeypatch, case):
    pr, _, base, bundles = bundle
    run, proof = bundles['governance-fast']
    run['run_attempt'] = 2
    proof['run_attempt'] = 1 if 'mixed' in case else 2
    name = 'graf-governance-fast-evidence'
    if not case.startswith('legacy'):
        import yaml
        workflow = yaml.safe_load((ROOT / '.github/workflows/governance-fast.yml').read_text())
        upload = next(step for step in workflow['jobs']['governance-fast']['steps']
                      if step.get('name') == 'Upload metadata-only evidence')
        name = upload['with']['name'].replace('${{ github.run_id }}', '11').replace('${{ github.run_attempt }}', '2')
        assert name == 'graf-governance-fast-evidence-11-2'
    row = dict(id=22, name=name, expired='expired' in case,
               expires_at='2099-01-01T00:00:00Z', workflow_run=dict(id=11))
    rows = [dict(row, id=21, name='graf-governance-fast-evidence-11-1'), row]
    if not case.startswith('legacy'):
        rows.append(dict(row, id=20, name='graf-governance-fast-evidence', expired=False))
    if 'duplicate' in case:
        rows.append(dict(row, id=23))
    monkeypatch.setattr(checks, 'api', lambda *_a, **_k: rows)
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, 'w') as output:
        output.writestr('receipt-11.json', json.dumps(proof))
    def download(args, **_kwargs):
        assert args[-1] == 'repos/owner/repo/actions/artifacts/22/zip'
        return archive.getvalue()
    monkeypatch.setattr(checks.subprocess, 'check_output', download)
    if case in {'retry', 'legacy'}:
        result = checks.artifact('owner/repo', run, 'governance-fast')
        checks.validate_source(pr, 'owner/repo', base, 'governance-fast', run, result)
        assert result['run_attempt'] == 2
    else:
        with pytest.raises(ValueError):
            result = checks.artifact('owner/repo', run, 'governance-fast')
            checks.validate_source(pr, 'owner/repo', base, 'governance-fast', run, result)


@pytest.mark.parametrize("workflow", ["governance-fast", "macos-pr", "pr-metadata"])
@pytest.mark.parametrize("status", ["failure", "in_progress", "missing-time"])
def test_later_attempt_of_older_run_cannot_hide_behind_newer_id(bundle, monkeypatch, workflow, status):
    pr, _, base, bundles = bundle
    good, proof = bundles[workflow]
    good.update(id=20, run_started_at="2026-09-13T01:00:00Z")
    retry = copy.deepcopy(good)
    retry.update(id=11, run_attempt=2, run_started_at="2026-09-13T01:02:00Z",
                 conclusion="failure" if status == "failure" else None,
                 status="completed" if status == "failure" else "in_progress")
    if status == "missing-time":
        retry.pop("run_started_at")
    def api(_repo, endpoint, **_kwargs):
        return [] if "/jobs?" in endpoint else [good, retry]
    monkeypatch.setattr(checks, "api", api)
    monkeypatch.setattr(checks, "artifact", lambda *_args, **_kwargs: None if _kwargs.get('optional') else proof)
    with pytest.raises((ValueError, KeyError)):
        checks.current_run("owner/repo", workflow, pr, base)


@pytest.mark.parametrize("case", ["two-prs", "rebase", "published-source", "unowned", "mixed-prs", "bad-policy", "no-base"])
def test_release_source_checks_actual_range(snapshot, monkeypatch, case):
    root, _, pr = snapshot
    monkeypatch.chdir(root)
    monkeypatch.setattr(checks, "ROOT", root)
    base, first = pr["base"]["sha"], pr["head"]["sha"]
    (root / "second").write_text("release change\n")
    git(root, "add", "second")
    git(root, "commit", "-qm", "second")
    source = git(root, "rev-parse", "HEAD")
    policy = dict(schema_version=1, repository="owner/repo", foundation_pr=1,
                  foundation_sha=base, activated_at="2026-09-01T00:00:00Z")
    if case == "bad-policy":
        policy.pop("foundation_sha")
    (root / ".github").mkdir()
    (root / ".github/pr-check-policy.json").write_text(json.dumps(policy))
    visited = []
    def api(_repo, endpoint, **_kwargs):
        if endpoint.startswith("releases?"):
            releases = [dict(tag_name="v2026.08.31.1", published_at="2026-08-31T00:00:00Z")]
            if case == "no-base":
                return []
            if case == "published-source":
                releases.append(dict(tag_name="v2026.09.13.1", published_at="2026-09-13T00:00:00Z"))
            return releases
        if endpoint.startswith("git/ref/tags/"):
            # Exercise real annotated tag resolution for the previous release.
            return dict(object=dict(type="commit", sha=source)) if endpoint.endswith("v2026.09.13.1") else dict(object=dict(type="tag", sha="a"*40))
        if endpoint == "git/tags/" + "a"*40:
            return dict(object=dict(type="commit", sha=base))
        commit = endpoint.split("/")[1]
        if case == "unowned" and commit == first:
            return []
        return [dict(number=8 if commit == source else 7, merge_commit_sha=commit,
                     merged_at="2026-09-13T00:00:00Z", base=dict(ref="master"))]
    def verify(_repo, number):
        visited.append(number)
        return dict(pr_number=number, merge_commit_sha=source if number == 8 else first,
                    base_sha=base if number == 7 or case == "rebase" else first)
    monkeypatch.setattr(checks, "api", api)
    monkeypatch.setattr(checks, "verify", verify)
    expected = [8] if case in {"rebase", "mixed-prs"} else [7, 8]
    if case in {"unowned", "mixed-prs", "bad-policy", "no-base"}:
        with pytest.raises(ValueError):
            checks.verify_source("owner/repo", source, included_prs=expected)
    else:
        results = checks.verify_source("owner/repo", source, included_prs=expected)
        assert sorted(row["pr_number"] for row in results) == expected
        assert visited == list(reversed(expected))


@pytest.mark.parametrize('valid_scope', [True, False])
def test_github_unevaluated_skipped_name_requires_actual_text_scope(github, valid_scope):
    text, scope = github['text']('governance-fast', status='completed')
    scope['text_only'] = valid_scope
    text['jobs'][1] = dict(name="needs.scope.outputs.text_only == 'true' && 'governance-fast-text-change' || 'governance-fast'", conclusion='skipped')
    if valid_scope:
        assert checks.current_run('owner/repo', 'governance-fast', github['pr'], github['base'])[0]['id'] == 11
    else:
        with pytest.raises(ValueError):
            checks.current_run('owner/repo', 'governance-fast', github['pr'], github['base'])


@pytest.fixture
def github(bundle, monkeypatch):
    """Provider facts, independent from the component/gate selection implementation."""
    pr, policy, base, bundles = bundle
    runs = {name: [copy.deepcopy(pair[0])] for name, pair in bundles.items()}
    artifacts = {(pair[0]['id'], name): copy.deepcopy(pair[1]) for name, pair in bundles.items()}
    exact_scope = load_scope_for_test().resolve(dict(number=7, action='edited', changes={'body': {'from':'old'}}, pull_request=pr), 'pull_request')
    artifacts[(12, 'macos-pr')].update(paths_digest=exact_scope['paths_digest'], native_required=exact_scope['native_required'])
    runs['macos-pr'][0]['jobs'][-1]['conclusion'] = 'success' if exact_scope['native_required'] else 'skipped'
    root = Path.cwd()
    (root / '.github').mkdir(exist_ok=True)
    (root / '.github/pr-check-policy.json').write_text(json.dumps(policy))
    monkeypatch.setattr(checks, 'ROOT', root)
    original_module = checks.module
    monkeypatch.setattr(checks, 'module', lambda name: load_scope_for_test() if name == 'ci-pr-scope' else original_module(name))
    state = dict(pr=pr, policy=policy, base=base, runs=runs, artifacts=artifacts, sleeps=0, elapsed=0, after_artifact=None)

    def find(run_id):
        return next(run for rows in runs.values() for run in rows if run['id'] == int(run_id))

    def api(_repo, endpoint, **_kwargs):
        assert _repo == 'owner/repo'
        if endpoint == 'pulls/7':
            return copy.deepcopy(pr)
        if endpoint == 'pulls/1':
            return dict(merged=True, merge_commit_sha=policy['foundation_sha'], merged_at='2026-08-31T00:00:00Z')
        match = re.match(r'actions/workflows/([^/]+)\.yml/runs\?', endpoint)
        if match:
            return copy.deepcopy(runs[match[1]])
        match = re.fullmatch(r'actions/runs/(\d+)/attempts/(\d+)/jobs\?per_page=100', endpoint)
        if match:
            run = find(match[1])
            assert run['run_attempt'] == int(match[2])
            return copy.deepcopy(run['jobs'])
        match = re.fullmatch(r'actions/runs/(\d+)', endpoint)
        if match:
            return copy.deepcopy(find(match[1]))
        raise AssertionError(endpoint)

    def artifact(_repo, run, kind, *, optional=False):
        proof = copy.deepcopy(artifacts.get((run['id'], kind)))
        if state['after_artifact']:
            state['after_artifact'](run, kind)
        if proof is None and not optional:
            raise ValueError('missing proof')
        return proof

    def text(workflow, run_id=25, status='in_progress'):
        source = runs[workflow][0]
        run = copy.deepcopy(source)
        run.update(id=run_id, run_started_at=f'2026-09-13T01:{run_id % 60:02}:00Z',
                   status=status, conclusion='success' if status == 'completed' else None)
        run['jobs'] = [dict(name='Determine code scope' if workflow == 'governance-fast' else 'Determine native scope', conclusion='success'),
                       dict(name=workflow, conclusion='success' if status == 'completed' else None)]
        if workflow == 'macos-pr':
            run['jobs'].append(dict(name='Swift build and tests', conclusion='skipped'))
        proof = dict(artifacts[(12, 'macos-pr')], run_id=run_id, text_only=True)
        artifacts[(run_id, 'code-scope' if workflow == 'governance-fast' else 'macos-pr')] = proof
        runs[workflow].append(run)
        return run, proof

    def sleep(_seconds):
        state['sleeps'] += 1
        state['elapsed'] += _seconds
        if state.get('on_sleep'):
            state['on_sleep']()

    monkeypatch.setattr(checks, 'api', api)
    monkeypatch.setattr(checks, 'artifact', artifact)
    state.update(text=text, sleep=sleep)
    return state


def load_scope_for_test():
    spec = importlib.util.spec_from_file_location('real_pr_scope', ROOT / 'scripts/ci-pr-scope.py')
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def reuse(github, monkeypatch, workflow='governance-fast', run_id=25, wait_seconds=0):
    event = dict(number=7, action='edited', changes={'body': {'from': 'previous description'}},
                 pull_request=copy.deepcopy(github['pr']))
    monkeypatch.setattr(checks.time, 'monotonic', lambda: github['elapsed'])
    monkeypatch.setattr(checks.time, 'sleep', github['sleep'])
    return checks.reuse('owner/repo', event, workflow, run_id, 1, wait_seconds=wait_seconds)


@pytest.mark.parametrize('workflow', ['governance-fast', 'macos-pr'])
def test_fixed_name_text_gates_reuse_actual_source_without_waiting_each_other(github, monkeypatch, workflow):
    source_id = github['runs'][workflow][0]['id']
    github['text'](workflow, 25)
    github['text'](workflow, 26)
    result = reuse(github, monkeypatch, workflow)
    assert result['run_id'] == str(source_id)
    assert github['sleeps'] == 0
    assert checks.current_run('owner/repo', workflow, github['pr'], github['base'])[0]['id'] == source_id


@pytest.mark.parametrize('workflow', ['governance-fast', 'macos-pr'])
def test_text_component_cli_reports_actual_source_identity(github, monkeypatch, tmp_path, capsys, workflow):
    source_id = str(github['runs'][workflow][0]['id'])
    github['text'](workflow)
    event = tmp_path / 'event.json'
    event.write_text(json.dumps(dict(number=7, action='edited', changes={'body': {'from': 'private draft text'}},
                                    pull_request=github['pr'])))
    summary = tmp_path / 'summary.md'
    monkeypatch.setenv('GITHUB_STEP_SUMMARY', str(summary))
    monkeypatch.setattr(sys, 'argv', ['validate-pr-checks.py', '--repository', 'owner/repo',
                                    '--reuse-component', workflow, '--event', str(event),
                                    '--run-id', '25', '--run-attempt', '1'])
    assert checks.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result['run_id'] == source_id and result['run_attempt'] == 1
    assert result['target_sha'] == github['pr']['head']['sha'] and result['base_sha'] == github['base']
    assert f'https://github.com/owner/repo/actions/runs/{source_id}' in summary.read_text()
    assert 'Product tests were not repeated' in summary.read_text()
    assert 'private draft text' not in summary.read_text()


@pytest.mark.parametrize('workflow', ['governance-fast', 'macos-pr'])
@pytest.mark.parametrize('outcome', ['failure', 'cancelled', 'timed_out', 'in_progress', 'queued'])
def test_reuse_cannot_hide_latest_unsuccessful_source(github, monkeypatch, workflow, outcome):
    source = github['runs'][workflow][0]
    older = copy.deepcopy(source)
    older.update(id=9, run_started_at='2026-09-12T00:00:00Z')
    github['runs'][workflow].append(older)
    source.update(status=outcome if outcome in {'in_progress', 'queued'} else 'completed',
                  conclusion=None if outcome in {'in_progress', 'queued'} else outcome)
    github['text'](workflow)
    with pytest.raises(ValueError):
        reuse(github, monkeypatch, workflow)


@pytest.mark.parametrize('outcome', ['success', 'failure', 'timeout'])
def test_existing_running_source_is_waited_without_a_new_execution(github, monkeypatch, outcome):
    source = github['runs']['governance-fast'][0]
    source.update(status='in_progress', conclusion=None)
    github['text']('governance-fast')
    def finish():
        if outcome != 'timeout':
            source.update(status='completed', conclusion=outcome)
    github['on_sleep'] = finish
    if outcome == 'success':
        assert reuse(github, monkeypatch, wait_seconds=2)['run_id'] == '11'
    else:
        with pytest.raises(ValueError):
            reuse(github, monkeypatch, wait_seconds=2)
    assert github['sleeps'] >= 1
    assert len(github['runs']['governance-fast']) == 2


@pytest.mark.parametrize('mutation', ['self-id', 'not-text', 'head', 'base', 'repository', 'attempt', 'missing', 'api'])
def test_reuse_requires_current_text_scope_and_identity(github, monkeypatch, mutation):
    run, proof = github['text']('governance-fast')
    run_id = run['id']
    if mutation == 'self-id':
        run_id = 11
    elif mutation == 'not-text':
        proof['text_only'] = False
    elif mutation in {'head', 'base'}:
        proof['target_sha' if mutation == 'head' else 'base_sha'] = 'f' * 40
    elif mutation == 'repository':
        run['repository']['full_name'] = 'other/repo'
    elif mutation == 'attempt':
        proof['run_attempt'] = 2
    elif mutation == 'missing':
        del github['artifacts'][(25, 'code-scope')]
    else:
        monkeypatch.setattr(checks, 'api', lambda *_a, **_k: (_ for _ in ()).throw(ValueError('API failed')))
    with pytest.raises(ValueError):
        reuse(github, monkeypatch, run_id=run_id)


@pytest.mark.parametrize('mutation', ['base', 'head', 'head-ref', 'base-ref', 'state', 'source-attempt'])
def test_reuse_rechecks_identity_and_source_after_loading_proof(github, monkeypatch, mutation):
    github['text']('governance-fast')
    def change(run, kind):
        if kind != 'governance-fast':
            return
        github['after_artifact'] = None
        if mutation in {'base', 'head'}:
            github['pr'][mutation]['sha'] = 'f' * 40
        elif mutation in {'base-ref', 'head-ref'}:
            github['pr'][mutation.split('-')[0]]['ref'] = 'another-branch'
        elif mutation == 'state':
            github['pr']['state'] = 'closed'
        else:
            source = github['runs']['governance-fast'][0]
            source.update(run_attempt=2, status='in_progress', conclusion=None,
                          run_started_at='2026-09-13T02:00:00Z')
    github['after_artifact'] = change
    with pytest.raises(ValueError):
        reuse(github, monkeypatch)


@pytest.mark.parametrize('outcome', ['missing', 'duplicate', 'failure', 'in_progress', 'success'])
def test_full_consumer_requires_latest_fixed_gate_not_only_source_proof(github, outcome):
    run, _ = github['text']('macos-pr', status='completed')
    if outcome == 'missing':
        run['jobs'][1]['name'] = 'macos-pr-text-change'
    elif outcome == 'duplicate':
        run['jobs'].append(copy.deepcopy(run['jobs'][1]))
    elif outcome == 'failure':
        run.update(conclusion='failure')
        run['jobs'][1]['conclusion'] = 'failure'
    elif outcome == 'in_progress':
        run.update(status='in_progress', conclusion=None)
        run['jobs'][1]['conclusion'] = None
    if outcome == 'success':
        assert checks.verify('owner/repo', 7)['checks']['macos-pr']['run_id'] == '12'
    else:
        with pytest.raises(ValueError):
            checks.verify('owner/repo', 7)


@pytest.mark.parametrize('changed', ['source', 'gate', 'metadata'])
def test_full_consumer_detects_same_sha_retry_while_checking_another_component(github, changed):
    text, _ = github['text']('macos-pr', status='completed')
    metadata_reads = 0
    def retry(_run, kind):
        nonlocal metadata_reads
        if kind != 'pr-metadata':
            return
        metadata_reads += 1
        if metadata_reads != 2:
            return
        github['after_artifact'] = None
        run = text if changed == 'gate' else github['runs']['governance-fast' if changed == 'source' else 'pr-metadata'][0]
        run.update(run_attempt=2, run_started_at='2026-09-13T02:00:00Z', status='in_progress', conclusion=None)
    github['after_artifact'] = retry
    with pytest.raises(ValueError):
        checks.verify('owner/repo', 7)
    assert metadata_reads == 2


def test_full_consumer_detects_changed_head_ref_after_proof_validation(github):
    def change(_run, kind):
        if kind == 'pr-metadata':
            github['pr']['head']['ref'] = 'another-branch'
            github['after_artifact'] = None
    github['after_artifact'] = change
    with pytest.raises(ValueError, match='PR changed'):
        checks.verify('owner/repo', 7)


@pytest.mark.parametrize('workflow', ['governance-fast', 'macos-pr'])
@pytest.mark.parametrize('case', ['merged', 'rebase', 'moving-base', 'wrong-tree', 'closed-unmerged', 'merge-changed', 'stale-metadata'])
def test_merged_text_reuses_checked_history_and_preserves_release_validation(github, monkeypatch, workflow, case):
    pr, root = github['pr'], Path.cwd()
    if case == 'rebase':
        old = pr['head']['sha']
        head = git(root, 'commit-tree', old + '^{tree}', '-p', old, '-m', 'second source')
        git(root, 'checkout', '--detach', head)
        pr['head']['sha'], pr['commits'] = head, 2
        pr['body'] = pr['body'].replace(old, head)
        for rows in github['runs'].values():
            rows[0]['head_sha'] = head
        for proof in github['artifacts'].values():
            for key in ('target_sha', 'requested_sha', 'observed_sha_start', 'observed_sha_end'):
                if key in proof:
                    proof[key] = head
    tree = (github['base'] if case == 'wrong-tree' else pr['head']['sha']) + '^{tree}'
    merge = git(root, 'commit-tree', tree, '-p', github['base'], '-m', 'squash')
    if case == 'rebase':
        merge = git(root, 'commit-tree', tree, '-p', merge, '-m', 'rebased second')
    pr.update(merged=True, state='closed', merged_at='2026-09-13T01:00:00Z', merge_commit_sha=merge)
    pr['base']['sha'] = git(root, 'commit-tree', tree, '-p', merge, '-m', 'later master')
    git(root, 'update-ref', 'refs/remotes/origin/master', pr['base']['sha'])
    if case == 'closed-unmerged':
        pr.update(merged=False, merge_commit_sha=None)
    github['text'](workflow, status='completed')
    if case == 'merge-changed':
        def change(run, kind):
            if run['id'] in {11, 12} and kind == workflow:
                # Different merge identity with the same checked base and final tree.
                pr['merge_commit_sha'] = git(root, 'commit-tree', tree, '-p', github['base'], '-m', 'another squash')
                github['after_artifact'] = None
        github['after_artifact'] = change
    if case in {'wrong-tree', 'closed-unmerged', 'merge-changed'}:
        with pytest.raises(ValueError):
            reuse(github, monkeypatch, workflow)
        return
    if case == 'moving-base':
        event = dict(number=7, action='edited', changes={'body': {'from': 'before'}}, pull_request=copy.deepcopy(pr))
        pr['base']['sha'] = git(root, 'commit-tree', tree, '-p', pr['base']['sha'], '-m', 'master advanced again')
        result = checks.reuse('owner/repo', event, workflow, 25, 1)
    else:
        result = reuse(github, monkeypatch, workflow)
    assert result['base_sha'] == github['base'] != pr['base']['sha']
    assert result['run_id'] == ('11' if workflow == 'governance-fast' else '12')
    pr['body'] += '\nUpdated release evidence\n'
    if case == 'stale-metadata':
        with pytest.raises(ValueError, match='metadata'):
            checks.verify('owner/repo', 7)
    else:
        github['artifacts'][(13, 'pr-metadata')].update(checks.metadata.metadata_snapshot(pr, 'owner/repo'))
        assert checks.verify('owner/repo', 7)['merge_commit_sha'] == merge


@pytest.mark.parametrize('fetch_failure', [False, True])
def test_merged_consumer_fetches_missing_history_before_checked_snapshot(github, tmp_path, fetch_failure):
    pr, root = github['pr'], Path.cwd()
    head = pr['head']['sha']
    remote = tmp_path / 'remote.git'
    git(root, 'clone', '--bare', str(root), str(remote))
    git(root, 'remote', 'add', 'origin', str(remote / 'missing' if fetch_failure else remote))
    pr.update(merged=True, state='closed', merged_at='2026-09-13T01:00:00Z', merge_commit_sha=head)
    # Only this disposable fixture loses its loose head object; the remote retains it.
    obj = root / '.git/objects' / head[:2] / head[2:]
    obj.unlink()
    if fetch_failure:
        with pytest.raises(checks.subprocess.CalledProcessError):
            checks.verify('owner/repo', 7)
        assert not obj.exists()
    else:
        assert checks.verify('owner/repo', 7)['merge_commit_sha'] == head
        assert git(root, 'rev-parse', head + '^{tree}')
