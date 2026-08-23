# Implementation Plan: Надёжность автоматической записи

**Branch**: `193-automatic-recording-reliability` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/193-automatic-recording-reliability/spec.md`

## Summary

Исправить весь существующий detector-assisted путь без новой подсистемы: сохранить
независимое состояние AudioHAL и Control Center, разрешать prompt/countdown только
после того же current policy/ack gate, считать trigger обработанным только после
принятия consumer-ом, восстанавливать системный observer со snapshot после startup,
wake и неожиданного завершения, а WebKit auth cookie синхронизировать в native
storage как авторитетный same-origin snapshot. Все решения и lifecycle переходы
получают bounded metadata-only диагностику; server contract и production defaults
не меняются.

## Technical Context

**Language/Version**: Swift 5.9+ / SwiftUI, AppKit, WebKit on macOS

**Primary Dependencies**: существующие Foundation, SwiftUI, AppKit, WebKit и
Swift Concurrency; новые зависимости не добавляются

**Storage**: существующие `HTTPCookieStorage` и atomic JSON registry/settings
cache; схема БД не меняется

**Testing**: Swift Package XCTest; repository CI через
`infra/scripts/ci-local.sh --fast` и `infra/scripts/ci-local.sh --full`

**Risk / Validation Lane**: high-risk-feature — меняются capture start/stop,
auth/session, diagnostics и lifecycle системного observer; mandatory clarify,
checklist, analyze и полный repository gate

**Release Gate**: no deploy — production policy, `/Applications/GRAF.app`,
Developer ID package, deployment и release не меняются без отдельного одобрения

**Target Platform**: текущий нативный GRAF для macOS

**Project Type**: monorepo macOS desktop app + неизменяемый в этой feature server

**Performance Goals**: временный blocker переоценивается не позднее чем через
2 секунды; неожиданно завершившийся observer или wake восстанавливает наблюдение
не позднее 5 секунд; одновременно работает не более одного live observer

**Constraints**: system-audio-first capture; только verified native targets;
fail-closed policy/auth; ручные Record/Stop сохраняются; никаких raw audio,
meeting content, transcript или session values в логах/evidence

**Scale/Scope**: один desktop process, текущий target registry и два независимых
platform evidence source (`audioHAL`, `sensorIndicator`)

## Constitution Check

### Before research

- **PASS — Human authority and transparency**: countdown, immediate Start, Skip,
  per-target choice, visible capture indicator и one-action Stop сохраняются.
- **PASS — Capture safety**: prompt и автоматический start проходят один current
  policy/ack/readiness gate; временный отказ не превращается в скрытое разрешение.
- **PASS — Source truth**: встреча считается активной пока активен хотя бы один
  независимый platform source; auto-stop привязан к реальной end boundary.
- **PASS — Authentication**: WebKit/native session reconciliation удаляет stale
  credentials и остаётся внутри существующего dedicated auth-header boundary.
- **PASS — Privacy**: новые события содержат только source, bundle ID, state,
  stable reason/result и timestamps; cookie values и meeting content запрещены.
- **PASS — Native-first/minimal architecture**: используются `/usr/bin/log`,
  Foundation `Process`, WebKit cookie store и текущий detector/capture path.
- **PASS — Fail closed**: отсутствие auth, current policy, acknowledgement,
  trustworthy snapshot или readiness не запускает assisted capture.

### After design

- **PASS — Minimal state**: существующий tracked candidate расширяется set-ом
  source; отдельный engine, endpoint, daemon или database table не создаётся.
- **PASS — Lifecycle ownership**: один supervisor владеет snapshot/live child,
  restart delay и deliberate stop, исключая параллельные streams.
- **PASS — Trigger semantics**: detector предлагает outcome, а consumer отдельно
  подтверждает handled/terminal состояние; retryable отказ остаётся eligible.
- **PASS — Session boundary**: web store является авторитетным snapshot только
  для настроенного same-origin cookie; остальные cookies не затрагиваются.
- **PASS — Evidence**: существующий `AppLog.writeRaw` переиспользуется с
  bounded metadata-only details и без новой telemetry subsystem.

## Validation Plan

1. Parser/log-stream tests фиксируют source identity, Sensor Indicator diff,
   атомарный bounded startup snapshot, timeout fallback и
   controlled/unexpected process termination.
2. Detector tests перебирают порядок двух sources, duplicate transitions,
   all-sources end, retryable consumer rejection, handled/Skip/manual-stop
   suppression, reset и следующий candidate того же bundle.
3. App policy tests фиксируют запрет countdown до valid policy/ack и current
   повторную проверку перед button/timeout/saved-target start.
4. Cookie tests покрывают stale replacement, logout removal, expiry, secure,
   domain/path matching и deterministic selection.
5. Запустить focused Swift suites, затем `infra/scripts/ci-local.sh --fast` и
   `infra/scripts/ci-local.sh --full`.
6. Собрать отдельный GRAF Dev через
   `sh apps/macos/Scripts/build-local-app.sh --open`; не заменять production app.
7. В dev runtime завершить child `/usr/bin/log stream` и доказать ровно один
   восстановленный observer в пределах 5 секунд; использовать только synthetic
   metadata и не записывать приватную встречу.

## Project Structure

### Documentation (this feature)

```text
specs/193-automatic-recording-reliability/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── automatic-recording-runtime.md
├── checklists/
│   ├── requirements.md
│   └── capture-reliability.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/Shared/Sources/MeetingDetection/
└── MacOSAudioOwnershipParser.swift

apps/macos/RecApp/
├── App/TwoBrainRecApp.swift
└── Sources/
    ├── Cabinet/DesktopCabinetSessionBridge.swift
    ├── MeetingDetection/
    │   ├── MacOSAudioOwnershipLogStream.swift
    │   └── MacOSMeetingActivityDetector.swift
    └── Upload/DesktopUploadClient.swift

apps/macos/Shared/Tests/
├── DesktopUploadClientTests.swift
├── MacOSAudioOwnershipParserTests.swift
└── MeetingDetectionPolicyTests.swift
```

**Structure Decision**: изменить существующие shared parser/model, detector,
observer, app orchestration и same-origin cookie seams. Переиспользовать текущие
test targets и `AppLog`; новых модулей и runtime dependencies не создавать.

## Complexity Tracking

Constitution violations отсутствуют.
