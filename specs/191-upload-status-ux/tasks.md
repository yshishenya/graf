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

## Phase 10: User Story 6 - Modern Settings controls (P1)

- [X] T025 [US6] Record switch, hint, theme, copy, and control-semantics decisions in `specs/191-upload-status-ux/spec.md`, `specs/191-upload-status-ux/research.md`, `specs/191-upload-status-ux/plan.md`, and `specs/191-upload-status-ux/checklists/ux.md`.
- [X] T026 [US6] Extend rendered-template and static contracts for shared switches, information hints, segmented themes, and checkbox boundaries in `apps/server/tests/unit/test_cabinet_template_components.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/contract/test_settings_ui_contract.py`, and `apps/server/tests/contract/test_calendar_settings_contract.py`.
- [X] T027 [US6] Add the minimal switch, information-hint, and theme-picker primitives in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html` and theme icons in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/icons.html`.
- [X] T028 [US6] Replace the misaligned upload retention checkbox and inline explanation with the shared switch and hint in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html`.
- [X] T029 [US6] Replace independent notification and calendar preference checkboxes with shared switches while preserving multi-select checkboxes in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`.
- [X] T030 [US6] Compact account Settings copy and sections and replace theme radio rows with the shared segmented theme picker in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`.
- [X] T031 [US6] Centralize switch, hint, theme, preference-row, typography, divider, and responsive states in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` without adding JavaScript or a new dependency.

## Phase 11: Modern Settings validation

- [X] T032 [P] Run focused template, static, web-shell, settings, and calendar contracts and update `CHANGELOG.md` with the user-visible behavior.
- [X] T033 [P] Inspect upload, account, notifications, recording, and calendar Settings in the in-app Browser at desktop and 375px, in light/dark themes, and with hover/keyboard focus on the hint.
- [X] T034 Run `infra/scripts/ci-local.sh --fast`, record evidence, and leave the validated follow-up uncommitted until explicit approval.

## Phase 12: Native macOS accent closeout

- [X] T035 Replace remaining system-blue product accents with `DesktopMeetingShellChrome.shellAccentColor` in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`, `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`, and `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T036 Add the native violet-token source contract in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`, compile the package, run the focused suite, and confirm only provider identity marks retain blue.

## Phase 13: User Story 7 - Shared unavailable and empty states (P1)

- [X] T037 [US7] Record the full-page state, inline-notice, runtime privacy, and release boundaries in `specs/191-upload-status-ux/spec.md`, `specs/191-upload-status-ux/research.md`, `specs/191-upload-status-ux/plan.md`, `specs/191-upload-status-ux/quickstart.md`, and checklists.
- [X] T038 [P] [US7] Add rendered and static contracts for one shared state component, standard primary actions, runtime template reuse, safe access-loss cleanup, and the absence of `new-button` in `apps/server/tests/unit/test_cabinet_template_sections.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/contract/test_recording_share_invitation_contract.py`, and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.
- [X] T039 [US7] Add the compact state component to `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` and reuse it from meeting-unavailable, unavailable-invitation, shared-meetings empty, and the meeting-detail recovery template.
- [X] T040 [US7] Clone the shared recovery template in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, centralize its layout in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, migrate the upload trigger to the standard primary button, and remove legacy `new-button` and duplicate `.empty-state` rules.

## Phase 14: Expanded validation and release

- [X] T041 [P] Run focused rendered-template, web-shell, invitation, runtime-recovery, and static-asset tests and inspect the shared states locally at desktop, 375px, keyboard focus, and 200% zoom.
- [X] T042 Run `infra/scripts/ci-local.sh --full` and record the expanded validation result in `specs/191-upload-status-ux/plan.md` and `CHANGELOG.md`.
- [ ] T043 Complete the approved push, PR, merge, issue closeout, notarized CalVer release, production dry run/execute, and exact deployed-SHA smoke using `docs/agent-guidance/release-and-validation.md` and `docs/agent-guidance/macos-notarization.md`.

## Dependencies

- T003-T006 depend on T001.
- T007-T009 depend on the existing upload activity contract and can proceed after T001.
- T010-T012 depend on implementation tasks T003-T009.
- T013-T016 establish the shared system before T017-T021.
- T022-T024 depend on T013-T021.
- T027-T031 depend on T025-T026; T028-T030 depend on T027; T032-T034 depend on T027-T031.
- T035-T036 follow the cabinet color closeout in T032-T034; T036 depends on T035.
- T038 can start after T037; T039 depends on T038; T040 depends on T039.
- T041 depends on T038-T040; T042 depends on T041; T043 depends on T042.
