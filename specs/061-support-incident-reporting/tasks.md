# Tasks: Support Incident Reporting

**Input**: Design documents from `/Users/yshishenya/.codex/worktrees/503d/crisp/specs/061-support-incident-reporting/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/support-incident-contract.md](contracts/support-incident-contract.md), [quickstart.md](quickstart.md)

**Tests**: Included because this is a `high-risk-feature` touching privacy diagnostics, backend API/storage, external GitHub dependency behavior, and native UX fallback state.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently after the shared foundation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase when file paths do not overlap.
- **[Story]**: User story label for story phases only: `[US1]`, `[US2]`, `[US3]`.
- Every task includes exact repository paths.

## Phase 1: Setup (Shared Scaffolding)

**Purpose**: Create minimal new file locations and test doubles used by the implementation.

- [X] T001 Create the support package marker in `apps/server/src/twobrain_rec_server/support/__init__.py`
- [X] T002 [P] Create the fake GitHub issue test double in `apps/server/tests/fakes/fake_github.py`
- [X] T003 [P] Create macOS support incident fixture helpers in `apps/macos/Shared/Tests/DesktopSupportIncidentFixtures.swift`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core trust-boundary, persistence, configuration, and API primitives that block all user stories.

**Critical**: No user story work should begin until this phase is complete.

- [ ] T004 Add support incident GitHub config fields, timeout config, and production safety validation in `apps/server/src/twobrain_rec_server/config.py` and `apps/server/.env.example`
- [ ] T005 Create the `SupportIncident` and `SupportIncidentRateLimitBucket` SQLAlchemy models with tenant scope, GitHub linkage, redacted JSON, affected count, dedupe fields, and durable rate-limit fields in `apps/server/src/twobrain_rec_server/db/models/support.py`
- [ ] T006 Add Alembic migration `0010_support_incidents.py` for support incidents, durable rate-limit buckets, indexes, uniqueness, and RLS policy in `apps/server/src/twobrain_rec_server/db/migrations/versions/0010_support_incidents.py`
- [ ] T007 Export the `SupportIncident` and `SupportIncidentRateLimitBucket` models in `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T008 Add support incident request, response, safe metadata, and failure schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T009 Implement allowlist redaction, forbidden-content detection, stable ordering, and safe report fingerprinting in `apps/server/src/twobrain_rec_server/support/redaction.py`
- [X] T010 Implement the minimal GitHub issue title/body/label builder and `httpx` client in `apps/server/src/twobrain_rec_server/support/github_issues.py`
- [ ] T011 Implement the support incident persistence service shell with redaction, durable rate-limit bucket checks, and GitHub dependency injection in `apps/server/src/twobrain_rec_server/support/incidents.py`
- [ ] T012 Add the support incident API router and register it in `apps/server/src/twobrain_rec_server/api/support_incidents.py` and `apps/server/src/twobrain_rec_server/main.py`
- [ ] T013 Extend `DesktopUploadClientProtocol`, shared request handling, and client error mapping for support incident submission in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T014 Add desktop support incident payload, response, and submission state types in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [ ] T015 Persist support incident submission state in the local upload ledger in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`

**Checkpoint**: Foundation ready. User story implementation can now proceed.

---

## Phase 3: User Story 1 - Send A Safe Report From A Blocked Local Recording (Priority: P1)

**Goal**: A user can send a safe support report from native custody UI and sees `Отчет отправлен. Мы разберемся. Номер: CUST-{github_issue_number}` only after the private GitHub issue exists or is updated.

**Independent Test**: Put a local recording into a support/admin/terminal reportable custody state, submit the report, and confirm `CUST-{github_issue_number}` persists for the same custody item while stored server data remains metadata-only.

### Tests for User Story 1

- [ ] T016 [P] [US1] Add contract coverage for successful `POST /api/v1/desktop/support-incidents`, `CUST-*` response shape, and forbidden desktop-direct GitHub assumptions in `apps/server/tests/contract/test_support_incident_contract.py`
- [ ] T017 [US1] Add integration coverage for successful incident persistence plus fake private GitHub issue creation in `apps/server/tests/integration/test_support_incidents.py`
- [ ] T018 [P] [US1] Add macOS tests for reportable custody states, full safe payload construction, and sent incident persistence in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`
- [ ] T019 [P] [US1] Add macOS client tests for support incident JSON request path, timeout, and `CUST-*` decoding in `apps/macos/Shared/Tests/DesktopUploadClientTests.swift`

### Implementation for User Story 1

- [ ] T020 [US1] Expand the desktop metadata-only support report fields and report availability rules in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`
- [ ] T021 [US1] Implement `submitSupportIncident` on the desktop upload client using `POST /api/v1/desktop/support-incidents` in `apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift`
- [ ] T022 [US1] Implement the authenticated support incident endpoint success path in `apps/server/src/twobrain_rec_server/api/support_incidents.py`
- [ ] T023 [US1] Implement redacted persistence plus new GitHub issue creation for the success path in `apps/server/src/twobrain_rec_server/support/incidents.py`
- [ ] T024 [US1] Add the primary `Отправить отчет` loading and success state to the native upload status card in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T025 [US1] Add the same support incident action/status affordance to the native right-panel custody detail row in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [ ] T026 [US1] Save and reload sent incident numbers for custody items in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`

**Checkpoint**: User Story 1 is independently functional and testable as the MVP.

---

## Phase 4: User Story 2 - Fall Back Safely When The Report Cannot Be Sent (Priority: P2)

**Goal**: Offline, unsafe, backend, GitHub, configuration, timeout, and rate-limit failures show the calm failure copy and visible `Скопировать отчет` fallback without exposing unsafe content or promising recovery.

**Independent Test**: Block support intake or submit unsafe metadata, then confirm the desktop shows `Не удалось отправить. Скопируйте отчет и отправьте в поддержку.`, keeps the safe report available, and never creates a user-visible success.

### Tests for User Story 2

- [X] T027 [P] [US2] Add unit coverage for unsafe payload rejection, allowlisted fallback values, deterministic redacted JSON, and forbidden evidence strings in `apps/server/tests/unit/test_support_incident_redaction.py`
- [ ] T028 [US2] Add contract coverage for `400`, `403`, `422`, `429`, and `503` fallback problem responses in `apps/server/tests/contract/test_support_incident_contract.py`
- [ ] T029 [US2] Add integration coverage for missing labels, wrong repo, public repo, GitHub outage, GitHub timeout, durable rate-limit bucket fallback, and no GitHub mutation while rate-limited in `apps/server/tests/integration/test_support_incidents.py`
- [ ] T030 [P] [US2] Add macOS fallback state, copy button visibility, safe clipboard report, accessible names, keyboard/focus reachability, and non-overlap tests for both native custody surfaces in `apps/macos/Shared/Tests/CaptureControlTests.swift` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`

### Implementation for User Story 2

- [X] T031 [US2] Harden unsafe payload rejection and metadata-only fallback values in `apps/server/src/twobrain_rec_server/support/redaction.py`
- [ ] T032 [US2] Map unsafe, workspace mismatch, unsupported schema, rate-limit, configuration, and GitHub unavailable failures to safe `Problem` responses in `apps/server/src/twobrain_rec_server/api/support_incidents.py`
- [X] T033 [US2] Implement repo privacy, label existence, auth failure, timeout, and GitHub rate-limit handling in `apps/server/src/twobrain_rec_server/support/github_issues.py`
- [ ] T034 [US2] Preserve failed-with-copy-fallback state and retry-safe local report state in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T035 [US2] Show the failure copy, visible `Скопировать отчет` fallback, and accessible labels in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T036 [US2] Update terminal expired and admin/access-policy human copy in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`

**Checkpoint**: User Stories 1 and 2 both work independently.

---

## Phase 5: User Story 3 - Support Receives A Deduped Metadata-Only Incident (Priority: P3)

**Goal**: Duplicate root causes update one private incident/GitHub issue with `affected_count`, at most 5 safe identities, and a safe structured issue body.

**Independent Test**: Submit repeated safe reports with the same root cause and confirm one persisted incident, one issue number, updated `affected_count`, bounded safe identity list, and no forbidden content in the GitHub issue body.

### Tests for User Story 3

- [X] T037 [P] [US3] Add unit coverage for GitHub issue title/body rendering, stable section order, metadata block replacement, closed-issue safe JSON retention, and forbidden-content safety in `apps/server/tests/unit/test_support_incident_github_issue_body.py`
- [ ] T038 [US3] Add duplicate aggregate integration scenarios for same dedupe key, affected count, and existing issue update in `apps/server/tests/integration/test_support_incidents.py`
- [ ] T039 [P] [US3] Add macOS aggregate-report tests for five matching custody items and bounded safe identities in `apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift`

### Implementation for User Story 3

- [ ] T040 [US3] Implement deterministic dedupe key derivation, upsert behavior, and max-5 safe identity cap in `apps/server/src/twobrain_rec_server/support/incidents.py`
- [X] T041 [US3] Implement GitHub issue update behavior that preserves human sections and replaces only generated metadata/counters in `apps/server/src/twobrain_rec_server/support/github_issues.py`
- [ ] T042 [US3] Ensure database uniqueness and indexes match dedupe semantics in `apps/server/src/twobrain_rec_server/db/migrations/versions/0010_support_incidents.py`
- [ ] T043 [US3] Add aggregate affected-count and safe identity payload support for grouped custody summaries in `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`

**Checkpoint**: All user stories are independently functional and safe.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final safety proof, repository hygiene, and release-facing documentation.

- [ ] T044 [P] Update the unreleased changelog entry for feature `061-support-incident-reporting` in `CHANGELOG.md`
- [ ] T045 [P] Confirm quickstart scenarios and validation commands remain accurate after implementation in `specs/061-support-incident-reporting/quickstart.md`
- [ ] T046 Run the focused server test command from `specs/061-support-incident-reporting/quickstart.md`
- [ ] T047 Run `swift test --package-path apps/macos` for native custody/report coverage from `specs/061-support-incident-reporting/quickstart.md`
- [ ] T048 Run `infra/scripts/ci-local.sh` as the repository gate in `infra/scripts/ci-local.sh`
- [ ] T049 Confirm no implementation diff touches the server-owned WebView meeting list route in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [ ] T050 Prepare Russian PR evidence with risk lane, validation, issue links, and no closing keywords unless fully closed using `.github/pull_request_template.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks every user story.
- **Phase 3 US1**: Depends on Phase 2. This is the MVP.
- **Phase 4 US2**: Depends on Phase 2 and can proceed in parallel with US1 if file conflicts are coordinated; it becomes user-visible once US1 exists.
- **Phase 5 US3**: Depends on Phase 2 and can proceed in parallel with US1/US2 after shared data contracts exist; it is easiest after US1 success path exists.
- **Phase 6 Polish**: Depends on all desired user stories for the PR.

### User Story Dependencies

- **US1 (P1)**: MVP path; no dependency on US2/US3 after foundation.
- **US2 (P2)**: Depends on foundation; integrates with US1 UI/client paths for final user-facing fallback.
- **US3 (P3)**: Depends on foundation; integrates with US1 issue creation and US2 dependency-failure behavior.

### Within Each User Story

- Write story tests before implementation and keep them failing until the story code lands.
- Server schemas/models before services.
- Redaction before persistence or GitHub body rendering.
- Services before endpoint wiring.
- Desktop payload/client before native action state.
- Story checkpoint before moving to the next priority when working sequentially.

## Parallel Opportunities

- T002 and T003 can run in parallel after T001.
- T004, T008, T009, T010, T013, and T014 can start in parallel once file ownership is assigned.
- T016, T018, and T019 can run in parallel for US1.
- T027 and T030 can run in parallel for US2.
- T037 and T039 can run in parallel for US3.
- T044 and T045 can run in parallel during polish.

## Parallel Example: User Story 1

```text
Task: T016 [P] [US1] Add contract coverage in apps/server/tests/contract/test_support_incident_contract.py
Task: T018 [P] [US1] Add macOS projection coverage in apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift
Task: T019 [P] [US1] Add macOS client coverage in apps/macos/Shared/Tests/DesktopUploadClientTests.swift
```

## Parallel Example: User Story 2

```text
Task: T027 [P] [US2] Add redaction unit coverage in apps/server/tests/unit/test_support_incident_redaction.py
Task: T030 [P] [US2] Add fallback/accessibility UI coverage in apps/macos/Shared/Tests/CaptureControlTests.swift and apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
```

## Parallel Example: User Story 3

```text
Task: T037 [P] [US3] Add GitHub issue body unit coverage in apps/server/tests/unit/test_support_incident_github_issue_body.py
Task: T039 [P] [US3] Add aggregate macOS projection coverage in apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 for US1.
3. Stop and validate: focused US1 server/macOS tests plus safe evidence.
4. Only then add fallback hardening and aggregate dedupe.

### Incremental Delivery

1. Foundation -> redaction, storage, GitHub client, endpoint shell, desktop state primitives.
2. US1 -> successful report submission and `CUST-*` state.
3. US2 -> failure/offline/config fallback and copy safety.
4. US3 -> dedupe/aggregate private issue updates.
5. Polish -> changelog, quickstart validation, local CI, PR evidence.

### Validation Closeout

1. Run focused server tests from `specs/061-support-incident-reporting/quickstart.md`.
2. Run `swift test --package-path apps/macos`.
3. Run `infra/scripts/ci-local.sh`.
4. Record selected lane `high-risk-feature` and safe evidence in the PR.

## Notes

- `tasks.md` is the implementation source of truth after generation.
- GitHub issues must be created later via `$speckit-taskstoissues` after `$speckit-analyze`.
- Do not create GitHub issues directly from the desktop app.
- Do not send or record audio, transcript text, raw local paths, tokens, signed URLs, human names, emails, account labels, or private meeting content in tests or evidence.
- Keep `apps/server/src/twobrain_rec_server/cabinet/web.py` outside this feature unless a later explicit feature says otherwise.
