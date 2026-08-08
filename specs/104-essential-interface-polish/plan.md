# Implementation Plan: Essential Interface Polish

**Branch**: `104-essential-interface-polish` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/104-essential-interface-polish/spec.md`

## Summary

Polish the GRAF macOS main window into a content-first meeting workspace while preserving native capture authority. The implementation keeps the existing SwiftUI/AppKit shell, server-rendered Jinja cabinet, HTMX list updates, dark GRAF tokens, and recording/upload contracts. It removes disabled, duplicate, and unsupported plan/calendar surface elements, turns filtering and bulk actions into contextual disclosure, humanizes meeting titles and list states, and reduces the native recording inspector to a compact action-first rail plus an intentional detail panel. Metadata-only diagnostics remain available to internal/support paths but disappear from normal idle UI.

## Technical Context

**Language/Version**: Swift 6 / SwiftPM for the macOS shell; Python 3.13 for the server; HTML/Jinja, CSS, and the existing dependency-free cabinet JavaScript for the embedded surface.

**Primary Dependencies**: SwiftUI, AppKit, WebKit, Foundation, existing capture/upload presentation models; FastAPI, Jinja 3.1, HTMX attributes already used by the cabinet, and existing cabinet icon macros. No new runtime dependency.

**Storage**: No database schema or persisted-data change. Existing meeting records, query-string filters, desktop queue items, local recording manifests, settings, and upload/processing state remain authoritative. Title/status cleanup is presentation-only.

**Testing**: XCTest/SwiftPM; pytest with cabinet unit, contract, and integration suites; existing CSS/HTML contract assertions; release app build; live macOS runtime inspection through the accessibility tree and metadata-safe screenshots; `infra/scripts/ci-local.sh` as the repository gate.

**Risk / Validation Lane**: High-risk feature. The slice changes brand-distance UX, accessibility, degraded/diagnostic presentation, deletion affordances, and native capture controls. It therefore requires full Spec Kit clarify, plan, UX checklist, tasks, clean analyze, GitHub issue sync, focused native/server proof, live visual comparison, and the repository gate.

**Release Gate**: The user approved scoped feature commits after validation. Checkpoint and implementation commits may include only feature-owned files and MUST preserve unrelated worktree changes. Deploy, release publication, installer replacement, and production rollout still require a separate explicit release decision after validated implementation.

**Target Platform**: macOS 14+ native desktop application with an embedded authenticated server cabinet; server rendering remains portable across existing local/production hosts.

**Project Type**: Native macOS desktop application containing a server-owned web workspace.

**Performance / Non-regression Goals**: Preserve the existing HTMX list replacement, current short input debounce, and existing 50-row page limit without a full app reload. Add no new polling, list request, capture-thread work, network call, or background service. Preserve the existing inspector transition class while making Reduce Motion independent of animation.

**Constraints**: Preserve manual Record/Stop, persistent active-recording truth, one-action Stop, permission and local-custody truth, server/native ownership, deletion confirmation, metadata-only diagnostics, current auth/session behavior, and all stored data. Do not invent plan/billing state or an upcoming calendar event that the current main-window projection does not provide. Do not copy Krisp composition, assets, strings, or proprietary behavior. Do not commit private screenshot content. Use existing helpers, native controls, and GRAF tokens before adding code.

**Scale/Scope**: One main macOS window; one embedded meeting-list route and shared sidebar; one native inspector/rail; and the 16 session, list, capture, custody, progress, selection, refinement, unavailable, and recovery state classes in [visual-target.md](./visual-target.md). Separate settings/onboarding/menu-bar windows, detail pages, new product capability, system-wide light theme, and backend contract changes are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk UX/capture gates.

- **Capture-first platform integrity**: PASS. SwiftUI/AppKit remain owners of capture-critical controls; the WebView is only post-meeting content.
- **Visible consent and control**: PASS. Manual start remains available, active recording keeps a local persistent indicator, and Stop remains one action in the titlebar/rail independent of cabinet health.
- **Data and egress boundaries**: PASS. No storage, egress, MediaScribe, Langfuse, credential, or raw-content behavior changes.
- **Diagnostics and privacy**: PASS. Raw/debug presentation is removed from ordinary UI, while metadata-only diagnostic collection, redaction, and support safety remain intact.
- **Deletion truth**: PASS. Row and bulk deletion retain their existing bounded confirmation and server/native ownership.
- **Spec-driven delivery**: PASS. Feature 104 follows clarify → plan → checklist → tasks → analyze → taskstoissues → implement.
- **Accessibility and localization**: PASS with explicit keyboard, VoiceOver, focus, control-size, Russian-copy, contrast, and long-text contracts.
- **Brand distance**: PASS with clean-room reference use and an original GRAF visual contract.
- **Ponytail form**: PASS. Reuse the current shell, templates, HTMX behavior, icon macros, presentation helpers, and tests; remove or hide proven noise; add no library or speculative abstraction.

**After Phase 1 design**: PASS. The UI contracts and selected pre-build Stitch target keep local capture authority, explicitly separate ordinary state from support diagnostics, preserve deletion and data truth, define accessibility and privacy boundaries, remove unsupported plan/calendar presentation, and require a clean-room before/after comparison. No constitution exception is required.

## Validation Plan

1. Treat the selected source and geometry in [visual-target.md](./visual-target.md) as the pre-build design contract; production code must adapt it through the existing stack rather than import prototype dependencies.
2. Add focused server tests for enabled-only navigation, absence of unsupported plan/calendar blocks, one search surface, contextual filters/selection, no disabled placeholders, humanized titles/durations, and active-only progress.
3. Add focused Swift tests for compact rail actions, stable inspector width during recording, actionable-problem expansion, idle omission of meters/telemetry/report actions, and preserved titlebar Stop.
4. Run affected server suites with `PYTHONPATH=src uv run --extra dev pytest` from `apps/server` and affected macOS suites with `swift test --package-path apps/macos --disable-swift-testing --filter ...`.
5. Build the release app with `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
6. Run all 16 state classes from [visual-target.md](./visual-target.md) using synthetic/redacted titles only; for layout-sensitive states, capture matched evidence at `1040×680`, `1280×760`, and one wider window.
7. Confirm no overlap, horizontal scroll, surprise width change, clipped date/action, or hidden Stop. The minimum-width sidebar/toolbar may collapse labels only when exact accessible names and tooltips remain.
8. Use keyboard-only traversal and the macOS accessibility tree to verify names, roles, focus order, contextual visibility, and confirmation dialogs. Check text/non-text contrast and control targets against [Apple accessibility guidance](https://developer.apple.com/design/human-interface-guidelines/accessibility/) and [WCAG 2.2](https://www.w3.org/TR/WCAG22/).
9. Compare the same GRAF viewport/state before and after. Use Krisp only to judge general hierarchy/density; verify zero copied strings, assets, proprietary flows, or recognizable branded composition.
10. Run `infra/scripts/ci-local.sh` before closeout. Do not deploy or replace the installed production app in this lane.

## Project Structure

### Documentation (this feature)

```text
specs/104-essential-interface-polish/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── visual-target.md
├── quickstart.md
├── contracts/
│   ├── capture-surface-ui.md
│   ├── main-window-ui.md
│   └── meeting-list-presentation.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/cabinet/
│   ├── queries.py
│   ├── rendering.py
│   ├── view_models.py
│   ├── static/cabinet/
│   │   ├── cabinet.css
│   │   └── cabinet.js
│   └── templates/cabinet/
│       ├── components/sections.html
│       └── pages/meeting_list_content.html
└── tests/
    ├── contract/
    ├── integration/
    └── unit/

apps/macos/
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── Cabinet/DesktopMeetingShellView.swift
│       ├── Capture/CaptureControlView.swift
│       └── Upload/DesktopSupportIncidentActionStrip.swift
└── Shared/Tests/
    ├── AppControlAccessibilityTests.swift
    ├── CaptureControlTests.swift
    └── DesktopMeetingShellWebViewBoundaryTests.swift

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep both existing owners in place. Server files own meeting navigation, list query controls, row presentation, and deletion affordances. Native files own start/stop, permissions, local recording truth, compact rail, inspector disclosure, meters, and support recovery. Share wording through existing presentation helpers where already available; do not introduce a cross-platform design framework or a new API.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Ponytail Plan

- Delete disabled and duplicate markup before adding a new component.
- Reuse semantic HTML (`details`, native inputs/buttons), existing HTMX form behavior, SwiftUI controls, SF Symbols, cabinet icon macros, and current color tokens.
- Add small presentation helpers only where the same humanization rule is testable in more than one rendering path.
- Keep diagnostics data and support submission services; remove only their unconditional ordinary-screen rendering.
- Avoid a command palette, saved-filter system, new navigation destinations, new theme engine, third-party component library, or broad cabinet rewrite.
