# Implementation Plan: Источник системного звука в индикаторе записи

**Branch**: `codex/156-recording-source-indicator` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/156-recording-source-indicator/spec.md`

## Summary

Показать в существующем верхнем индикаторе записи проверенное имя источника текущей capture-сессии. Для auto-record использовать уже сохранённое имя целевого приложения; для ручного режима — честное «Системный звук»; при отсутствии значения — «Источник не определён». Меняется только presentation layer индикатора и его accessibility-контракт.

## Technical Context

**Language/Version**: Swift 6 package, macOS 14+

**Primary Dependencies**: SwiftUI, existing `TwoBrainRecShared` models, XCTest

**Storage**: N/A; existing in-memory `CaptureSession.triggerEvidence` is read only

**Testing**: focused XCTest plus macOS package build and repository fast lane

**Risk / Validation Lane**: `high-risk-feature`; capture indicator and accessibility are protected user-facing recording controls, even though the implementation does not alter capture behavior

**Release Gate**: `no deploy`; no production or public macOS release is requested

**Target Platform**: native GRAF macOS desktop app

**Project Type**: desktop app

**Performance Goals**: no added work on audio callbacks or capture start; indicator remains responsive with existing layout

**Constraints**: system-audio-first MVP, visible indicator and one-action Stop remain intact, no process polling, no new dependencies, no audio/telemetry egress

**Scale/Scope**: one capture surface, one shared label/identifier contract, focused tests and changelog entry

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- Capture-First MVP Integrity: PASS — no audio route, source selection, permission, or ScreenCaptureKit behavior changes.
- Visible Consent And User Control: PASS — existing indicator, status hierarchy, pause/resume and one-action Stop remain visible and unchanged.
- Privacy and secret discipline: PASS — only an already approved local display name is shown; no new collection, network call, raw audio, transcript, or secret is introduced.
- Clean-room UX/accessibility: PASS — source is a compact native row with explicit neutral fallbacks, truncation-safe accessibility text, and no animation dependency.
- Spec-Driven Delivery: PASS — clarification completed with no unresolved questions; design artifacts and high-risk checklists are required before implementation.

## Validation Plan

1. Run `swift test --package-path apps/macos --filter CaptureIndicatorTests` for source mapping, lifecycle visibility, fallback and accessibility text.
2. Run `swift test --package-path apps/macos --filter AppControlAccessibilityTests` for source-level accessibility contracts.
3. Run `apps/macos/Scripts/build-local-app.sh` or the focused package build on a macOS host.
4. Run `infra/scripts/ci-local.sh --fast` before closeout because the change affects a shared user-facing capture surface.
5. No deploy, release preparation, notarization, or CD command is in scope.

## Project Structure

### Documentation (this feature)

```text
specs/156-recording-source-indicator/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── recording-source-indicator.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift
apps/macos/Shared/Sources/Models/SystemAudioCaptureCoreModels.swift
apps/macos/Shared/Tests/CaptureIndicatorTests.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
CHANGELOG.md
```

**Structure Decision**: Reuse the existing SwiftUI capture status component and shared labels/identifiers. No new model, service, dependency, persisted field, capture callback, or process observer is needed.

## Complexity Tracking

No constitution violations. Ponytail ceiling: source attribution is limited to the approved session target and does not attempt per-process attribution of display-wide system audio; add a dedicated attribution design only if product later requires it and can define a truthful macOS contract.
