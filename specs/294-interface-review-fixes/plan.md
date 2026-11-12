# Implementation Plan: Исправления после ревью интерфейса

**Branch**: `294-interface-review-fixes` | **Date**: 2026-11-12 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/294-interface-review-fixes/spec.md`

## Summary

Упростить presentation-слой, убрать мёртвые поля и дубли строк, исправить подтверждённые дефекты управления записью, микрофоном, окном, сменой аккаунта и часовым поясом. После полного набора проверок выпустить CalVer-релиз и выкатить сервер в production.

## Technical Context

**Language/Version**: Swift 6.0.3 (CI) / macOS 14+, Python 3.12, existing web cabinet without a separate frontend toolchain.

**Primary Dependencies**: SwiftUI, AppKit, WebKit, Sparkle 2.9.4, XCTest, pytest, existing release scripts.

**Storage**: local upload queue and recording manifests in Application Support; server PostgreSQL/MinIO unchanged.

**Testing**: `swift build`, focused XCTest, full `apps/macos/Scripts/run-swift-tests.sh`, `ContractValidation`, `infra/scripts/ci-local.sh --fast`, GitHub `release-full`, notarization/Gatekeeper/Sparkle, production health.

**Risk / Validation Lane**: high-risk-feature. Capture, microphone, privacy of account switch, window restore, public release.

**Release Gate**: `release-full` on frozen candidate; Developer ID; notarization; staple; Gatekeeper; Sparkle; `cd-remote.sh --dry-run`; production execute only with explicit operator approval.

**Target Platform**: macOS 14+ Apple Silicon; self-hosted server `https://rec.2brain.pro`.

**Project Type**: desktop-app + web-service monorepo.

**Constraints**: no new frontend toolchain; no weakening capture/privacy/deletion gates; preserve existing local buffer and analytics scaffold; no manual app copies.

**Scale/Scope**: macOS app shell, capture controls, cabinet navigation/settings, account-switch bridge, menu bar, release/deploy tooling.

## Constitution Check

- **I. Capture-First MVP Integrity**: PASS. Capture semantics unchanged; only action visibility and degraded handling corrected.
- **II. Visible Consent And User Control**: PASS. Stop remains visible/available; one predicate makes it consistent.
- **III. Plaintext Observability**: PASS. Logs remain bounded; flush added at termination.
- **IV. Deletion Truth**: PASS. Deletion copy and lifecycle untouched.
- **V. Public macOS Distribution**: PASS. Release remains Developer ID/notarization/Sparkle only.
- **VI. Spec-Driven Delivery**: PASS. This feature follows spec/plan/tasks and validation gates.
- **VII. Reference-Fidelity**: PASS. No visual redesign; only behavior and consistency fixes.

## Validation Plan

- Focused XCTest for shortcuts, stop visibility, microphone fallback/disconnect, preferences, tray state, timezone rows, settings sections, dead-code absence.
- Full `apps/macos/Scripts/run-swift-tests.sh`.
- `swift run --package-path apps/macos ContractValidation`.
- `infra/scripts/ci-local.sh --fast`.
- PR checks: `governance-fast`, `macos-pr`, `pr-metadata`.
- `release-full` on frozen candidate.
- macOS notarization/staple/Gatekeeper/Sparkle; live appcast.
- Server deploy `deploy_result=pass`; public health; runtime SHA.
- Record evidence in `specs/294-interface-review-fixes/validation.md` and `validation/release.md`.

## Project Structure

```text
specs/294-interface-review-fixes/
├── spec.md
├── plan.md
├── tasks.md
├── validation.md
└── checklists/
    └── requirements.md

apps/macos/RecApp/Sources/
├── AppShell/ContentView.swift
├── AppShell/AppLifecycleDelegate.swift
├── AppShell/InterfacePreferences.swift
├── AppShell/AppLog.swift
├── Cabinet/DesktopCabinetWorkspaceView.swift
├── Cabinet/WorkspaceZoom.swift
├── Cabinet/DesktopCabinetSessionBridge.swift
├── Capture/CaptureStatusPresentation.swift
├── Capture/CaptureStatusItem.swift
├── Capture/LocalRecordingPresentation.swift
├── Capture/RecordingBlockerPresentation.swift
├── Capture/MicrophoneCaptureService.swift
├── Calendar/CalendarTray.swift
└── MeetingDetection/MeetingDetectionSettingsView.swift

apps/macos/Shared/Sources/
├── Models/SystemAudioCaptureCoreModels.swift
└── UserTime.swift

changes/unreleased/F294.yaml
```

**Structure Decision**: сохраняем существующий single-package target и текущие файлы; удаляем мёртвые типы/поля вместо добавления новых абстракций.

## Complexity Tracking

| Change | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Один предикат Stop/Pause | Устраняет расхождение панели, меню и accessibility | Оставлять несколько switch-ей — уже привело к расхождению |
| Удаление мёртвых presentation-состояний | Упрощает код и убирает второй источник правды | Достраивать UI под неиспользуемые состояния — усложнение без потребителя |
| Асинхронная очистка storage | Приватность смены аккаунта | Полагаться на порядок WebKit — гонка |
| Общий shortcut-модель навигации | Тестируемость и отсутствие конфликтов | Дублировать строки в view и меню — конфликт не ловится тестом |
