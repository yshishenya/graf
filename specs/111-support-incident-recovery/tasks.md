# Tasks: Восстановление отчётов поддержки

**Input**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md), [security checklist](checklists/security.md), and [UX checklist](checklists/ux.md)

**Risk / validation lane**: High-risk feature: auth/session and CSRF use, private GitHub egress, PostgreSQL-backed diagnostics, local durable state, privacy and degraded UX. Tests precede behaviour changes; the repository gate is required.

**Organization**: Tasks are ordered by independently verifiable user story. `tasks.md` is the implementation source of truth. Mark a task `[X]` only after its exact validation evidence is present.

## Format: `[ID] [P?] [Story] Description`

- **[P]** means another developer could work in a different file without waiting on an incomplete task.
- **[US#]** maps work to the user stories in `spec.md`.
- Every task names exact files.

## Phase 1: Foundation and regression tests

**Purpose**: Make the production auth boundary and safe data contract executable before changing delivery behaviour.

- [X] T001 [P] [US1] Add failing cookie-session/CSRF, production legacy-header rejection, and accepted server-response contract coverage in `apps/server/tests/integration/test_support_incidents.py`, `apps/server/tests/contract/test_support_incident_contract.py`, and `apps/server/tests/contract/test_cabinet_csrf_contract.py`.
- [X] T002 [P] [US1] Add failing same-origin/argument-only bridge boundary, response decoding, and no-manual-cookie regression coverage in `apps/macos/Shared/Tests/EmbeddedCabinetSupportIncidentBridgeTests.swift`, `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`, and `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`.
- [X] T003 [P] [US2] Add failing safe Issue body and internal readiness status coverage in `apps/server/tests/unit/test_support_incident_github_issue_body.py`, `apps/server/tests/unit/test_support_incident_redaction.py`, and `apps/server/tests/integration/test_health_readiness.py`.
- [X] T004 [P] [US3] Add failing accepted-pending, no-new-payload sync retry, durable `pending_sync`, localized accessibility copy, and safe clipboard fallback coverage in `apps/server/tests/integration/test_support_incidents.py`, `apps/server/tests/contract/test_support_incident_contract.py`, `apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift`, and `apps/macos/Shared/Tests/CaptureControlV5Tests.swift`.

**Checkpoint**: Tests distinguish auth rejection from server acceptance and block cookie/CSRF boundary regressions.

---

## Phase 2: User Story 1 — отправить отчёт о неудачной записи (Priority: P1) 🎯 MVP

**Goal**: An authenticated macOS user sends a metadata-only report through the embedded cabinet and receives a `CUST-*` correlation number with a private Issue link when synchronization succeeds.

**Independent Test**: A cookie-authenticated, CSRF-valid synthetic report reaches the server through the fixed same-origin bridge; the private Issue is created once, and a legacy-header-only request remains rejected.

### Implementation for User Story 1

- [X] T005 [US1] Update accepted support response models, correlation-number assignment before external egress, idempotency handling, and authenticated intake orchestration in `apps/server/src/twobrain_rec_server/api/schemas.py`, `apps/server/src/twobrain_rec_server/api/support_incidents.py`, and `apps/server/src/twobrain_rec_server/support/incidents.py`.
- [X] T006 [US1] Add the narrowly scoped `DesktopSupportIncidentSubmitting` transport boundary and remove manual session-cookie attachment from `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift` and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T007 [US1] Implement and wire the fixed same-origin WebKit support bridge without token/cookie extraction in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`, `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, and `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T008 [US1] Run the focused User Story 1 pytest/XCTest commands from `specs/111-support-incident-recovery/quickstart.md` and record metadata-only results in `specs/111-support-incident-recovery/validation/us1-authenticated-intake.md`.

**Checkpoint**: A real authenticated desktop path no longer relies on disabled legacy headers or copied web cookies.

---

## Phase 3: User Story 2 — понять проблему по private Issue (Priority: P2)

**Goal**: A private Issue contains actionable, structured metadata-only facts and an operator can see support integration configuration without a secret disclosure.

**Independent Test**: Synthetic report rendering includes correlation number, problem/failure/state/version/timeline/fingerprint/sync sections, rejects forbidden content, and internal readiness reports a bounded support configuration state.

### Implementation for User Story 2

- [X] T009 [US2] Extend the generated private Issue section with the server `CUST-*` correlation number and truthful synchronization status while preserving redaction/dedupe behaviour in `apps/server/src/twobrain_rec_server/support/github_issues.py` and `apps/server/src/twobrain_rec_server/support/incidents.py`.
- [X] T010 [US2] Expose bounded support-integration configuration state through the existing internal readiness contract in `apps/server/src/twobrain_rec_server/api/health.py` and `apps/server/src/twobrain_rec_server/api/schemas.py` without performing public GitHub calls or revealing a secret.
- [X] T011 [US2] Run the focused redaction, Issue-body, readiness and support-intake pytest suite from `specs/111-support-incident-recovery/quickstart.md` and record safe results in `specs/111-support-incident-recovery/validation/us2-private-issue.md`.

**Checkpoint**: Support has sufficient safe facts to triage an incident; the Issue remains private and content-free.

---

## Phase 4: User Story 3 — честный результат при деградации (Priority: P3)

**Goal**: A report accepted by the server survives temporary Issue synchronization failure, and the desktop clearly distinguishes pending, rejected and sign-in-required outcomes.

**Independent Test**: A fake GitHub outage yields `202 pending_sync` with `CUST-*`; a later sync request carries only that number and transitions to a linked Issue. An unsafe/auth/network failure exposes the right localized recovery and only the safe clipboard fallback.

### Implementation for User Story 3

- [X] T012 [US3] Implement accepted-pending result, workspace-scoped no-payload synchronization retry, bounded failure states and rate/idempotency preservation in `apps/server/src/twobrain_rec_server/api/support_incidents.py`, `apps/server/src/twobrain_rec_server/api/schemas.py`, and `apps/server/src/twobrain_rec_server/support/incidents.py`.
- [X] T013 [US3] Add durable `pending_sync` support state, retry transport operation and backward-safe queue updates in `apps/macos/Shared/Sources/Models/AudioModelCore.swift`, `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`, and `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T014 [US3] Replace the generic support failure message with truthful pending/rejected/sign-in-required copy, a safe clipboard action, and accessible sync recovery controls in `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift` and `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.
- [X] T015 [US3] Run the User Story 3 server and macOS tests from `specs/111-support-incident-recovery/quickstart.md` and record the three-state matrix in `specs/111-support-incident-recovery/validation/us3-degraded-states.md`.

**Checkpoint**: The desktop never calls a pending report lost, and it never claims an Issue exists before the server confirms it.

---

## Phase 5: Cross-cutting validation and tracker reconciliation

- [X] T016 Update `[Unreleased]` in `CHANGELOG.md` with the user-visible report recovery, authentication and compatibility boundary for feature 111.
- [X] T017 Run `git diff --check`, the complete quickstart suite, and `infra/scripts/ci-local.sh`; record non-sensitive command outcomes and selected high-risk lane in `specs/111-support-incident-recovery/validation/local-ci.md`.
- [X] T018 Run `$ponytail-review` on the final diff; remove unjustified complexity, preserve auth/privacy controls, and record the conclusion in `specs/111-support-incident-recovery/validation/ponytail-review.md`.
- [X] T019 Reconcile every completed feature-111 task with its GitHub Issue, add Russian evidence comments, and leave incomplete work open according to `docs/agent-guidance/github-issue-canon.md`.

## Dependencies and execution order

1. T001–T004 establish the regression tests and are complete before code changes.
2. T005–T007 deliver the P1 authenticated vertical slice; T008 is its independent proof.
3. T009–T011 add detailed private Issue/readiness proof without weakening P1.
4. T012–T014 add the pending/retry/degraded states; T015 proves them.
5. T016–T019 only begin after all desired user stories are green.

## Parallel opportunities

- T001–T004 touch separate test surfaces and can be prepared in parallel before implementation.
- T006 and server-only T005 can proceed independently after their corresponding tests are in place, but T007 waits for the transport interface.
- T009 and T010 touch separate server files after T005 is stable.
- Do not parallelize direct edits to `support_incidents.py`, `incidents.py`, `DesktopUploadClient.swift`, or `DesktopUploadQueueService.swift` in one shared checkout.

## Implementation strategy

1. Deliver P1 first: no auth downgrade, no copied cookie, a valid report reaches the already authorized server route.
2. Preserve and enrich the existing private Issue redaction path rather than inventing new diagnostics storage.
3. Add accepted-pending and sync retry as the smallest durable degraded mode, then make its product copy honest and accessible.
4. Run the high-risk validations, a Ponytail complexity review and tracker reconciliation before requesting approval to commit or release.
