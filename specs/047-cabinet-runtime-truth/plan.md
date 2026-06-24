# Implementation Plan: Cabinet Runtime Truth

**Branch**: `047-cabinet-runtime-truth` | **Date**: 2026-06-24 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/047-cabinet-runtime-truth/spec.md`

## Summary

Make the macOS cabinet shell truthful by separating static cabinet configuration
from runtime cabinet health/auth state. The embedded WebKit surface already
detects HTTP and navigation failures; this slice lifts that state into the
native shell, classifies login/sign-up page loads as auth-required rather than
ready, adds regression tests, and rechecks web/desktop cabinet parity.

## Technical Context

**Language/Version**: Swift 6 for the macOS app and XCTest; Python 3.13 for
server/web cabinet checks.

**Primary Dependencies**: SwiftUI, WebKit, FastAPI server-owned cabinet,
server-rendered HTML review surface, Playwright/Chrome runtime checks when
browser validation is needed.

**Storage**: No new persisted storage. Runtime state is local UI state only.

**Testing**: `swift test --package-path apps/macos`; focused macOS cabinet
tests; focused server/web cabinet tests; browser runtime checks for visible web
and embedded cabinet states; production health curl checks.

**Target Platform**: macOS desktop app plus existing web cabinet.

**Project Type**: Native macOS desktop app with embedded server-owned web
cabinet.

**Performance Goals**:

- Runtime state updates on the same navigation events that already drive the
  embedded cabinet.
- No extra server polling is introduced in this slice.
- Desktop shell status never waits on a long background process before showing
  offline/auth-required navigation failures.

**Constraints**:

- Desktop still never sends audio directly to MediaScribe and never stores
  provider credentials.
- Local recording controls remain native and visible outside the WebKit surface.
- Status and evidence remain metadata-only.
- UI copy stays Russian and product-facing; technical route names stay out of
  visible user copy.
- This slice may not weaken access, deletion, upload, processing, or playback
  policy.

**Scale/Scope**: One owner MVP desktop/web review loop, configured cabinet URL,
embedded meeting list/detail/login routes, and failure states that can happen
during server restart or session expiry.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Plan Response |
|---|---|---|
| Capture-first MVP integrity | PASS | Does not change capture, routing, permissions, or recording package creation. |
| Visible consent and one-action stop | PASS | Preserves native Record/Stop and active recording safety in every cabinet state. |
| Data boundary and secret discipline | PASS | Desktop remains server-only; no dependency credentials or content-bearing evidence added. |
| Deletion truth and lifecycle accounting | PASS | Does not alter deletion; cabinet parity checks must preserve existing unavailable/deleted states. |
| Spec-driven delivery | PASS | Spec, plan, quickstart, checklists, tasks, analyze, implementation, and evidence are included. |
| Metadata-only diagnostics/evidence | PASS | Validation records only state names, counts, routes classes, and command outcomes. |

No constitution violation is required.

## Project Structure

### Documentation (this feature)

```text
specs/047-cabinet-runtime-truth/
|-- spec.md
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- checklists/
|   |-- requirements.md
|   `-- ux.md
|-- contracts/
|   `-- cabinet-runtime-state-contract.md
|-- evidence/
|   `-- validation-log.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/macos/
|-- RecApp/App/TwoBrainRecApp.swift
|-- RecApp/Sources/Cabinet/
|   |-- DesktopCabinetWorkspaceView.swift
|   |-- DesktopMeetingShellView.swift
|   `-- EmbeddedCabinetWebView.swift
`-- Shared/Tests/
    `-- DesktopCabinetWorkspaceTests.swift

apps/server/
|-- src/twobrain_rec_server/cabinet/
|   |-- web.py
|   `-- view_models.py
`-- tests/
    |-- integration/
    `-- unit/
```

**Structure Decision**: Keep state truth in the existing desktop cabinet
components. Do not add a new service, background health poller, database table,
or web route for this slice.

## Complexity Tracking

No constitution violations are required.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

1. Treat cabinet configuration as static routing information only.
2. Lift embedded cabinet runtime state to the native shell via a SwiftUI
   binding.
3. Classify finished routes by route kind so login/sign-up pages do not become
   ready.
4. Keep web cabinet validation fixture-backed and metadata-safe.

## Phase 1 Design Decisions

Design artifacts:

- [data-model.md](./data-model.md): cabinet configuration, runtime state,
  shell presentation, and parity cases.
- [contracts/cabinet-runtime-state-contract.md](./contracts/cabinet-runtime-state-contract.md):
  runtime state mapping and UI truth contract.
- [quickstart.md](./quickstart.md): focused validation commands and expected
  outcomes.

## Post-Design Constitution Check

| Gate | Status | Design Response |
|---|---|---|
| Capture-first MVP integrity | PASS | No capture path changes; active recording safety is tested across cabinet states. |
| Visible consent and one-action stop | PASS | Native shell invariant remains required for every cabinet runtime state. |
| Data boundary and secret discipline | PASS | No content, credentials, signed URLs, or private paths added to status/evidence. |
| Deletion truth and lifecycle accounting | PASS | Web/embedded parity checks preserve existing review state truth. |
| Spec-driven delivery | PASS | Artifacts map to tasks and validation gates. |
| Metadata-only diagnostics/evidence | PASS | Quickstart forbids private content in evidence and commands. |
