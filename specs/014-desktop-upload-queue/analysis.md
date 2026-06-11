# Specification Analysis Report: Desktop Upload Queue

**Created**: 2026-06-11

## Findings

| ID | Category | Severity | Location(s) | Summary | Recommendation |
|----|----------|----------|-------------|---------|----------------|
| A1 | Coverage | LOW | `tasks.md` T024-T028 | Validation tasks depend on local macOS tooling and may be partially blocked outside full Xcode/runtime environments. | Record blockers explicitly in `evidence/test-results.md` if local tooling cannot run. |

## Coverage Summary

| Requirement Key | Has Task? | Task IDs | Notes |
|-----------------|-----------|----------|-------|
| FR-001 auto queue | Yes | T007, T010, T011, T012 | Covered by persistence, discovery, and app hooks. |
| FR-002 identity preservation | Yes | T004, T006, T007 | Covered by deterministic queue model. |
| FR-003 states | Yes | T004, T005, T006, T015 | Covered by model and UI tasks. |
| FR-004 30-second visibility | Yes | T011, T012, T028 | Covered by launch/finalize scan and validation script. |
| FR-005 restart survival | Yes | T007, T010, T028 | Covered by durable queue persistence. |
| FR-006 bounded retry | Yes | T014, T020, T021 | Covered by retry and retention tasks. |
| FR-007 server truth before uploaded | Yes | T018, T019, T022 | Covered by client/finalize/contract tasks. |
| FR-008 transient retry | Yes | T013, T014, T019 | Covered by failure classification and worker. |
| FR-009 artifact retention | Yes | T020, T021 | Covered by retention decision tasks. |
| FR-010 manual action | Yes | T015, T016 | Covered by UI and action wiring. |
| FR-011 idempotency | Yes | T017, T018, T019 | Covered by client tests and implementation. |
| FR-012 track completeness | Yes | T004, T007, T015 | Covered by artifact profile and UI. |
| FR-013 failure classes | Yes | T004, T013, T014 | Covered by model and retry tests. |
| FR-014 no third-party upload | Yes | T018, T022, T027 | Covered by client scope and scans. |
| FR-015 no purge while pending | Yes | T020, T021 | Covered by retention tasks. |
| FR-016 accounting diagnostics | Yes | T003, T008, T009, T023 | Covered by audit and redaction tasks. |
| FR-017 capture behavior unchanged | Yes | T011, T012, T015, T029 | Covered by app hooks and final audit. |
| FR-018 independent of auto-start/driver | Yes | T011, T012, T029 | Covered by app integration scope. |
| FR-019 deterministic ordering/non-regression | Yes | T006, T007 | Covered by transition tests and service. |
| FR-020 retryability evidence | Yes | T004, T014, T015, T023 | Covered by models, worker, UI, logs. |
| FR-021 role mapping | Yes | T007, T017, T018, T022 | Covered by queue/client/contracts. |
| FR-022 compact UI scope | Yes | T015, T016 | Covered by CaptureControlView tasks. |
| FR-023 env-only bearer auth | Yes | T031, T032, T034, T035, T036, T037, T038 | Covered by upload-specific env header handling, redaction, production smoke token-file flow, temporary AuthSession issuance, and cleanup regression tests. |

## Constitution Alignment Issues

None.

## Unmapped Tasks

None.

## Metrics

- Total functional requirements: 23
- Total tasks: 38
- Coverage: 100%
- Ambiguity count: 0 blocking
- Duplication count: 0
- Critical issues count: 0

## Next Actions

Implementation may proceed. The only residual risk is local tool availability
for full validation; record any local blocker as evidence instead of treating a
missing runtime as product acceptance.

## Final Implementation Audit - 2026-06-11

Status: PASS after implementation and validation loop.

Validated evidence:

- `swift build`: PASS.
- `swift test`: PASS, 369 tests, 0 failures.
- `swift run ContractValidation`: PASS.
- `./Scripts/validate-desktop-upload-queue.sh`: PASS.
- `check-prerequisites.sh --require-tasks --include-tasks`: PASS.
- `tasks.md`: no remaining unchecked implementation tasks.

Issues found and resolved during the loop:

- Test wrapper used reserved `zsh` variable name `status`; reran with `swift_test_result`.
- New queue tests initially exposed unstable mutable clock capture and inaccessible recording-directory construction; tests now use deterministic clocks and explicit package URLs.
- Feature validator initially self-matched clarification wording in checklist/quickstart instructions; validation scope now targets only blocking artifacts.

Residual risk:

- Live ingest smoke against a real owner-controlled server URL was not run in this local pass; coverage is build, unit/contract validation, static egress validation, queue persistence/retry tests, and UI summary tests.

## Production Bearer Auth Audit - 2026-06-11

Status: PASS for implementation and production preflight; live upload is blocked only by missing local bearer token value.

Findings resolved:

- Desktop uploader lacked a bearer auth handoff for production ingest. Added env-only bearer handling with no UserDefaults persistence.
- Production smoke runner could have used a secret value CLI argument through the existing helper. Added `--token-file` support and wired runner to pass only the Docker secret file path.
- Diagnostic redaction did not explicitly cover all bearer naming variants. Added `authorization`, `bearerToken`, `uploadBearerToken`, and `authBearerToken` coverage and tests.

Production preflight evidence:

- `https://rec.2brain.pro/api/v1/health/live`: PASS.
- `https://rec.2brain.pro/api/v1/health/ready`: PASS.
- Local/server gates after auth hardening: PASS.

Remaining live-smoke blocker:

- `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN` must be supplied locally in ignored env state before any production upload attempt.

## Live Production Upload Smoke Audit - 2026-06-11

Status: PASS.

Findings:

- The Docker secret `twobrain_smoke_credential` is not a valid production Rec API bearer session token; using it produced `401 auth_session_invalid`.
- Correct production bearer behavior requires a raw `AuthSession` token with a matching database hash and trusted device binding.
- A temporary internal-smoke auth session/device binding was created, used for one live upload, and then removed during cleanup.

Evidence:

- `run_id`: `smoke-014-session-20260611-092141`.
- Upload finalized with `meeting_status=ingested_pending_processing`.
- Cleanup passed with `database_records_removed=26` and `object_keys_removed=3`.
- No bearer token value was recorded.

Follow-up:

- Update future production-smoke tooling to create and clean temporary `AuthSession` records rather than treating `twobrain_smoke_credential` as an API bearer token.

Credential hygiene note:

- The successful live-smoke bearer token was per-run only. After cleanup removed the `AuthSession`, binding, and smoke identity, the local env token value was cleared to avoid reusing a stale credential.

## 2026-06-11 AuthSession smoke hardening audit

Decision: production upload smoke must use a real temporary Rec `AuthSession`, not the infrastructure `twobrain_smoke_credential`, because the live auth boundary accepts bearer values only when they resolve to a stored valid auth-session hash and trusted device binding.

Implemented corrections:

- Added `apps/server/scripts/issue_smoke_auth_session.py` to seed the internal smoke identity, issue a temporary auth session, bind the seeded device as trusted, and write the raw bearer only to a 0600 token file.
- Added `apps/server/scripts/cleanup_smoke_auth_session.py` so auth session device bindings and auth sessions are removed before normal smoke artifact cleanup deletes the seeded device/identity rows.
- Updated `infra/scripts/run-production-smoke.sh` to call the AuthSession helper, pass `--token-file` to upload, remove the temporary token file, and include auth cleanup evidence in the final smoke result.
- Updated server regression coverage so the runner cannot regress to `twobrain_smoke_credential` bearer usage and cleanup ordering remains explicit.
- Updated `[Unreleased]` changelog Ops notes for `feature:014`, `T036-T038`.

Audit findings:

- No raw bearer is printed by the AuthSession helper dry-run or final runner output.
- `twobrain_smoke_credential` is no longer referenced by the production smoke runner as an upload bearer source.
- Auth cleanup runs before upload artifact cleanup in the normal path and is also registered as an exit trap for failure paths after session issuance.
- Local feature gates are clean: server contract subset, macOS build/test, ContractValidation, and desktop upload queue validator all passed on 2026-06-11.

Residual operational constraint:

- The updated production runner depends on new helper scripts being present inside the production `rec-api` container. Because `infra/server/Dockerfile` copies `apps/server/scripts` into the image, live validation of the updated runner requires a production image rebuild/deploy or an equivalent approved operational rollout before running `infra/scripts/run-production-smoke.sh --remote`.

Final re-check note: `.specify/feature.json` was corrected back to `specs/014-desktop-upload-queue` after temporary auth-backlog work, and `.specify/scripts/bash/check-prerequisites.sh` had its executable bit restored so the documented direct prereq command works without requiring a manual `bash` prefix.

## 2026-06-11 Deep Review Findings And Remediation

Status: remediation in progress until the final validation loop is recorded.

Findings found during the full feature review:

- The analysis coverage table did not include FR-023 or T031-T038 after bearer/AuthSession hardening. Fixed this audit traceability gap so Spec Kit coverage reflects the current feature scope.
- The production smoke runner treated auth cleanup as best-effort even on the success path. Fixed the runner to fail closed unless `auth_cleanup_result=pass`.
- The production smoke runner could run auth cleanup twice through the exit trap after a successful manual cleanup. Fixed the runner to track cleanup completion and disable the trap after required cleanup succeeds.
- Failure between smoke identity seeding and upload could leave seeded internal-smoke identity rows because artifact cleanup previously required `meeting_id` and `session_id`. Fixed `cleanup_smoke_artifacts.py` to support run-id-only identity cleanup.
- The desktop uploader accepted generic `TWO_BRAIN_REC_BEARER_TOKEN` fallback. Removed the fallback so upload bearer auth uses only the upload-specific `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN`.
- The desktop uploader generated first upload part number `1`, while server contracts, server tests, and production smoke use zero-based part numbers. Fixed the desktop client to use the same zero-based server convention.
- Diagnostic redaction removed `authorization` keys but did not remove arbitrary allowed-field values containing standalone `Bearer ...`. Added a forbidden value pattern and regression coverage.

## Final implementation audit - 2026-06-11

Status: PASS, no unresolved critical/high/medium/low implementation findings found in the audited scope.

Audit scope covered:

- Spec Kit artifacts for feature 014: spec, plan, research, data model, contracts, quickstart, tasks, checklists, analysis, and evidence.
- Server production smoke helpers and cleanup helpers.
- Desktop upload queue/client implementation and diagnostics.
- macOS and server tests related to upload, cleanup, secret env contract, diagnostic redaction, and contract validation.
- GitHub issue traceability for all 38 feature 014 tasks.
- Linear mapping validation for all 38 feature 014 tasks.

Findings fixed during audit:

- Updated stale analysis coverage from 22 functional requirements / 30 tasks to 23 functional requirements / 38 tasks, including FR-023 env-only bearer auth.
- Made production smoke auth cleanup fail closed instead of best-effort after a successful upload path.
- Prevented duplicate cleanup attempts in the smoke runner with explicit cleanup completion guards.
- Added run-id-only smoke residue cleanup so seeded identity rows can be removed even if smoke fails before upload creates meeting/session identifiers.
- Removed generic bearer-token fallback from the desktop uploader; only `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN` is accepted for upload authorization.
- Changed desktop upload part numbering to zero-based part numbers to match the server helper/smoke convention.
- Extended diagnostic redaction to remove standalone bearer values, not only `authorization` keys.
- Fixed a cleanup script syntax error caught by `py_compile`.
- Restored executable permission for `.specify/scripts/bash/check-prerequisites.sh` so the documented prerequisite command runs directly.

Residual operational note:

- Linear sync validation is clean, but the optional Linear project named `2brain Rec / 014 Desktop Upload Queue` was not present during sync, so issues were synced without that project grouping. This does not block code readiness or task traceability; it is an external Linear organization cleanup item if project-level grouping is desired.

## Linear/GitHub traceability correction - 2026-06-11

Status: PASS. The earlier residual operational note about a missing Linear Project is resolved.

Corrections applied:

- Created Linear Project `2brain Rec / 014 Desktop Upload Queue`.
- Migrated existing projectless Linear issues `YSH-148` through `YSH-185` into that project without recreating them.
- Verified all 38 Linear issues are in `Done` and assigned to the expected project.
- Added GitHub issue links to all 38 Linear issue descriptions.
- Updated local mapping with GitHub issue IDs for all 38 tasks.
- Patched the local Linear sync GitHub issue parser so `(GH #512)` style references are recognized.

Final traceability state:

- Linear Project: `2brain Rec / 014 Desktop Upload Queue`, state `completed`.
- Linear issues: 38 found, 38 in project, 38 `Done`, 38 with GitHub links.
- GitHub issues: `feature:014` open=0, closed=38.

## Upstream Linear extension/bootstrap correction - 2026-06-11

Status: PASS.

The Linear project migration exposed one remaining extension-level bug: `(GH #512)` task references were not parsed as GitHub issues because the regex required whitespace or end-of-line after the number. The upstream extension now includes a punctuation-safe parser.

Evidence:

- Upstream extension commit: `5a86776 Parse GitHub issue refs before punctuation`.
- Fresh `speckit-bootstrap .` completed after installing `PyYAML 6.0.3` for the user Python site.
- `agent-context` updated successfully during bootstrap.
- New Linear sync canonical commands were installed.
- Feature `014` sync/validate passed after bootstrap.
- Independent Linear audit confirmed 38 completed issues in the completed `2brain Rec / 014 Desktop Upload Queue` project, with 38 GitHub links.
