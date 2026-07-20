# Tasks: Manual Media Upload UI

**Input**: Design documents from `/specs/090-manual-media-upload-ui/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/manual-upload-ui-contract.md](./contracts/manual-upload-ui-contract.md),
[quickstart.md](./quickstart.md)

**Tests**: Required. This is a high-risk feature touching upload UX, auth/CSRF,
storage custody entry, and embedded desktop WebView boundaries.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Confirm active stacked context and validation anchors before code.

- [X] T001 [P] Verify active feature context and stacked `087` dependency in `specs/090-manual-media-upload-ui/plan.md`
- [X] T002 [P] Verify quickstart commands and forbidden-content scan targets in `specs/090-manual-media-upload-ui/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Shared backend boundary that blocks all upload UI stories.

**CRITICAL**: User story work depends on this phase because both browser and
embedded UI need the same CSRF-safe cabinet upload boundary.

### Tests

- [X] T003 [P] Add regression coverage for public `087` `/api/v1/media-uploads` behavior after helper extraction in `apps/server/tests/integration/test_manual_media_upload.py`
- [X] T004 [P] Add cabinet upload route contract coverage for response shape and OpenAPI presence in `apps/server/tests/contract/test_ingest_openapi_contract.py`

### Implementation

- [X] T005 Create shared manual media upload helper in `apps/server/src/twobrain_rec_server/ingest/manual_media_upload.py`
- [X] T006 Refactor public manual upload endpoint to call the shared helper in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T007 Add CSRF-protected cabinet manual upload route in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T008 Update response/schema imports only as needed for the cabinet upload route in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T009 Update generated OpenAPI contract after route changes in `specs/012-server-ingest-foundation/contracts/openapi.yaml`

**Checkpoint**: Public `087` upload and new cabinet upload route are both
available without UI.

---

## Phase 3: User Story 1 - Upload Owned Media From Web Cabinet (Priority: P1)

**Goal**: Browser owner can upload one media file from `/meetings`, see
progress, and receive accepted meeting handoff.

**Independent Test**: Cookie-authenticated owner opens `/meetings`, selects a
small media file, submits with CSRF, receives accepted meeting response, and
sees upload UI controls without desktop headers.

### Tests

- [X] T010 [P] [US1] Add browser meeting list rendering assertions for upload entry, sheet controls, CSRF meta, and empty-state upload action in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T011 [P] [US1] Add browser successful cabinet upload integration test in `apps/server/tests/integration/test_cabinet_manual_upload.py`
- [X] T012 [P] [US1] Add static asset guard for manual upload JS/CSS without frontend toolchain drift in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`

### Implementation

- [X] T013 [US1] Add trusted manual upload fragment source in `apps/server/src/twobrain_rec_server/cabinet/templates.py`
- [X] T014 [US1] Render manual upload fragment from meeting list page in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T015 [US1] Add manual upload sheet template in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`
- [X] T016 [US1] Enable browser upload entry and empty-state action in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [X] T017 [US1] Add file metadata, duration fallback, idempotency identity, XHR upload, progress, abort, and accepted handoff controller in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T018 [US1] Add responsive upload sheet, progress, validation, and accepted-state styles in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

**Checkpoint**: US1 works independently in browser with a session cookie and
CSRF token.

---

## Phase 4: User Story 2 - Upload From Embedded Desktop Cabinet (Priority: P1)

**Goal**: Embedded desktop `/desktop/meetings` exposes the same server-owned
upload sheet when session/CSRF proof exists and keeps native capture boundaries
outside WebView.

**Independent Test**: Cookie-authenticated embedded route renders desktop-safe
upload UI, does not introduce `/desktop/upload`, and route policy remains safe.

### Tests

- [X] T019 [P] [US2] Add embedded desktop upload rendering assertions for `/desktop/meetings` in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T020 [P] [US2] Add embedded desktop successful cabinet upload integration test in `apps/server/tests/integration/test_cabinet_manual_upload.py`
- [X] T021 [P] [US2] Add or update desktop route-policy assertions that `/desktop/upload` remains unnecessary or blocked in `apps/macos/Shared/Tests/DesktopCabinetNavigationRequestPolicyTests.swift`

### Implementation

- [X] T022 [US2] Pass embedded surface mode and upload availability into the manual upload fragment in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T023 [US2] Add desktop-safe upload copy and browser-only workflow exclusions in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`
- [X] T024 [US2] Ensure embedded upload action degrades safely when CSRF/session proof is absent in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`
- [X] T025 [US2] Update desktop route policy only if T021 proves a required gap in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`

**Checkpoint**: US2 works independently for embedded session/cookie cabinet and
does not move native capture or local uploader behavior into web code.

---

## Phase 5: User Story 3 - Handle Upload Errors Safely (Priority: P1)

**Goal**: Validation, auth, network, server, and processing-unavailable states
are safe, localized, actionable, and metadata-only.

**Independent Test**: Invalid browser and embedded upload attempts produce safe
messages and no secret/object/path/content leakage.

### Tests

- [X] T026 [P] [US3] Add CSRF missing, stale CSRF, and expired-session upload tests in `apps/server/tests/integration/test_cabinet_manual_upload.py`
- [X] T027 [US3] Add missing file, invalid duration, empty file, oversized file, and duplicate retry tests in `apps/server/tests/integration/test_cabinet_manual_upload.py`
- [X] T028 [P] [US3] Add no-secret/no-private-content upload error assertions in `apps/server/tests/contract/test_cabinet_no_secret_content_egress.py`

### Implementation

- [X] T029 [US3] Add safe cabinet upload problem-code mapping in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T030 [US3] Add accessible validation/error/live-region markup in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`
- [X] T031 [US3] Add server-side cabinet upload CSRF/session-specific safe problem responses in `apps/server/src/twobrain_rec_server/api/cabinet.py`
- [X] T032 [US3] Add error, disabled, indeterminate progress, and reduced-motion styling in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

**Checkpoint**: US3 failure states are independently testable without private
media or credentials.

---

## Phase 6: User Story 4 - Preserve Meeting List And Review Continuity (Priority: P2)

**Goal**: Accepted manual uploads become normal meeting rows/details with
manual-media provenance and existing processing/review states.

**Independent Test**: Upload acceptance refreshes the list/detail handoff, and
manual upload rows behave like other meetings under search/status rendering.

### Tests

- [X] T033 [P] [US4] Add list refresh and accepted manual upload row assertions in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T034 [P] [US4] Add manual upload detail handoff assertions for processing and ready states in `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T035 [P] [US4] Add view-model assertions for manual upload source/provenance/action labels in `apps/server/tests/unit/test_cabinet_view_models.py`

### Implementation

- [X] T036 [US4] Update manual upload row provenance/action labels if needed in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T037 [US4] Refresh meeting list region and detail link handoff after accepted upload in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T038 [US4] Ensure processing/accepted copy remains separate from transcript and notes readiness in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

**Checkpoint**: US4 preserves the existing meeting review loop without a
parallel upload list model.

---

## Phase 7: Polish, Validation, And Closeout

**Purpose**: Cross-cutting checks, docs, and evidence for the high-risk lane.

- [X] T039 [P] Update feature behavior and validation notes in `CHANGELOG.md`
- [X] T040 [P] Run placeholder and forbidden-content scans covering `specs/090-manual-media-upload-ui`, `apps/server/src/twobrain_rec_server/api`, `apps/server/src/twobrain_rec_server/ingest`, `apps/server/src/twobrain_rec_server/cabinet`, and `apps/server/tests`
- [X] T041 Run focused server validation from `specs/090-manual-media-upload-ui/quickstart.md`
- [X] T042 Run focused macOS `DesktopCabinet` validation if any Swift source or route-policy test changed in `apps/macos`
- [X] T043 Run full local CI with `infra/scripts/ci-local.sh`
- [X] T044 Mark completed tasks `[X]` only after validation evidence passes in `specs/090-manual-media-upload-ui/tasks.md`
- [X] T045 Record high-risk validation lane, quickstart evidence, CI evidence, no-deploy status, and stacked `087` dependency in `specs/090-manual-media-upload-ui/tasks.md` closeout notes and the final response or PR

---

## Phase 8: Post-Release UX Correction - List-Owned Upload Progress

**Purpose**: Apply stakeholder feedback after the first polished modal release:
the upload sheet starts the transfer and closes, while the meetings workspace
shows progress, status, and hover/focus controls.

- [X] T046 [P] Update 090 spec, contract, data model, research, and quickstart for list-owned upload progress in `specs/090-manual-media-upload-ui/`
- [X] T047 [P] Add meeting-list upload activity rendering assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T048 [P] Update static asset contract for upload activity controls in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T049 Move manual upload progress/accepted/cancel UI from the sheet into meeting-list upload activity rows in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_list_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T050 [P] Update user-visible changelog for the corrected upload workflow in `CHANGELOG.md`
- [X] T051 Run focused quickstart validation for the corrected upload workflow and record evidence in closeout notes

---

## Phase 9: Post-Release Duration Field Correction

**Purpose**: Apply stakeholder feedback after production review: duration is
file information from metadata, not a user-editable field.

- [X] T052 [P] Update 090 spec, contract, data model, research, and quickstart so duration is metadata-derived and not user-editable in `specs/090-manual-media-upload-ui/`
- [X] T053 [P] Add regression assertions for hidden-only duration submission and no manual duration listener in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T054 Remove the visible duration number field while keeping the hidden backend field in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`
- [X] T055 Update manual-upload JS validation to block unreadable duration metadata without asking for manual seconds in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T056 Remove unused duration-field CSS in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T057 Update user-visible changelog for the duration-field correction in `CHANGELOG.md`

---

## Phase 10: Post-Release Embedded WebView File Picker Correction

**Purpose**: Fix the installed-app embedded cabinet path where the server-owned
manual upload surface rendered but WebKit had no native file-picker delegate.

- [X] T058 Add embedded WebView regression coverage for manual upload file picker support in `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`
- [X] T059 Add `WKUIDelegate` open-panel handling for server-owned manual upload file inputs in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- [X] T060 Harden embedded manual-upload button/modal contracts in `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/contract/test_cabinet_static_assets_contract.py`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T061 Update user-visible changelog and run focused Swift/server validation for the embedded upload workflow in `CHANGELOG.md`

GitHub tracking: #2804.

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 has no dependencies.
- Phase 2 depends on Phase 1 and blocks all user stories.
- US1, US2, and US3 depend on Phase 2.
- US4 depends on the accepted-upload handoff from US1 and can be completed
  after US1.
- Phase 7 depends on all implemented user stories selected for closeout.
- Phase 8 depends on the released 090 implementation and does not change the
  `087` backend route or public API contract.
- Phase 9 depends on the released Phase 8 upload-list workflow and does not
  change the `087` backend route or public API contract.
- Phase 10 depends on the released Phase 9 workflow and does not add native
  upload business logic; it only restores the WebKit file-picker bridge needed
  by the existing server-owned form.

### User Story Dependencies

- **US1 (P1)**: First MVP browser path after foundational route/helper.
- **US2 (P1)**: Shares US1 UI components and validates embedded desktop
  surface mode.
- **US3 (P1)**: Shares US1/US2 routes and UI, but failure states are
  independently testable.
- **US4 (P2)**: Depends on upload acceptance and reuses existing list/detail
  models.

### Parallel Opportunities

- T001-T004 can run in parallel.
- T010-T012 can run in parallel after Phase 2.
- T019-T021 can run in parallel after Phase 2.
- T026 and T028 can run in parallel; T027 touches the same file as T026 and
  should be coordinated.
- T033-T035 can run in parallel.
- T039 and T040 can run in parallel after implementation.
- T046-T048 and T050 can run in parallel; T049 touches runtime UI files and
  T051 must run after implementation.
- T052-T053 and T057 can run in parallel; T054-T056 touch the runtime upload
  UI and should be validated together.

## Parallel Examples

```text
Task: "T010 [US1] Add browser meeting list rendering assertions in apps/server/tests/unit/test_cabinet_web_shell.py"
Task: "T011 [US1] Add browser successful cabinet upload integration test in apps/server/tests/integration/test_cabinet_manual_upload.py"
Task: "T012 [US1] Add static asset guard in apps/server/tests/contract/test_cabinet_static_assets_contract.py"
```

```text
Task: "T033 [US4] Add list refresh assertions in apps/server/tests/integration/test_cabinet_meeting_list.py"
Task: "T034 [US4] Add detail handoff assertions in apps/server/tests/integration/test_cabinet_meeting_detail.py"
Task: "T035 [US4] Add view-model assertions in apps/server/tests/unit/test_cabinet_view_models.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 browser upload success.
3. Validate US1 independently with focused server tests.
4. Complete US2 embedded behavior and US3 safe failures.
5. Complete US4 continuity.
6. Run high-risk closeout gates.

### Safe Stop Points

- Stop after Phase 2 if public `087` upload compatibility fails.
- Stop after US1 if browser upload cannot pass CSRF/session and safe-progress
  tests.
- Stop after US2 if embedded desktop requires a native upload bridge or broad
  WebView POST header injection; that must become a separate Spec Kit slice.
- Stop before closeout if any no-secret scan, route-policy test, or local CI
  gate fails.

## Notes

- `[P]` means different files or no dependency on incomplete tasks.
- Tests for each story precede implementation tasks and should fail before the
  corresponding implementation.
- Implementation commits require explicit user approval after validation.
- No production deploy is part of this task list.

## Closeout Evidence

- Risk/validation lane: high-risk active Spec Kit feature slice because the
  change touches upload UX, auth/CSRF, storage custody entry, and embedded
  desktop WebView boundaries.
- Feature context: `090-manual-media-upload-ui` is stacked on the completed
  `087-own-media-upload-processing` backend/manual-upload custody slice and
  reuses the `087` one-file upload backend path through a shared helper.
- GitHub tracking: grouped execution issues were created and validated through
  `github-issue-canon` as #2645, #2646, #2647, #2648, #2649, and #2650.
- Review gate: post-implementation diff review found no critical/blocking
  findings. Checked CSRF/session boundary, legacy header-only rejection,
  one-file helper reuse, duplicate retry behavior, single-track processing,
  Alembic head, OpenAPI contract, metadata-only errors, embedded route policy,
  and release hygiene.
- Post-rebase focused server validation after replaying onto `origin/master`:
  `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_manual_upload.py tests/integration/test_manual_media_upload.py tests/integration/test_cabinet_csrf.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_ingest_openapi_contract.py tests/contract/test_openapi_contract_drift.py`
  passed with `81 passed, 1 warning`.
- Post-release UX correction evidence on 2026-07-08:
  - `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py tests/integration/test_cabinet_manual_upload.py tests/integration/test_cabinet_meeting_list.py` -> 64 passed.
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_manual_upload.py tests/integration/test_manual_media_upload.py tests/integration/test_cabinet_csrf.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_ingest_openapi_contract.py` -> 76 passed.
  - `PYTHONPATH=src uv run --extra dev ruff check .` -> pass.
  - `git diff --check` -> pass.
  - Forbidden-content scan on changed files -> no matches.
  - `infra/scripts/ci-local.sh` -> `ci_local_result=pass`; 1036 passed, 4 skipped, server lint passed, python compile passed, deployment evidence scan passed.
- Post-release duration-field correction evidence on 2026-07-08:
  - `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py tests/integration/test_cabinet_manual_upload.py tests/integration/test_cabinet_meeting_list.py` -> 64 passed.
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_manual_upload.py tests/integration/test_manual_media_upload.py tests/integration/test_cabinet_csrf.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py tests/contract/test_ingest_openapi_contract.py` -> 76 passed.
  - `PYTHONPATH=src uv run --extra dev ruff check .` -> pass.
  - `git diff --check` -> pass.
  - Diff-only forbidden-content scan on new lines -> no matches.
  - `infra/scripts/ci-local.sh` -> `ci_local_result=pass`; 1036 passed, 4 skipped, server lint passed, python compile passed, deployment evidence scan passed.
- Post-rebase macOS embedded-route validation:
  `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet'`
  passed with `74 tests, 0 failures`.
- Placeholder scan and forbidden-content scan completed for the spec, server
  API/ingest/cabinet code, and server tests. Matches were reviewed as source
  identifiers, HTML placeholder attributes, existing placeholder table/code
  names, synthetic test fixture values, or checklist text; no live secrets,
  signed URLs, raw audio, raw transcript text, or private meeting content were
  identified.
- Full local CI:
  `infra/scripts/ci-local.sh` passed with `ci_local_result=pass`; server tests
  reported `1036 passed, 4 skipped, 1 warning`, server lint passed, Python
  compile completed, production compose config rendered, and deployment
  evidence scan passed.
- Post-release embedded WebView file-picker correction evidence on 2026-07-08:
  - GitHub tracking: #2804.
  - `node --check apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py` -> 44 passed.
  - `PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_cabinet_manual_upload.py tests/integration/test_cabinet_csrf.py tests/integration/test_cabinet_meeting_list.py tests/unit/test_cabinet_web_shell.py tests/contract/test_cabinet_static_assets_contract.py` -> 69 passed.
  - `PYTHONPATH=src uv run --extra dev ruff check .` -> pass.
  - `swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|EmbeddedCabinet'` -> 79 passed.
  - `swift build --package-path apps/macos --product TwoBrainRecApp` -> pass.
  - `git diff --check` -> pass.
  - Diff-scope forbidden-content scan -> no matches.
  - `infra/scripts/ci-local.sh` -> `ci_local_result=pass`; 1050 passed, 4 skipped, 1 warning, server lint passed, Python compile passed, deployment evidence scan passed.
- The original implementation slice did not run production deploy/smoke; later
  release lanes deployed the browser and embedded upload flow. The final
  security-closeout release evidence is tracked in Phase 11 below.
- Implementation commit was created after explicit user release/closeout
  approval and rebased cleanly onto `origin/master`.
- Phase 10 embedded WebView file-picker correction was merged in PR #2805,
  released as `v2026.07.08.7`, deployed with smoke evidence, and installed
  locally as documented in the closure comment for GitHub issue #2804.

---

## Phase 11: Security Review Reconciliation And Final Release Closeout

**Purpose**: Reconcile the already deployed security-review follow-up with the
repository source of truth, validate the exact merge candidate, build the local
macOS application, and publish a release from the merged `master` SHA.

- [X] T062 Review PR #3040 for auth, CSRF, tenant isolation, storage, migration,
  processing, and egress regressions and record validated findings.
- [X] T063 Merge the current `origin/master` into the security-closeout branch
  without discarding unrelated work.
- [X] T064 Run the 090 focused server, migration, auth, storage, and egress
  validation against the exact merge candidate.
- [X] T065 Run focused macOS cabinet/WebView validation and build the release
  `TwoBrainRecApp` product.
- [X] T066 Run `infra/scripts/ci-local.sh` and the metadata-only forbidden-content
  scans against the exact merge candidate.
- [X] T067 Build, sign, and verify the local owner-machine `GRAF.app` package;
  record that installation in `/Applications` requires interactive macOS admin
  authorization and preserve the Developer ID/notarization limitation.
- [X] T068 Merge PR #3040 and verify that its merge SHA is contained in current
  `master`.
- [X] T069 Prepare and publish the next CalVer release from the exact merged
  `master` SHA with Russian release notes and migration/rollback limitations.
- [X] T070 Run production deploy dry-run, execute, health checks, smoke, and
  runtime-SHA ancestry verification.
- [X] T071 Reconcile all feature-090 GitHub issues with post-deploy evidence and
  remove only feature-specific temporary closeout state.

### Phase 11 closeout evidence

- PR #3040 merged to `master`; release PR #3042 merged.
- Release `v2026.07.11.1` targets merged SHA
  `eec53931b99aca8629ec208c2c75a86d8c05c649`.
- Focused server/auth/migration/storage/egress validation: `142 passed`.
- Focused macOS validation: `150 tests, 0 failures`; release build passed.
- Full local CI and deploy-gate CI: `1220 passed, 4 skipped`; lint, compile,
  compose validation, and deployment evidence scan passed.
- Production backup and restore rehearsal passed; migration head is
  `0020_user_scoped_recording_ids`; disposable production RLS probe passed.
- Production smoke `smoke-20260710-211520` passed with
  `readiness_verdict=infra_smoke_ready`; smoke cleanup passed.
- Local `GRAF.app` and `graf-local.pkg` version `2026.07.11.1` built and passed
  strict `codesign` verification with the local self-signed identity. Package
  SHA-256:
  `0933abf173f1367a382835a1d723c1f5c1b432a1895f7aa1108092473e91a38e`.
  Public Developer ID signing/notarization remains unavailable, and installing
  the local package requires interactive administrator authorization.

---

## Phase 12: Current-Diff Convergence (2026-07-20)

Эта append-only фаза закрывает только проверенные расхождения текущего diff.
Старые релизные receipts выше не переиспользуются как доказательство новых
границ. Внешний production Chrome/E2E путь остаётся отдельным gate.

- [ ] T072 [P0] Доказать полный результат ручной загрузки на реальной записи
  (transcript, speaker truth, сохранённый summary и cleanup) без публикации
  содержимого в evidence; зависит от внешнего MediaScribe/Chrome пути (#3050).
- [X] T073 [P1] Показать в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
  честный accepted-without-dispatch статус и recovery для auth/session failure;
  покрыто static asset contract (#3047).
- [X] T074 [P0] Сохранить source-kind-aware playback M4A contract и regression
  coverage текущего `manifest.py`/`finalize.py`/normalization пути (#3046).
- [X] T075 [P0] Выполнить fingerprint preflight до materialization в
  `apps/server/src/twobrain_rec_server/ingest/finalize.py` и доказать сохранение
  принятого multipart object при конфликтном retry (#3048).
- [X] T076 [P1] Добавить stat size в `MinioStorage` и fail-closed проверку
  playback/download до выдачи range headers в `cabinet/egress.py` (#3045).
- [X] T077 [P1] Добавить regression checks для UI recovery controls и
  `workflow_started` handoff в `tests/contract/test_cabinet_static_assets_contract.py`.
- [X] T078 [P0] Подтвердить bounded multipart stream и отсутствие whole-file
  `UploadFile.read` в текущем manual-upload path (#3053, canonical T090).
- [X] T079 [P0] Подтвердить durable custody и immutable conflict boundary
  focused PostgreSQL тестом (#3052, canonical T089).
- [X] T080 [P0] Проверить защищённый embedded picker в
  `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift` (#3054, canonical T091).
- [X] T083 [P0] Получить независимый product/UX/code/security/release review
  receipt после исправлений T073–T080; остаточные external E2E и browser
  runtime gates явно сохранены открытыми (#3044, canonical T083).
- [X] T084 [P0] Добавить origin/cleanup/UI recovery regression assertions
  (#3057, canonical T094).
- [X] T085 [P0] Повторить release/deploy gate для текущего runtime diff после
  merge; `v2026.07.20.6` и production SHA `bcfba51a` подтверждены, а полный
  external user-path E2E остаётся отдельным T072/#3050 gate (#3049).
- [X] T095 [P0] Ограничить smoke helpers exact production HTTPS/loopback origin,
  mode-0600/O_NOFOLLOW auth material и exact `run_id` binding в
  `apps/server/scripts/smoke_target.py` (#3058).
- [X] T096 [P0] Дополнить workspace-prefix cleanup receipt фактическим
  post-run zero-object read-back; production smoke returned residue `0` and
  cleanup passed without publishing keys (#3059).
- [X] T097 [P1] Убрать blind retry для fingerprint/auth conflict и сохранить
  keyboard-safe recovery controls (#3060).
- [X] T098 [P0] Провести текущий-diff closeout checks и закрыть связанные
  GitHub issues только после receipts (#3061); доказанные review/cleanup
  issues #3044, #3055 и #3059 закрыты, внешние E2E issues оставлены открытыми.
- [X] T092 [P0] Получить независимый review receipt после исправлений и
  зафиксировать остаточные ограничения без заявления production Chrome proof
  (#3055, canonical T092).
- [ ] T093 [P0] Зафиксировать metadata-only E2E и zero-residue evidence на
  текущем exact SHA; raw audio/transcript/summary не сохраняются
  (#3056, canonical T093).

## Phase 13: Validation Receipt (2026-07-20)

- [X] V001 Run `node --check`, focused PostgreSQL tests, focused Swift tests,
  `git diff --check`, Ruff, compile and forbidden-content scan; exact counts are
  recorded in `validation/closeout-2026-07-20.md`.
- [X] V002 Run `GRAF_TEST_WORKERS=4 bash infra/scripts/ci-local.sh` on the final
  candidate and record the exact SHA and result in the receipt.
- [X] V003 Run independent code review and Ponytail review; record findings and
  residual limitations without claiming production Chrome proof.

## Phase 14: Tracker and Release Boundary

- [X] V004 Close only issues whose acceptance is proven by the receipt;
  #3044, #3055 and #3059 закрыты после receipts, а #3050, #3056, #3049 и
  #3061 остаются открытыми для внешних или дополнительных границ.
- [X] V005 Prepare and deploy CalVer `v2026.07.20.6` only after runtime code
  from Phase 12 was merged and the production gate was green; the release and
  exact runtime SHA are recorded above.
