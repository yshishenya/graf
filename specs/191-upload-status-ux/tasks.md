# Tasks: Upload Status And Cabinet Design System

**Input**: Design documents from `/specs/191-upload-status-ux/`

## Phase 1: Foundation

- [X] T001 [P] Add the `uploaded_at` projection and document the date/status contract in `apps/server/src/twobrain_rec_server/api/schemas.py` and `specs/191-upload-status-ux/contracts/upload-status-ux.md`.
- [X] T002 [P] Record the high-risk UX and upload validation lane in `specs/191-upload-status-ux/plan.md` and checklists.

## Phase 2: User Story 1 - Truthful status (P1)

- [X] T003 [US1] Update the meeting list view model and rendering in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py` so upload, waiting, processing, and attention states are distinct.
- [X] T004 [US1] Add focused unit/integration coverage in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/integration/test_cabinet_meeting_list.py`.

## Phase 3: User Story 2 - Upload date (P1)

- [X] T005 [US2] Populate `uploaded_at` from existing `Meeting.created_at` in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and use it only for manual-upload date fallback.
- [X] T006 [US2] Cover manual-upload and legacy date behavior in `apps/server/tests/unit/test_cabinet_view_models.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.

## Phase 4: User Story 3 - Upload progress UI (P1)

- [X] T007 [US3] Redesign the activity markup and state updates in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` for visible percent/bar/action alignment.
- [X] T008 [US3] Replace affected blue accents and tighten responsive states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T009 [US3] Update static asset contracts in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 5: Validation

- [X] T010 [P] Run focused pytest targets for view models, list rendering, web shell, and static assets.
- [X] T011 [P] Run local Browser QA for desktop and 375px upload/progress/processing states, including console and interaction checks.
- [X] T012 Run `infra/scripts/ci-local.sh --fast` when the repository environment supports it and record the result.

## Phase 6: User Story 4 - Shared cabinet system (P1)

- [X] T013 [US4] Add canonical semantic color, typography, geometry, and control tokens and shared native checkbox/radio treatment in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T014 [US4] Replace remaining GRAF product-blue interaction styles and isolate provider identity colors in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T015 [US4] Consolidate conflicting repeated Settings/card/control rules instead of adding another style layer in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T016 [US4] Extend static asset contracts for central tokens, violet form controls, product-blue exclusions, and canonical shared rules in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 7: User Story 3 - Compact main-screen upload experience (P1)

- [X] T017 [US3] Move upload percentage next to status, simplify state/recovery copy, and keep actions visible in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T018 [US3] Reduce empty space and align progress, metadata, state, and actions across desktop/mobile in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T019 [US3] Shorten upload-dialog copy and reuse the shared form-control system in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`.

## Phase 8: User Story 5 - Stable Settings layout (P1)

- [X] T020 [US5] Stabilize Settings sidebar width, row height, labels, helper text, cards, and narrow reflow in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T021 [US5] Add contract coverage for Settings label geometry, single canonical overview-card rules, and responsive reflow in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 9: Final validation

- [X] T022 [P] Run focused static, view-model, web-shell, and meeting-list tests for the expanded scope.
- [X] T023 [P] Capture and inspect current-run desktop/375px screenshots for main, upload dialog, processing/date, and Settings; inspect console health.
- [X] T024 Run `infra/scripts/ci-local.sh --fast` and record the expanded validation result without committing or deploying.

## Dependencies

- T003-T006 depend on T001.
- T007-T009 depend on the existing upload activity contract and can proceed after T001.
- T010-T012 depend on implementation tasks T003-T009.
- T013-T016 establish the shared system before T017-T021.
- T022-T024 depend on T013-T021.
