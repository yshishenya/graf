from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

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
                   event='pull_request_target' if name == 'pr-metadata' else 'pull_request')
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


def test_latest_text_event_does_not_hide_failed_code(bundle, monkeypatch):
    pr, _, base, bundles = bundle
    code, proof = bundles['governance-fast']
    older = copy.deepcopy(code)
    older['id'] = 10
    code['conclusion'] = 'failure'
    text = dict(code, id=12, conclusion='success')
    def api(_repo, endpoint, **_kwargs):
        if '/jobs?' in endpoint:
            return [dict(name='governance-fast-text-change' if '/12/' in endpoint else 'governance-fast')]
        return [text, code, older]
    monkeypatch.setattr(checks, 'api', api)
    monkeypatch.setattr(checks, 'artifact', lambda *_a: proof)
    with pytest.raises(ValueError, match='latest code run'):
        checks.current_run('owner/repo', 'governance-fast', pr, base)


def test_expired_or_missing_artifact_is_not_reused(bundle, monkeypatch):
    run = bundle[3]['macos-pr'][0]
    for artifacts in [[], [dict(name='graf-native-scope-12-1', expired=True)]]:
        monkeypatch.setattr(checks, 'api', lambda *_a, **_k: artifacts)
        with pytest.raises(ValueError, match='missing/expired'):
            checks.artifact('owner/repo', run, 'macos-pr')


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
    monkeypatch.setattr(checks, "artifact", lambda *_args: proof)
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
def test_github_unevaluated_skipped_name_requires_actual_text_scope(bundle, monkeypatch, valid_scope):
    pr, _, base, bundles = bundle
    code, proof = bundles['governance-fast']
    text = dict(code, id=25)
    scope = dict(bundles['macos-pr'][1], text_only=valid_scope, run_id=25)
    def api(_repo, endpoint, **_kwargs):
        if '/25/' in endpoint:
            return [dict(name='Determine code scope', conclusion='success'),
                    dict(name="needs.scope.outputs.text_only == 'true' && 'governance-fast-text-change' || 'governance-fast'", conclusion='skipped')]
        return [dict(name='governance-fast', conclusion='success')] if '/jobs?' in endpoint else [text, code]
    monkeypatch.setattr(checks, 'api', api)
    monkeypatch.setattr(checks, 'artifact', lambda _repo, _run, workflow: scope if workflow == 'code-scope' else proof)
    if valid_scope:
        assert checks.current_run('owner/repo', 'governance-fast', pr, base)[0]['id'] == code['id']
    else:
        with pytest.raises(ValueError, match='unverified text-only'):
            checks.current_run('owner/repo', 'governance-fast', pr, base)
