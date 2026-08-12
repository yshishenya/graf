# Implementation Evidence: Feature 145

Date: 2026-08-12

## Scope and lane

- Lane: significant/high-risk capture change; full Spec Kit flow.
- Branch: `145-assisted-autostart-hardening`.
- Initial implementation base: `fc1be4d289234d47821a232172f25df1513f0749`.
- Before publication the validated commit was rebased onto current
  `origin/master` at `c43e1f09`; the only content conflict was in
  `docs/current-product-status.md`, where both the current Feature 140 runtime
  closeout and the Feature 145 implementation block were retained.
- Numbering was checked against local specs and remote branches before creation.
  Feature 145 was free; the next feature number is 146.
- Production rollout, deployment and runtime enablement were not performed.

## Implemented behavior

- The Feature 124 eight-second countdown, Start, Skip and target-scoped saved
  preference remain intact.
- Assisted start now requires an active workspace-scoped policy and a persisted
  exact user+device acknowledgement. Policy and acknowledgement are rechecked
  before and after asynchronous permission work.
- Button, timeout and saved-target starts use separate reason and initiator
  evidence; automatic starts are not attributed to a button press.
- Target activity, permissions, current upload-queue budget, native volume
  capacity, active session, indicator and one-action Stop fail closed.
- Runtime and committed production defaults remain disabled.

## Focused validation

- `.venv/bin/ruff check ...`: PASS.
- `.venv/bin/pytest tests/unit/test_config_validation.py -q`: 67 passed.
- `run_local_postgres_tests.sh --focused tests/contract/test_meeting_detection_api_contract.py -q`:
  5 passed.
- `run_local_postgres_tests.sh --focused tests/contract/test_openapi_contract_drift.py -q`:
  10 passed.
- `swift test`: 664 passed.
- Runtime OpenAPI contains all required `AssistedAutoStartPolicy` fields,
  including `deviceRef`, `issuedAt` and `expiresAt`.
- `git diff --check`: PASS.

The first full CI attempt found one legitimate OpenAPI drift failure after the
new response schema was added. The canonical OpenAPI YAML was regenerated from
the FastAPI runtime using the repository-documented command. The focused drift
suite and the repeated full CI then passed.

## Full local CI

Command: `infra/scripts/ci-local.sh`

Final post-rebase result: `ci_local_result=pass mode=full`.

- Retired audio-driver architecture guard: PASS.
- macOS build: PASS.
- macOS tests: 664 passed.
- macOS contract validation: PASS.
- Server parallel suite: 2883 passed, 1 skipped.
- Strict PostgreSQL suite: 42 passed, 1 skipped.
- Server lint and Python compile: PASS.
- Production Compose rendering: PASS; assisted auto-start is `false` and all
  scoped policy values are empty by default.
- Deployment evidence scan: PASS.

The local CI reports the live-production RLS probe as not attempted because no
production database was supplied. This is expected for local implementation
validation and is not represented as production evidence.

## Review and limitations

- Correctness review found and fixed pre-`issuedAt` activation, missing exact
  device binding and OpenAPI drift.
- Ponytail review removed an unused recursive recordings-directory scan; the
  implementation reuses the known queue size and native volume capacity without
  a new dependency, endpoint or database table.
- No real meeting/audio was captured during automated validation. A manual
  capture smoke remains a release-time action because it exercises local macOS
  permissions and creates real recording artifacts.
- GitHub task issues #5024-#5040 exist for T001-T017. Feature 145 issue content
  is canonical. The repository-wide issue validator still reports pre-existing
  non-canonical Feature 140 issues #5017-#5019; they were not normalized without
  separate approval.

## Verdict

Implementation and local validation are complete. The feature remains disabled
in production and is ready for review/commit, not deployment.
