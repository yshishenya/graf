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

Expected: Spec Kit resolves to stable `v1.0.1`, bootstrap is `v0.8.0`, dry-run does not mutate files.

## Scenario 2: One-time migration

```sh
speckit-bootstrap .
speckit-bootstrap . --doctor --frozen
```

Expected: lock schema 3, project-local skills and hashes, managed local-state ignore, preserved legacy user-level skills.

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

Expected: fast lane includes the focused governance check. Full CI, release preparation and deployment are not executed.

## Validation Evidence — 2026-08-30

- Source checkout `speckit-bootstrap` fast-forwarded cleanly to
  `6019b1b4267292d415c78c9325f2e95555fba9c5` (`v0.8.0^{}`); source and installed
  executable SHA-256 both equal
  `9761c3615d1f506c729053641b0946a2f1d0f8aa5c6a617f01110add8202151a`.
- Preflight resolved Specify CLI `1.0.1`, bootstrap `0.8.0`, Spec Kit `v1.0.1`
  and immutable ref `9118ed15a0ba65053469a94c560ea5d233f75884`.
- One non-frozen refresh migrated the lock from schema 2 to schema 3, preserved
  legacy user-level skills and recorded 19 project-local skill hashes.
- `speckit-bootstrap . --doctor --frozen` passed after migration.
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
- Final `infra/scripts/ci-local.sh --fast` passed on the completed diff:
  governance guard PASS, 1346 server tests passed, server lint passed and
  Python compile passed. Two dependency deprecation/import warnings were
  reported without test failures.
- Ponytail review found one self-test fixture simplification, which was applied
  and revalidated. Final `$speckit-converge` found no remaining missing,
  partial, contradictory or unrequested work and appended no tasks.
- Full CI, release preparation and deployment remain intentionally out of scope.
