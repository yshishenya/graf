#!/usr/bin/env python3
"""Read-only, synthetic probe of the selected checkout's Dev identity resolver."""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from unittest.mock import patch


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    args = parser.parse_args()
    checkout = args.checkout.resolve()
    path = checkout / 'scripts/dev-harness.py'
    spec = importlib.util.spec_from_file_location('f259_identity_probe', path)
    harness = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(harness)
    sha = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=checkout, text=True).strip()
    with tempfile.TemporaryDirectory(prefix='graf-identity-probe-') as temporary:
        root = Path(temporary)
        common_dirs = [root / side / 'project' / '.git' for side in ('one', 'two')]
        identities = []
        for common_dir in common_dirs:
            common_dir.mkdir(parents=True)
            with patch.object(harness.subprocess, 'check_output', return_value=str(common_dir)):
                identities.append(harness._repo_identity())
        with patch.object(harness.subprocess, 'check_output', side_effect=subprocess.CalledProcessError(1, ['git'])):
            try:
                harness._repo_identity()
                git_failure_rejected = False
            except harness.HarnessError:
                git_failure_rejected = True
        # Relative Git output must resolve against the command's cwd. We patch
        # _repo_root, but intentionally retain this probe's unrelated cwd.
        with patch.object(harness, '_repo_root', return_value=common_dirs[0].parent):
            with patch.object(harness.subprocess, 'check_output', return_value='.git'):
                relative_identity = harness._repo_identity()
            with patch.object(harness.subprocess, 'check_output', return_value=str(common_dirs[0])):
                absolute_identity = harness._repo_identity()
    result = {
        'source_sha': sha,
        'scope': 'synthetic identity resolution only; no live state read or mutation',
        'different_repositories_isolated': identities[0] != identities[1],
        'git_failure_rejected': git_failure_rejected,
        'relative_common_dir_resolved_against_repo_root': relative_identity == absolute_identity,
    }
    print(json.dumps(result, indent=2))
    return 0 if all(result[key] for key in (
        'different_repositories_isolated', 'git_failure_rejected',
        'relative_common_dir_resolved_against_repo_root',
    )) else 1


if __name__ == '__main__':
    raise SystemExit(main())
