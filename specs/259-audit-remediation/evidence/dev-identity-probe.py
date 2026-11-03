#!/usr/bin/env python3
"""Read-only identity probe using temporary real Git repositories, without live state."""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    spec = importlib.util.spec_from_file_location('f259_identity_probe', checkout / 'scripts/dev-harness.py')
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    def git(root, *arguments):
        return subprocess.check_output(['git', '-C', str(root), *arguments], text=True, stderr=subprocess.DEVNULL).strip()
    with tempfile.TemporaryDirectory(prefix='graf-identity-probe-') as temporary:
        root = Path(temporary).resolve()
        repos = [root / side / 'project' for side in ('one', 'two')]
        identities = []
        for repo, origin in zip(repos, ('git@github.com:example/one.git', 'https://github.com/example/two')):
            repo.mkdir(parents=True)
            git(repo, 'init', '-q')
            git(repo, 'config', 'remote.origin.url', origin)
            with patch.object(harness, '_repo_root', return_value=repo):
                identities.append(harness._repo_identity())
        with patch.object(harness, '_repo_root', return_value=root / 'not-a-repository'):
            try:
                harness._repo_identity()
                git_failure_rejected = False
            except harness.HarnessError:
                git_failure_rejected = True
        before_cwd = Path.cwd()
        try:
            with patch.object(harness, '_repo_root', return_value=repos[0]):
                os.chdir(repos[0])
                in_repository = harness._repo_identity()
                os.chdir(root)
                from_other_cwd = harness._repo_identity()
        finally:
            os.chdir(before_cwd)
        git(repos[1], 'config', 'remote.origin.url', 'https://github.com/EXAMPLE/one.git/')
        with patch.object(harness, '_repo_root', return_value=repos[1]):
            same_repository_alias = harness._repo_identity() == in_repository
    result = {
        'source_sha': sha,
        'scope': 'temporary real Git identity only; no live state read or mutation',
        'different_repositories_isolated': identities[0] != identities[1],
        'git_failure_rejected': git_failure_rejected,
        # Retained receipt key: the resolver now avoids git-common-dir entirely.
        'relative_common_dir_resolved_against_repo_root': in_repository == from_other_cwd,
        'same_repository_alias': same_repository_alias,
    }
    print(json.dumps(result, indent=2))
    return 0 if all(result[key] for key in (
        'different_repositories_isolated', 'git_failure_rejected',
        'relative_common_dir_resolved_against_repo_root', 'same_repository_alias',
    )) else 1


if __name__ == '__main__':
    raise SystemExit(main())
