# Quickstart: Надёжный Spec Kit workflow

## Preconditions

- Рабочая ветка `211-spec-kit-workflow-hardening` основана на актуальном `origin/master`.
- Worktree чистый либо каждый существующий diff явно относится к Feature 211.
- `specify`, `speckit-bootstrap`, Git и Python 3 доступны.

## Scenario 1: Source and version preflight

```sh
git status --short --branch
specify version
speckit-bootstrap --version
speckit-bootstrap . --dry-run --json
```

Expected: Spec Kit resolves to stable `v1.0.1`, bootstrap is `v0.9.0`, dry-run does not mutate files.

## Scenario 2: One-time migration

```sh
speckit-bootstrap .
python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py
speckit-bootstrap . --doctor --frozen
```

Expected: lock schema 3, project-local skills and hashes, managed local-state ignore, preserved legacy user-level skills; Python command does not create `__pycache__`/`.pyc`, and frozen doctor remains green after the import.

## Scenario 3: Focused governance validation

```sh
python3 scripts/check_spec_kit_governance.py --self-test
python3 scripts/check_spec_kit_governance.py
```

Expected: self-test proves positive and four protected negative classes; repository check confirms bootstrap integrity and GRAF-specific rules.

## Scenario 4: Idempotence

```sh
git status --short
speckit-bootstrap . --dry-run --json
speckit-bootstrap .
python3 scripts/check_spec_kit_governance.py
git status --short
```

Expected: second apply creates no unexplained tracked diff and governance check remains green.

## Scenario 5: PR feedback gate

```sh
infra/scripts/ci-local.sh --fast
```

Expected: fast lane includes the focused governance check and is the final repository gate for this governance/tooling-only change. Full CI, product release preparation and deployment are not executed.

## Validation Evidence — 2026-08-30

- Source checkout `speckit-bootstrap` is clean on `main == origin/main == v0.9.0^{}`
  at `dfef00fcb4ecd1208919872289f77731207f1ce0`; installed executable SHA-256 is
  `6b2c63c965c2b2b401bd1430f3996df496c1bc8469bb1df4b1b66fb39926f689`.
- Preflight resolved Specify CLI `1.0.1`, bootstrap `0.9.0`, Spec Kit `v1.0.1`
  and immutable ref `9118ed15a0ba65053469a94c560ea5d233f75884`.
- One non-frozen refresh migrated the lock from schema 2 to schema 3, preserved
  legacy user-level skills and recorded 19 project-local skill hashes.
- `speckit-bootstrap . --doctor --frozen` passed after migration.
- `github-issue-canon v0.3.2` archive SHA-256 is
  `184e31dc14759ae461318c586545922ea4f2c89493d900891907b15781426e67` and immutable
  ref is `344713a3d4d10673d3fd984b611ecfdc2c6ce1c8`; validator checked 300 issues,
  subsequent frozen doctor passed, and no `__pycache__` appeared.
- Direct agent-context refresh passed with the Python runtime from the
  installed `specify` shebang; no global PyYAML installation was needed.
- Repeated refresh preserved the tracked status digest
  `b906ea1350d806d4b4f5f85773a9b4ffd8b3ad1d7fea0da5d6d4b87cab2a3a7f` and the
  integrity-managed tree digest
  `373acf51989f2c9df90b7750d1703dd1525bc02e530f05bf5664ce0ef3c3314b`.
  Only `installed_at` rotated in the two bootstrap-owned `skip-worktree`
  receipts `.specify/extensions/.registry` and
  `.specify/integrations/codex.manifest.json`; this is expected machine-local
  metadata and creates no tracked governance drift.
- `python3 scripts/check_spec_kit_governance.py --self-test` passed its positive
  fixture and all four required negative classes; the repository guard also
  passed.
- Final `infra/scripts/ci-local.sh --fast` passed after adopting the patch releases:
  governance guard PASS, 1347 server tests passed, server lint passed and
  Python compile passed. Two dependency deprecation/import warnings were
  reported without test failures.
- Ponytail review found one self-test fixture simplification, which was applied
  and revalidated. Final `$speckit-converge` found no remaining missing,
  partial, contradictory or unrequested work and appended no tasks.
- Full CI was explicitly stopped because product runtime was not changed; the interrupted run is not PASS and is not used as evidence. Product release preparation and deployment remain intentionally out of scope.
