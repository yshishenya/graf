# Implementation Plan: восстановление устойчивой синхронизации записи

## Summary

Исправить ложное объявление capture clock нестабильным, когда callback приходит
позже фактического PTS, и сохранить существующий macOS system-audio-first v5
pipeline. Основной diff должен быть в timeline/source boundary и regression
tests; серверный контракт, MediaScribe dispatch и удалённый routing не меняются.

## Risk and validation lane

Выбран lane: **significant/high-risk capture, timing, storage and upload gate**.
Причина — изменение поведения записи, финализации и eligibility к внешней
передаче. Обязательны полный Spec Kit flow, audio-capture checklist,
metadata-only evidence и `infra/scripts/ci-local.sh`. Deploy, installer и
hardware acceptance в этот slice не входят.

## Constitution and product gates

- Native ScreenCaptureKit system audio и app-owned AVFoundation microphone
  сохраняются.
- Ручной Stop, visible active-recording state, scope consent и Pause/Resume не
  меняются.
- Capture-critical logic остаётся platform-native; новая зависимость не нужна.
- Desktop не получает MediaScribe credentials и не отправляет audio напрямую в
  MediaScribe.
- Неполный package остаётся blocked; deletion/observability policy не меняется.
- Диагностика и committed evidence не содержат raw audio/transcript/private
  meeting content.

## Technical approach

### 1. Устранить ложный clock gate

Файл: `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`.

- Оставить PTS источника authoritative для frame position.
- Нормализовать `.sourcePresentationTime` в comparable internal label без
  вычисления стабильности по `observedHostTimeSeconds`.
- Убрать jitter/latency rejection и требование callback observation.
- Сохранить valid observation как optional metadata; не сдвигать PTS к callback.
- Оставить bounded one-second reorder look-behind: он покрывает заявленный
  500-мс delivery outlier с запасом, но не создаёт unbounded queue.
- Сохранить explicit failures для invalid PTS, incompatible domains, route,
  overflow, gap, late batch, missing source и converter.

### 2. Сохранить timestamp metadata через bounded buffer

Файл: `apps/macos/RecApp/Sources/Capture/RecordingSampleSources.swift`.

- При split большого batch в `readTimestampedBatch` переносить
  `observedHostTimeSeconds` в remainder.
- Не менять frame-based capacity/overflow policy и не добавлять raw-audio store.

### 3. Не превращать host-clock observation в capture data loss

Файл: `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`.

- PTS должен оставаться принимаемым, даже если optional callback observation не
  получена.
- Native callback остаётся bounded и serial; существующий ScreenCaptureKit queue
  drain не ослаблять.
- Не переносить extraction в неограниченную дополнительную очередь.

### 4. Регрессии package/finalization

Файлы:

- `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`
- `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`
- `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`

Добавить проверки для delayed/reordered PTS, missing observation, split metadata,
длительного малого drift, stateful 44.1 kHz conversion, stop drain и полного
artifact set. Существующие fail-closed tests для route/overflow/missing source
сохранить.

### 5. Release/readiness documentation

- Обновить `CHANGELOG.md` в `[Unreleased]` русской записью без приватного
  содержимого.
- После анализа синхронизировать executable tasks с GitHub issues в canonical
  Russian format; не дублировать incident #4460.

## Files and contracts

### Existing files to change

- `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`
- `apps/macos/RecApp/Sources/Capture/RecordingSampleSources.swift`
- `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
- `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`
- `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`
- `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`
- `CHANGELOG.md`

### New feature artifacts

- `specs/126-recording-clock-recovery/spec.md`
- `specs/126-recording-clock-recovery/research.md`
- `specs/126-recording-clock-recovery/data-model.md`
- `specs/126-recording-clock-recovery/contracts/timeline-and-finalization.md`
- `specs/126-recording-clock-recovery/quickstart.md`
- `specs/126-recording-clock-recovery/checklists/requirements.md`
- `specs/126-recording-clock-recovery/checklists/audio-capture.md`
- `specs/126-recording-clock-recovery/tasks.md`

## Test strategy

1. Сначала focused `swift test` для timeline, package и native capture service.
2. Затем весь `swift test` из `apps/macos`.
3. Затем canonical `infra/scripts/ci-local.sh`.
4. Review `git diff --check`, `git status`, changed-file scope и metadata-only
   evidence.
5. Hardware run T063 не запускать автоматически и не выдавать synthetic result
   за hardware acceptance.

## Rollback and compatibility

Изменение локальное, schema migration не требуется. При регрессии можно вернуть
изменённые Swift-файлы к предыдущему branch revision без изменения server data;
feature docs и CHANGELOG должны оставаться согласованными с фактически
включённым кодом. Implementation commit возможен только после отдельного
пользовательского approval.
