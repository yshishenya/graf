# Implementation Plan: Авторизация и доказательства автозаписи

**Branch**: `145-assisted-autostart-hardening` | **Date**: 2026-08-12 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/145-assisted-autostart-hardening/spec.md`

## Summary

Сохранить UX Feature 124, включая восьмисекундный countdown и старт по timeout,
но поставить общий detector-assisted start path за реальной workspace policy,
подтверждением её актуальной версии и фактической проверкой storage/capture gates.
Политика доставляется внутри уже существующего аутентифицированного target-registry
response и включается только fail-closed runtime-конфигурацией для одного внутреннего
workspace. Клиент хранит acknowledgement конкретного opaque policy reference,
повторно проверяет все gates перед стартом и пишет точную metadata-only причину.

## Technical Context

**Language/Version**: Swift 5.9+/SwiftUI on macOS; Python 3.12/FastAPI

**Primary Dependencies**: существующие Foundation, AppKit, SwiftUI, CryptoKit,
FastAPI, Pydantic; новые зависимости не добавляются

**Storage**: существующие atomic JSON settings/cache под Application Support;
PostgreSQL schema не меняется

**Testing**: Swift Package XCTest; pytest unit/contract/integration; repository
local CI via `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: high-risk-feature — меняется автоматический запуск
capture, consent attribution и fail-closed readiness

**Release Gate**: no deploy — реализация и локальная validation; production
configuration/deploy требуют отдельного подтверждения пользователя

**Target Platform**: macOS desktop app plus Linux-hosted GRAF API

**Project Type**: monorepo desktop app + web service

**Performance Goals**: countdown не стартует до 8.000 s; решение выполняется один
раз; policy добавляется к существующему registry request без нового round trip;
storage probe не читает содержимое файлов

**Constraints**: system-audio-first native capture; offline только до policy expiry;
manual Record/Stop не зависит от assisted acknowledgement; metadata-only evidence;
unknown/browser/manual-only targets не расширяются

**Scale/Scope**: один явно настроенный внутренний workspace; существующий native
target registry; внешний/customer rollout вне feature

## Constitution Check

### Before research

- **PASS — Human authority and transparency**: countdown, Skip, visible indicator
  и one-action Stop сохраняются; первая актуальная policy version требует явного
  acknowledgement.
- **PASS — Capture safety**: реальный policy snapshot, permissions, storage,
  target activity, active session, indicator и Stop повторно проверяются в общем
  start path.
- **PASS — Privacy and evidence**: contract содержит только opaque references,
  версии, timestamps, target IDs и reason codes; meeting content не передаётся.
- **PASS — Native-first**: новый capture engine или virtual driver не вводится.
- **PASS — Fail closed**: committed defaults выключены; отсутствующая,
  несовместимая или просроченная policy блокирует assisted start.
- **PASS — Scope**: только текущий внутренний workspace; внешний rollout отдельно.

### After design

- **PASS — Minimal architecture**: policy добавляется к существующему
  authenticated registry response; отдельные endpoint, table и admin service не
  нужны.
- **PASS — Persistence**: acknowledgement сохраняется atomic JSON вместе с
  существующими meeting-detection settings и привязан к opaque policy reference.
- **PASS — Audit truth**: `prompt_button`, `prompt_timeout` и
  `saved_target_policy` проходят через один decision object и capture evidence.
- **PASS — Accessibility**: remaining seconds доступны как видимый текст,
  accessibility label/value и не зависят от цветного progress.

## Validation Plan

1. Python unit/contract tests проверяют fail-closed config, workspace scoping,
   expiry, response schema, ETag и отсутствие опасных полей.
2. Swift model/store tests проверяют decoding, cache, policy expiry и exact-version
   acknowledgement migration.
3. Swift behavioral tests с управляемым временем проверяют 7.999/8.000 s,
   single resolution, Start/Skip/disappearance/revocation races и три reason codes.
4. Capture tests проверяют scope approval/initiator, policy snapshot evidence,
   storage blocker и повторную проверку target activity.
5. Accessibility contract и ручной smoke проверяют видимые секунды, VoiceOver,
   indicator и one-action Stop.
6. Запустить `infra/scripts/ci-local.sh`. `cd-remote.sh` и deploy не выполнять в
   этой feature без отдельного подтверждения.

## Project Structure

### Documentation (this feature)

```text
specs/145-assisted-autostart-hardening/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── assisted-auto-start-policy.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/src/twobrain_rec_server/
├── api/meeting_detection.py
├── api/schemas.py
└── config.py

apps/server/tests/
├── contract/test_meeting_detection_api_contract.py
└── unit/test_meeting_detection_registry.py

apps/macos/Shared/Sources/MeetingDetection/
├── MeetingDetectionModels.swift
├── MeetingDetectionPolicy.swift
└── MeetingTargetRegistry.swift

apps/macos/RecApp/
├── App/TwoBrainRecApp.swift
└── Sources/
    ├── Buffering/LocalBufferService.swift
    ├── Capture/CaptureSessionController.swift
    ├── Capture/CaptureScopeApprovalService.swift
    └── MeetingDetection/
        ├── MacOSMeetingActivityDetector.swift
        ├── MeetingDetectionSettingsStore.swift
        └── MeetingDetectionSettingsView.swift

apps/macos/Shared/Tests/
├── MeetingTargetRegistryTests.swift
├── MeetingDetectionPolicyTests.swift
├── CaptureControlV5Tests.swift
└── SystemAudioPermissionUXTests.swift

infra/
├── docker-compose.yml
└── env/rec.production.env.example
```

**Structure Decision**: изменить существующие server registry и macOS
meeting-detection/capture seams. Новый модуль, БД-таблица, endpoint и runtime
dependency не создаются.

## Complexity Tracking

Constitution violations отсутствуют.
