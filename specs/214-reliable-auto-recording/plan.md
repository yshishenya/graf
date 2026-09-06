# Implementation Plan: Надёжный полный цикл автоматической записи

**Branch**: `codex/214-reliable-auto-recording` | **Date**: 2026-08-31 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from
`/specs/214-reliable-auto-recording/spec.md`

## Summary

Сделать надёжным один существующий путь автоматической записи без параллельной
архитектуры. Локальная карта `Всегда / Спрашивать / Никогда` становится
единственным пользовательским источником решения; устаревшие глобальные поля и
серверное разрешение удаляются после совместимого клиентского шага. Требование
остановки сохраняется даже во время запуска, а wake/restart и десятиминутная
страховка сверяют активную detector-запись с текущей встречей.

Текущий writer получает ранний активный manifest и не реже чем раз в 10 секунд
закрепляет WAV на диске. Существующий recovery path восстанавливает незавершённую
папку либо помечает её как `Запись повреждена`. Та же существующая upload queue
получает состояние сохранения и ручное действие `Отправить`; её строки
передаются в существующий встроенный список встреч и после успеха объединяются
с серверной строкой по устойчивой личности.

## Technical Context

**Language/Version**: Swift 6.0 / SwiftUI / AppKit / WebKit on macOS 14+;
Python 3.13+ / FastAPI / Pydantic on server; plain browser JavaScript

**Primary Dependencies**: existing Foundation, AVFoundation, Swift Concurrency,
Network, WebKit, FastAPI and Pydantic; no new package or runtime dependency

**Storage**: existing atomic JSON meeting settings, target-registry cache,
`LocalRecordingManifest` and media files, existing atomic JSON upload queue;
no database migration and no new local database

**Testing**: Swift Package XCTest, pytest contract/unit tests, source-contract
checks, `node --check`, synthetic desktop runtime checks, repository fast/full
gates

**Risk / Validation Lane**: high-risk-feature — capture start/stop, local audio
durability, recovery, upload retry, data lifecycle and high-risk user states;
mandatory constitution, clarify, checklist, tasks and analyze

**Release Gate**: no deploy in planning/implementation by default. The rollout
requires a separately approved notarized client release first and a later
server deployment after the compatibility gate. One full CI run is required on
the exact release candidate before either release.

**Target Platform**: native GRAF desktop app for macOS and the existing GRAF
server registry endpoint/common cabinet list

**Project Type**: monorepo desktop application plus server-rendered embedded web
cabinet and API service

**Performance Goals**: prompt resolves at 8 seconds; detector stop intent is
accepted immediately and completed once capture leaves startup; active WAV is
durably synchronized at intervals no longer than 10 seconds; common-list state
updates within 1 second of queue change; upload progress remains bounded by the
existing observer cadence

**Constraints**: system-audio-first; verified targets only; one active capture;
visible indicator and one-action Stop never removed; 10-minute safety stop;
maximum 10-second recoverable tail loss; offline local settings and baseline
registry; metadata-only diagnostics/evidence; no second queue, service, database
or meeting list

**Scale/Scope**: one desktop process, one active capture, current verified
native registry (tens of targets), existing local recording directories and
upload queue; client-first/server-second rollout

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

### Before research

- **PASS — Capture-first integrity**: early manifest, periodic WAV durability,
  bounded recovery and stop-race handling strengthen the canonical local path;
  no routing or alternate capture engine is introduced.
- **PASS — Visible consent and user control**: the exact three local states,
  eight-second prompt, remembrance mapping, visible indicator, manual Record and
  one-action Stop match Constitution 6.0.0.
- **PASS — Client ownership**: no server permission or acknowledgement owns the
  per-app choice; general workspace recording/consent restrictions remain.
- **PASS — Storage truth**: every discovered local folder becomes sendable,
  degraded or damaged; useful audio is not hidden because a derived artifact or
  manifest finalization failed.
- **PASS — Deletion truth**: damaged local records reuse the existing explicit
  local delete path and do not claim server deletion.
- **PASS — Privacy**: committed evidence, recovery diagnostics and list bridge
  carry metadata only; no audio, transcript, credentials or live secret paths.
- **PASS — Spec-driven delivery**: high-risk lane includes clarify, capture/UX/
  storage checklists, dependency-ordered tasks, analyze and exact release gates.
- **PASS — Minimal architecture**: existing settings, writer, manifest,
  recovery, upload queue and embedded list are extended in place.

### After design

- **PASS — One source of preference truth**: runtime stores only the three-state
  map; removed fields may be read only during one-way legacy decoding and are
  never written again.
- **PASS — One stop owner**: the app orchestration keeps one pending stop intent
  and drains it after startup; wake/snapshot and safety timeout reuse the same
  stop function.
- **PASS — One recording package**: an active manifest becomes the final or
  degraded manifest; recovery does not invent another package format.
- **PASS — One queue/list identity**: the current deterministic queue ID,
  directory ID and server meeting ID reconcile saving, retry and server states.
- **PASS — Safe offline behavior**: a bundled registry passes the same validator
  as remote/cache data and never overrides a newer valid remote registry.
- **PASS — Staged compatibility**: client ignores the old field before server
  schema/config removal; server target registry, ETag and diagnostics remain.
- **PASS — Accessible UX**: settings, prompt, progress, `Отправить`, damage and
  deletion have visible text, keyboard/VoiceOver access and non-color meaning.

## Implementation Phases

### Phase 1 — Local policy and offline registry

1. Normalize settings to `automaticRecordingRules` plus one-time legacy decode;
   remove runtime use of global detection/auto-start/acknowledgement fields.
2. Simplify settings UI to the bulk and per-app three-state controls.
3. Add one bundled validated registry JSON and use it only after remote/cache
   resolution fails.
4. Remove assisted authorization from detector and start decision while keeping
   ordinary permissions, storage, target, consent, indicator and Stop gates.

### Phase 2 — Stop and local durability

1. Persist one pending stop request when stop races with startup and drain it
   after the transition.
2. Reconcile detector-started capture after snapshot/wake/restart and use the
   existing one-second advance loop for the 10-minute safety deadline.
3. Write an active v5 manifest before samples are accepted and checkpoint WAV
   header/data at most every 10 seconds.
4. Extend startup recovery to repair WAV length/header, rebuild review media
   when possible, finalize degraded manifest and classify impossible recovery.

### Phase 3 — Common list and sending

1. Add `saving` to the existing queue lifecycle and enqueue the local identity
   at stop start; merge the finalized manifest into the same item.
2. Preserve automatic retry and expose existing `retry(itemId:)` as the user
   action `Отправить` from app orchestration.
3. Project local rows into the embedded meeting-list document through the
   existing WebView bridge; merge by server meeting identity after upload.
4. Remove the compact local panel and right `Локальная сохранность` disclosure
   after all required states/actions exist in the common list; keep native rows
   for the unconfigured local-only shell.

### Phase 4 — Server cleanup and compatibility

1. Prove the client decodes registry documents with and without the old field
   and never consults it.
2. Remove the server policy builder, response model/property, config/env flags,
   OpenAPI schema and tests solely dedicated to assisted auto-start permission.
3. Keep published target documents, exclusions, validation, ETag/cache headers,
   telemetry and auth boundaries unchanged.
4. Record release order and rollback: client release first; server cleanup only
   after the supported minimum client no longer requires the old field.

## Validation Plan

1. Run focused Swift policy/countdown/settings/registry tests for every
   three-state and remembrance combination, clean install, legacy decode and
   offline fallback.
2. Run detector/capture orchestration tests for normal end, end during start,
   duplicate end, manual Stop suppression, unrelated manual recording,
   snapshot/wake/restart reconciliation and 10-minute safety stop.
3. Run writer/recovery tests with forced interruption before frames, after
   frames, during checkpoint, during stop and before queue merge; assert no more
   than 10 seconds of recoverable tail loss and no invisible useful folder.
4. Run queue/custody/common-list tests for saving, progress, automatic retry,
   `Отправить`, damaged/delete-only and local/server deduplication.
5. Run server config/API/OpenAPI tests proving the old field is absent while
   target registry and ETag stay valid.
6. Run keyboard/VoiceOver/source-contract checks and `node --check` for the
   embedded list bridge. Use synthetic metadata only.
7. Run the scenarios in [quickstart.md](quickstart.md), then
   `infra/scripts/ci-local.sh --fast` before PR. Do not claim release readiness
   until one `infra/scripts/ci-local.sh --full` passes on the exact candidate.
8. For an approved release, build a separate GRAF Dev artifact for runtime
   crash/wake/network checks. Public publication still requires Developer ID,
   notarization, staple, Gatekeeper and live Sparkle gates.

## Project Structure

### Documentation (this feature)

```text
specs/214-reliable-auto-recording/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── client-runtime.md
│   └── server-removal.md
├── checklists/
│   ├── requirements.md
│   ├── capture-storage.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/Shared/Sources/
├── MeetingDetection/
│   ├── MeetingDetectionModels.swift
│   ├── MeetingDetectionPolicy.swift
│   └── MeetingTargetRegistry.swift
└── Models/AudioModelCore.swift

apps/macos/RecApp/
├── App/TwoBrainRecApp.swift
├── Resources/meeting-target-registry-baseline.json
└── Sources/
    ├── Capture/
    │   ├── CanonicalRecordingWriter.swift
    │   ├── CaptureRecoveryService.swift
    │   ├── LocalRecordingManifestService.swift
    │   └── V5LocalRecordingWriter.swift
    ├── Cabinet/
    │   ├── DesktopMeetingShellView.swift
    │   └── EmbeddedCabinetWebView.swift
    ├── MeetingDetection/
    │   ├── MeetingDetectionAppModule.swift
    │   ├── MeetingDetectionSettingsStore.swift
    │   └── MeetingDetectionSettingsView.swift
    └── Upload/DesktopUploadQueueService.swift

apps/macos/Shared/Tests/
├── CanonicalRecordingManifestTests.swift
├── DesktopMeetingShellWebViewBoundaryTests.swift
├── DesktopUploadQueueV5Tests.swift
├── LocalRecordingWriterTests.swift
├── MeetingDetectionCountdownTests.swift
├── MeetingDetectionPolicyTests.swift
└── MeetingTargetRegistryTests.swift

apps/server/src/twobrain_rec_server/
├── api/meeting_detection.py
├── api/schemas.py
└── config.py

apps/server/src/twobrain_rec_server/cabinet/
├── rendering.py
└── static/cabinet/cabinet.js

apps/server/tests/
├── contract/test_meeting_detection_api_contract.py
├── contract/test_openapi_contract_drift.py
└── unit/test_config_validation.py

infra/
├── docker-compose.yml
└── env/rec.production.env.example

specs/012-server-ingest-foundation/contracts/openapi.yaml
```

**Structure Decision**: modify the current monorepo seams that already own each
state. Add only one static baseline registry resource and two feature contracts;
do not create a new runtime module, daemon, endpoint, database table, upload
queue or native meeting-history surface.

## Complexity Tracking

Constitution violations: none.
