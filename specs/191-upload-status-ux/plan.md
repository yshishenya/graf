# Implementation Plan: Upload Status, Processing Visibility, And Upload Date

**Branch**: `191-upload-status-ux` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

## Summary

Expose the existing server receipt timestamp as `uploaded_at`, use it only as the date fallback for manual uploads, and redesign the main upload/processing experience. Consolidate the existing cabinet CSS into one canonical token and primitive layer for violet interaction color, typography, geometry, helper text, Settings navigation, switches, information hints, theme selection, repeated controls, and compact full-page state screens. Reuse one server-rendered state component for direct and runtime unavailable-meeting flows instead of rebuilding it in JavaScript. Reuse the existing native macOS violet token for matching SwiftUI states and actions. Keep HTMX, XHR progress, native form inputs, current Jinja primitives, and the single existing stylesheet.

## Technical Context

**Language/Version**: Python 3.13, browser JavaScript, CSS, Swift 6

**Primary Dependencies**: Existing Pydantic schemas, Jinja rendering, HTMX, native XHR, existing cabinet CSS, SwiftUI

**Storage**: Existing PostgreSQL `meetings.created_at`; no migration

**Testing**: Focused pytest unit/integration/contract tests, focused Swift tests/build, local rendered browser QA

**Risk / Validation Lane**: high-risk-feature; user-facing degraded/upload states and a shared backend projection are affected

**Release Gate**: user-approved full cycle after green validation: push, PR, merge, notarized CalVer release, production dry run/execute, and exact-SHA smoke

**Target Platform**: Browser cabinet and embedded desktop cabinet

**Project Type**: Server-rendered web cabinet with embedded macOS surface

**Performance Goals**: No additional polling or network request; list refresh behavior remains unchanged

**Constraints**: Preserve server-mediated upload, metadata-only evidence, accessibility, keyboard focus, reduced motion, and forced colors

**Scale/Scope**: Whole server-rendered cabinet style audit plus native macOS product-accent audit; implementation prioritizes the meeting list, upload activity, upload dialog, Settings navigation/overview, and shared controls.

## Constitution Check

- **UX and brand distance**: PASS. Public usability principles inform behavior, while the implementation uses original GRAF layout, components, violet tokens, assets, and Russian copy. Clean-room and brand-distance review is recorded before merge.
- **Upload and server boundary**: PASS. No endpoint, credential, object-storage, or MediaScribe boundary changes.
- **Accessibility**: PASS. Existing live regions, progressbar semantics, focus handling, reduced-motion, and forced-colors behavior remain required.
- **Deletion/storage truth**: PASS. The date is metadata only and does not change retention or deletion behavior.

## Validation Plan

1. Add focused tests for `uploaded_at`, manual-upload date fallback, and legacy «Без даты» behavior.
2. Add/adjust static contract assertions for violet product accents, shared checkbox/radio styling, compact progress composition, canonical Settings rules, and visible action discoverability.
3. Run focused pytest targets for view models, cabinet list, web shell, and static assets.
4. Run `infra/scripts/ci-local.sh --fast` if the environment supports the repository gate.
5. Run the local cabinet flow in the in-app Browser; inspect main, upload dialog, upload/processing evidence, Settings overview/detail, desktop/375px reflow, DOM state, interaction, and console health.
6. Compare upload, account, notifications, and calendar screens with the measurable GRAF density and accessibility contract; verify switch geometry, theme segments, divider rhythm, tooltip hover/focus, and critical-copy visibility in light and dark themes.
7. Compile the macOS package and run the focused accessibility/style contract after replacing native system-blue product accents with the existing violet token.
8. Render and inspect the server meeting-unavailable page, runtime access-loss replacement, unavailable invitation, and shared-meetings empty state at desktop and 375px widths.
9. Run `infra/scripts/ci-local.sh --full`, then complete PR/merge and the repository notarization, release, deployment, and exact-SHA smoke runbooks.

## Validation record

- Focused unit, static-contract, and web-shell tests: `216 passed`.
- Isolated PostgreSQL integration lane for the cabinet list: `29 passed`.
- Modern Settings and shared-button follow-up suite: `160 passed`.
- Isolated PostgreSQL calendar Settings contract: `20 passed`.
- macOS `AppControlAccessibilityTests`: `22 passed`; the focused run compiled
  the full Swift package and executable targets.
- `infra/scripts/ci-local.sh --fast`: `1168 passed`, lint and Python compile
  passed.
- In-app Browser on the local server: manual-upload meeting row rendered
  `Обрабатывается` and `Загружено 23 авг, 01:23`; 375px viewport had no
  horizontal overflow; upload dialog rendered with violet dropzone and primary
  action; browser error/warning log was empty.
- Current-run 375px screenshots covered the collapsed main screen, upload hint,
  account sessions, calendar, notifications, recording, summaries, and light
  theme. Ordinary button labels remained centered and on one line, upload
  actions reused the shared button contract, and the upload hint stayed inside
  the dialog.
- The native file chooser was unavailable to the in-app Browser harness, so the
  live transfer card itself was validated through the existing JavaScript
  contract harness and focused tests rather than an actual file transfer.
- Repository color scan found no remaining system `.blue` product accent in the
  audited native macOS UI. Remaining blue values in cabinet CSS are isolated to
  official calendar-provider identity marks.
- Expanded shared-state suite passed `236` focused unit, rendered-template,
  web-shell, invitation, runtime-recovery, and static-asset checks against an
  isolated PostgreSQL container; the focused CSS/static contract rerun passed
  `55` checks after restoring short actionable upload errors.
- Current-run shared-state Browser QA covered direct unavailable meeting and
  invitation pages, the empty shared-meetings list, runtime access loss,
  keyboard focus, a 375px viewport, and 200% equivalent reflow. The browser
  console remained empty. Accepted narrow screenshots include
  `25-settings-overview-375.png`, `26-settings-account-375.png`,
  `29-settings-account-hint-no-overlap-375.png`, and
  `31-upload-hint-aligned-375.png`.
- Historical pre-review `infra/scripts/ci-local.sh --full` passed on reviewed
  commit `1490f64701db2f66ee5fb644e182d234c2ef7ec4`: 726 macOS tests, 3313 server
  tests plus one expected skip, 52 strict PostgreSQL/RLS tests plus one expected
  skip, server lint, Python compile, production Compose rendering, and the
  deployment evidence scan. This is historical validation, not release-gate
  evidence for a later candidate.
- Clean-room and brand-distance review passed: the implementation uses original
  GRAF components, violet tokens, assets, and Russian copy and contains no
  external product assets, icons, copy, or distinctive screen composition.

## Project Structure

```text
apps/server/src/twobrain_rec_server/api/schemas.py
apps/server/src/twobrain_rec_server/cabinet/view_models.py
apps/server/src/twobrain_rec_server/cabinet/rendering.py
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/icons.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/primitives.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_unavailable_content.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/share_invitation_content.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_with_me_list_content.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shell.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html
apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
apps/server/tests/unit/test_cabinet_view_models.py
apps/server/tests/integration/test_cabinet_meeting_list.py
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/contract/test_cabinet_static_assets_contract.py
apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift
apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
```

**Structure Decision**: Keep one `cabinet.css`, the existing Jinja primitives, and the existing `DesktopMeetingShellChrome.shellAccentColor` native token. Extend the existing section catalog with one state component and clone its inert template for runtime recovery. Add no frontend framework, dependency, migration, CSS-in-JS layer, or parallel component system.

## Complexity Tracking

No constitution violations.
