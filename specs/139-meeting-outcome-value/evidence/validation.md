# Validation receipt

Дата: `2026-08-04`
Lane: significant/high-risk AI, user workflow, privacy/access and release.
Scope: pre-commit validation и отдельно одобренный prompt gate; server
deploy/package не заявлены.

## Focused feature lane

- Isolated PostgreSQL runner:
  `apps/server/scripts/run_local_postgres_tests.sh --focused ...`.
- Result: `319 passed`, `0 failed`, `2` known non-feature warnings,
  `216.00s`; isolated container removed successfully.
- Covered outcome prompt/validator, candidate revisions, prompt optimization,
  view models, browser shell, summary UI contract, generation, public sharing,
  accepted-only export and cabinet outcome integrations.

## Static and content checks

- `ruff check apps/server/src apps/server/tests`: pass.
- Python compile for `apps/server/src`: pass.
- `node --check` for `cabinet.js`: pass.
- `git diff --check`: pass.
- Repository evidence scanner over Feature 139 evidence Markdown/CJS: pass,
  `flagged_file_count=0`.
- Prompt/eval receipt: pass; `92` retained observations, `0` critical failures,
  `30/30` judge calibration agreement and `10/10` format routing.

## Canonical fast CI

- Command: `infra/scripts/ci-local.sh --fast`.
- Post-rebase rerun date: `2026-08-05`.
- Result: `ci_local_result=pass mode=fast`.
- Server unit suite: `882 passed`, `0 failed`, `2` known non-feature warnings,
  `51.94s`.
- Server Ruff and Python compile: pass.
- macOS removed-legacy-audio architecture guard: pass; Swift lane skipped as
  designed by fast mode.
- Isolated PostgreSQL container cleanup: pass.

## Prompt release gate

- Operator-approved exact promotion/readback: `14/14` prompts.
- Private synthetic e2e: `5/5` model calls, three judges `1.00/pass`, reflection
  parser `pass`; trace has `6` observations including terminal receipt.
- Historical outcome `v3` was found incompatible with the new strict runtime
  schema as a future rollback target, so compatible unlabelled `v6` rollback
  versions were prepared.
- Outcome labels were returned to exact `v3` after the e2e so the currently
  deployed old runtime remains compatible; final `v5` move is post-deploy.
- No CI bypass or `skip-local-CI` option was used.
