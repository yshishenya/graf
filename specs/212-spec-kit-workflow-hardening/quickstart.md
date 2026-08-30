# Quickstart: Надёжный Spec Kit workflow

## Preconditions

- Рабочая ветка `212-spec-kit-workflow-hardening` основана на актуальном `origin/master`.
- Worktree чистый либо каждый существующий diff явно относится к Feature 212.
- `specify`, `speckit-bootstrap`, Git и Python 3 доступны.
- Для live-проверки issue canon доступны сеть и аутентифицированный `gh`; focused governance guard и frozen doctor сами сеть не требуют.

## Scenario 1: Source and version preflight

```sh
git status --short --branch
python3 -c 'import sys; assert sys.version_info >= (3, 9)'
specify version
speckit-bootstrap --version
speckit-bootstrap . --dry-run --json
```

Expected: Python is `3.9+`, Spec Kit resolves to stable `v1.0.1`, bootstrap is `v0.9.5`, and dry-run does not mutate files.

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

Expected: self-test proves positive and five protected negative classes, including wrong workflow order; repository check confirms bootstrap integrity and GRAF-specific rules.

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

- Source checkout `speckit-bootstrap` is clean on `main == origin/main` at
  `ae45a7d241921a19c99d797f3447a4f9284f6d88`; immutable `v0.9.5^{}` resolves to
  the same SHA. Installed executable SHA-256 is
  `b62c8de2b11f8d109710969e1c13a5e8bf2552426012a4c97801eebd04e27a2a`.
- Preflight resolved Specify CLI `1.0.1`, bootstrap `0.9.5`, Spec Kit `v1.0.1`
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
- Repeated `v0.9.5` dry-run/apply preserved the generated-artifact diff digest
  `e4227937d8f9d1342656a129d4b87953b97c44ec1cb3c80f88d6af3324751680`;
  dry-run also preserved the status digest
  `9c64cd483fbf5c8ae901a4eccd07ade8ce4f510c76df4b6b838a91855b8e5d95`.
  Only `installed_at` rotated in the two bootstrap-owned `skip-worktree`
  receipts `.specify/extensions/.registry` and
  `.specify/integrations/codex.manifest.json`; this is expected machine-local
  metadata and creates no tracked governance drift.
- `python3 scripts/check_spec_kit_governance.py --self-test` passed its positive
  fixture and all five required negative classes; repository guard, frozen
  doctor and `check-prerequisites.sh --json --paths-only` also passed.
- Issue-canon validation checked 300 issues after the final refresh; bytecode
  count remained `0 → 0`, and the subsequent frozen doctor passed.
- The earlier PR fast gate passed with governance guard PASS, 1347 server tests,
  server lint and Python compile. It was not rerun for the final generated-only
  `v0.9.5` refresh; current closeout evidence is the focused command set above.
- Product app packaging, Developer ID signing, notarization, stapling and appcast assets are `N/A`: Feature 212 changes governance/tooling only and does not publish a GRAF product build.
- Ponytail review found one self-test fixture simplification, which was applied
  and revalidated. Final `$speckit-converge` found no remaining missing,
  partial, contradictory or unrequested work and appended no tasks.
- Full CI was explicitly stopped because product runtime was not changed; the interrupted run is not PASS and is not used as evidence. Product release preparation and deployment remain intentionally out of scope.
