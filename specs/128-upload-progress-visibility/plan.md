# Implementation Plan: Видимый прогресс загрузки записи

**Branch**: `128-upload-progress-visibility` | **Date**: 2026-07-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/128-upload-progress-visibility/spec.md`

## Summary

Показать per-record прогресс уже существующей отправки в нативной строке
локальной записи. UI переиспользует `DesktopUploadQueueItem.progressFraction`
и существующий `ArtifactCompletenessProfile` для определения измеримого total;
он не добавляет состояние, сетевой запрос, retry или новый custody-owner.
При 100% принятых байтов строка сообщает о проверке/финализации, пока queue item
не станет `uploaded`.

## Technical Context

**Language/Version**: Swift 5.9+ и SwiftUI существующего macOS приложения

**Primary Dependencies**: `TwoBrainRecShared`, существующий
`DesktopUploadQueueItem`, `DesktopUploadCustodyProjection`, XCTest; новых
зависимостей нет

**Storage**: N/A; не добавляются поля, миграции или новый persisted state

**Testing**: focused XCTest в `CaptureControlV5Tests.swift`, source contract
для нативной строки, `swift build`, полный `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature`: изменение user-facing upload /
custody UX затрагивает запись, локальное хранение, accessibility и truthful
degraded states; обязательны clarify, UX checklist, analyze и repository gate

**Release Gate**: `no deploy`: пользователь не просил релиз или production
rollout; deploy и installed-app production evidence остаются отдельным gate

**Target Platform**: macOS native shell на Apple Silicon; configured и local-only
режимы существующего кабинета

**Project Type**: нативное macOS desktop-приложение с server-owned WebView

**Performance Goals**: не добавлять сетевые запросы, таймеры или polling; UI
обновляется только с существующим queue snapshot и не создаёт заметной задержки

**Constraints**: не менять upload protocol, accepted-byte truth, custody,
automatic retry, local purge, deletion, retention, server policy или visible
capture controls; не показывать private content, paths, identifiers или secrets

**Scale/Scope**: максимум три уже видимые локальные строки; per-row progress
только для active `uploading`, без общего HUD, ETA или скорости

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- PASS: capture-first MVP и system-audio-first путь не изменяются; manual Stop,
  visible capture indicator и target-scoped auto-recording не затрагиваются.
- PASS: progress only reflects existing accepted-byte snapshot; no direct
  MediaScribe access, new egress, credential or storage surface is introduced.
- PASS: local custody remains authoritative for upload/retry/deletion/local-purge
  truth; 100% bytes are not presented as `uploaded` before state transition.
- PASS: committed tests/evidence remain metadata-only and contain no audio,
  transcript, private meeting content, local paths or credentials.
- PASS: native SwiftUI is the platform-native implementation and the UI keeps
  text plus accessibility semantics instead of relying on color alone.

## Validation Plan

1. Focused XCTest: `CaptureControlV5Tests` covers active/queued/uploaded summary
   semantics, measured progress, full-byte finalization and safe accessibility
   copy; source contract checks the visible native row and absence of retry UI.
2. macOS build and focused suite from `quickstart.md`.
3. `git diff --check` and metadata-only forbidden-content scan.
4. Full `infra/scripts/ci-local.sh` before closeout; its production RLS probe
   may remain environment-blocked in the no-deploy lane, as documented by the
   repository runner.
5. No `cd-remote.sh` execution: this slice changes a native UX surface only and
   does not claim installed-app or production acceptance.

## Project Structure

### Documentation (this feature)

```text
specs/128-upload-progress-visibility/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/native-upload-progress.md
├── checklists/requirements.md
├── checklists/ux.md
├── checklists/security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/Shared/Tests/CaptureControlV5Tests.swift
apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep the existing local queue row and pure custody
projection as the single source of truth. Add only a small presentation helper
inside the existing shell and extend the existing custody contract tests; do
not create a second queue model, a new native HUD, a server route or a new
shared UI framework.

## Complexity Tracking

No constitution exception or new architectural complexity is required.
