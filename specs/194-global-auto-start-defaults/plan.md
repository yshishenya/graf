# Implementation Plan: Глобальный автозапуск и безопасные defaults

**Branch**: `194-global-auto-start-defaults` | **Date**: 2026-08-23 | **Spec**: [spec.md](spec.md)

## Summary

Добавить явный server global-scope flag и strict validation, расширить policy
contract полем `scope`, включить first-install detection/verified native target
defaults и разрешить обычный prompt до acknowledgement без скрытого auto-start.
Явное `Всегда писать это приложение` сохраняет текущую policy acknowledgement
модель; после такого подтверждения final timeout/saved-target gates остаются
неизменными. До подтверждения prompt остаётся видимым ручным выбором без
обещания скрытого автоматического старта.

## Technical Context

**Language/Version**: Python 3.11+/Pydantic v2, Swift 5.9+/SwiftUI

**Primary Dependencies**: существующие FastAPI, SQLAlchemy, Foundation, SwiftUI,
AppKit и Swift Concurrency; новые зависимости не добавляются

**Storage**: существующий deployment env, JSON registry cache и atomic local
settings file; схема БД не меняется

**Testing**: pytest server unit/contract; Swift Package XCTest focused suites;
Compose config validation

**Risk / Validation Lane**: high-risk-feature — capture start/stop, policy,
permissions, onboarding/prompt UX and multi-workspace authorization

**Release Gate**: no deploy in implementation; production global flag and app
update require a separate release/deploy approval after evidence

**Target Platform**: macOS 14.5+ desktop and Docker-hosted API

**Project Type**: monorepo desktop app + FastAPI service

**Performance Goals**: first valid registry applies defaults in the same main-actor
  turn; prompt remains within existing detector debounce; no additional observer
  or network request

**Constraints**: system-audio-first capture, target allowlist, visible indicator,
one-action Stop, fail-closed policy/auth, metadata-only diagnostics

**Scale/Scope**: all authenticated workspaces only when operator global approval is
explicit; all prompt-capable native targets in the current registry

## Constitution Check

- **PASS — Visible consent**: prompt remains visible with Start/Skip and truthful
  timeout text; no hidden capture or auto-acknowledgement.
- **PASS — Capture safety**: final automatic starts still require current policy,
  acknowledgement, permissions, storage, indicator and Stop gates.
- **PASS — Workspace boundary**: global scope is explicit and approval-gated;
  subject/device references retain concrete tenant bindings.
- **PASS — External notice boundary**: notice mode remains internal-only; customer
  rollout is out of scope and not claimed.
- **PASS — Native-first/minimal**: reuse current registry, settings store,
  detector and capture path; no new runtime dependency or data table.

## Validation Plan

1. Server config tests: default disabled, scoped compatibility, global approval,
   ambiguous config, dates/version validation.
2. API contract tests: global policy in different tenant contexts, reference
   binding and schema scope/etag behavior.
3. Swift tests: scope decoding, fresh-install defaults, legacy marker behavior,
   target filtering, prompt/no-ack policy action and acknowledgement only from
   explicit opt-in path.
4. Run focused suites and Compose config rendering. Full CI remains a user-directed
   optional lane and is not claimed unless explicitly run.
5. Build a separate Dev app for first-run prompt/default smoke; do not replace
   `/Applications/GRAF.app` in this slice.

## Project Structure

```text
specs/194-global-auto-start-defaults/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── global-auto-start-policy.md
├── checklists/
│   ├── requirements.md
│   ├── capture-safety.md
│   ├── security.md
│   └── ux.md
└── tasks.md

apps/server/src/twobrain_rec_server/
├── config.py
├── api/meeting_detection.py
└── api/schemas.py

apps/macos/Shared/Sources/MeetingDetection/
├── MeetingDetectionModels.swift
├── MeetingDetectionPolicy.swift
└── MeetingTargetRegistry.swift

apps/macos/RecApp/
├── App/TwoBrainRecApp.swift
└── Sources/MeetingDetection/MeetingDetectionSettingsStore.swift

infra/docker-compose.yml
infra/env/rec.production.env.example
```

**Structure Decision**: extend the existing server policy and desktop detector
seams only; no new module, endpoint, migration, capture engine or dependency.

## Complexity Tracking

No constitution violations. Global approval is an explicit configuration safety
boundary, not an abstraction layer.
