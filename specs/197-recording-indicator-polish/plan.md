# Implementation Plan: Деликатный индикатор источника записи

**Branch**: `197-recording-indicator-polish` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/197-recording-indicator-polish/spec.md`

## Summary

В существующем верхнем `RecordingTitlebarHUD` нужно показать подтверждённое имя
источника текущей сессии как тихую вторичную подпись внутри единственной внешней
плашки. Источник уже нормализуется в `CaptureStatusItem`; новая правка переносит
его presentation из боковой панели в верхний HUD, не меняя capture-путь,
размер/доступность Pause/Resume/Stop или данные сессии.

## Technical Context

**Language/Version**: Swift 6 package, macOS 14+

**Primary Dependencies**: SwiftUI, existing `TwoBrainRecShared` models, XCTest

**Storage**: N/A; read-only `CaptureSession.triggerEvidence`

**Testing**: focused XCTest, macOS package build, repository fast lane

**Risk / Validation Lane**: `high-risk-feature` within an active Spec Kit slice;
the change is presentation-only but touches the persistent recording indicator,
accessibility, and visible Stop control.

**Release Gate**: implementation work was planned without deploy; the owner
explicitly extended this closeout to commit, PR, CalVer release and production
deploy. Public macOS distribution still requires the Developer ID gates below.

**Target Platform**: native GRAF macOS desktop app

**Project Type**: desktop app

**Performance Goals**: no work on audio callbacks, no process polling, no layout
animation dependency, and no loss of responsive existing controls.

**Constraints**: system-audio-first MVP, one persistent visible indicator, truthful
source attribution, one-action Stop, no new dependency or network call, and no
second source surface in the active shell.

**Scale/Scope**: one native titlebar HUD, existing source normalization helpers,
shared accessibility identifiers/labels, focused tests, and changelog.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-first MVP integrity: **PASS** — no audio route, permission,
  ScreenCaptureKit, lifecycle, or session mutation changes.
- Visible user control: **PASS** — the existing upper indicator and one-action
  Stop remain present; Pause/Resume remain separate controls.
- Privacy and truthfulness: **PASS** — only existing approved session evidence is
  presented; no app polling, raw audio, transcript, telemetry, or egress is added.
- Clean-room UX/accessibility: **PASS** — one outer capsule, no clickable source
  badge, single-line truncation, full VoiceOver/help text, and no motion dependency.
- Ponytail ceiling: **PASS** — reuse `sourceDisplayName` and existing tokens;
  no new view abstraction or data model is needed.

## Validation Plan

1. Run the focused `CaptureIndicatorTests` and `AppControlAccessibilityTests`.
2. Run the `quickstart.md` macOS package build and metadata-only visual smoke.
3. Run `infra/scripts/ci-local.sh --fast` because a shared capture UX surface
   and accessibility contract changed.
4. Inspect the attached recording-state screenshot and the built active/paused/
   degraded/narrow states; reject any second background, wrap, or Stop movement.
5. Do not run deploy, release preparation, notarization, Sparkle, or appcast
   checks: no production artifact is requested.

## Project Structure

### Documentation (this feature)

```text
specs/197-recording-indicator-polish/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recording-indicator-polish.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/Shared/Tests/CaptureIndicatorTests.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
CHANGELOG.md
```

**Structure Decision**: Reuse the existing SwiftUI titlebar HUD and the existing
session-source normalization. The top HUD owns the active source presentation;
the sidebar keeps the status/actions surface without repeating the source row.
The shared labels and identifier remain the single accessibility contract.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | N/A | No new project, dependency, model, or service is introduced. |
