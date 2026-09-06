# Implementation Plan: Надёжный переход локальной записи в кабинет

**Branch**: `231-local-recording-handoff` | **Date**: 2026-09-02 | **Spec**: [spec.md](spec.md)

## Summary

Исправить единый desktop-embedded путь локальной записи: безопасно передавать UTF-8 строки в WebView, дать строке нативное воспроизведение и штатную пиктограмму, показывать фактическую сохранённую длительность, мигрировать неверную локальную классификацию и заменять локальную строку серверной только после подтверждённого handoff. На общей AEC3-границе ограничить конечные пики до −1…1, сохранив fail-closed для нечисловых кадров, неверного размера и настоящих ошибок процессора. Новые API, таблицы и зависимости не нужны.

## Technical Context

**Language/Version**: Swift 5.9+/SwiftPM, JavaScript ES2022, Markdown

**Primary Dependencies**: AppKit, WebKit, AVFoundation, существующий `GrafAEC3`, существующий server-owned cabinet

**Storage**: Локальные v5 recording directories и `upload-queue.json`; PostgreSQL schema не меняется

**Testing**: XCTest, статические WebView/JavaScript contracts, `node --check`, feature quickstart, `infra/scripts/ci-local.sh --fast`

**Risk / Validation Lane**: high-risk-feature — затронуты capture, локальное удаление, диагностика и основной пользовательский путь

**Release Gate**: no deploy — commit/release/deploy и установленная production app требуют отдельного согласования

**Target Platform**: macOS desktop app и встроенный server-owned cabinet

**Project Type**: SwiftUI/AppKit desktop app со встроенным WebKit cabinet и Python server UI assets

**Performance Goals**: AEC остаётся в существующем 10-ms frame budget; WebView update остаётся одним bounded payload

**Constraints**: system-audio-first; один обязательный AEC3; raw microphone не сохраняется; локальные пути не выходят в WebView; private content не попадает в evidence

**Scale/Scope**: один локальный пользователь, одна очередь на channel, существующие и новые v5 packages; без backend migration

## Constitution Check

- PASS — ручные Record/Stop и видимый индикатор не меняются.
- PASS — MediaScribe credentials и приватные пути не передаются desktop/WebView.
- PASS — raw microphone fallback не добавляется; сохраняется только уже очищенный prefix.
- PASS — удаление ограничено корнем локальных записей и пользовательским подтверждением.
- PASS — локальная и серверная custody truth не смешиваются в одной DOM-строке.
- PASS — accessibility включает доступное основное действие, keyboard activation и понятные labels.
- PASS — никаких новых зависимостей, API, таблиц или speculative abstractions.

Post-design re-check: те же границы закреплены в [data-model.md](data-model.md), [local-recording-row.md](contracts/local-recording-row.md) и [quickstart.md](quickstart.md); нарушений нет.

## Validation Plan

1. RED/GREEN focused XCTest для AEC clamp, NaN/size failures, точного capture code, фактической длительности, queue migration и bridge UTF-8/action policy.
2. `node --check` и DOM/source contract для локальной строки, пиктограммы, клавиатуры и отсутствия server-row grafting.
3. Feature quickstart: local failure/play/delete, queued/uploading, confirmed server replacement и свежая успешная запись на dev app с synthetic/non-private evidence.
4. `infra/scripts/ci-local.sh --fast` перед готовностью ветки. Full CI, signing, notarization, release и deploy отложены до одобренного release candidate.

## Project Structure

### Documentation (this feature)

```text
specs/231-local-recording-handoff/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/local-recording-row.md
├── checklists/requirements.md
├── checklists/capture-ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/Sources/Capture/
├── RecordingEchoProcessor.swift
├── RecordingAudioTimeline.swift
└── V5LocalRecordingWriter.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift
apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift
apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/Shared/Tests/
├── RecordingEchoProcessorTests.swift
├── RecordingAudioTimelineTests.swift
├── DesktopUploadQueueV5Tests.swift
└── DesktopMeetingShellWebViewBoundaryTests.swift
apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js
```

**Structure Decision**: Изменение остаётся в существующих shared capture/queue/bridge точках и server-owned list renderer; отдельный модуль или dependency не создаётся.

## Complexity Tracking

Нет отклонений от constitution или Ponytail ladder.
