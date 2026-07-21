# Implementation Plan: Детальный metadata-only отчёт поддержки

**Branch**: `114-support-incident-diagnostics` | **Date**: 2026-07-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/114-support-incident-diagnostics/spec.md`

## Summary

Новый отчёт поддержки будет версией `desktop-support-incident.v2`: он сохранит
совместимость с v1, но добавит канонический этап, явную локальную/серверную
истину, safe-коды причины и следующего действия, bounded timeline и последние
retry-события. macOS переиспользует уже существующий authenticated
`sync-state` endpoint, сервер продолжит принимать только metadata-only allowlist,
а private GitHub Issue получит структурированную русскую сводку и фильтруемые
корреляции. Кнопка fallback будет копировать тот же детальный redacted отчёт,
который отправляется на сервер.

## Technical Context

**Language/Version**: Swift 5.9+ (macOS app), Python 3.11+ (server)

**Primary Dependencies**: Foundation/CryptoKit/XCTest; FastAPI/Pydantic/SQLAlchemy/httpx/pytest; существующие Spec Kit/GitHub issue-canon extensions

**Storage**: JSON upload queue/ledger на macOS; `support_incidents.latest_safe_report_json` в Postgres; новая миграция не нужна

**Testing**: `swift test --package-path apps/macos`; targeted pytest contract/unit/integration; `infra/scripts/ci-local.sh` на closeout

**Risk / Validation Lane**: `high-risk-feature` — изменение privacy boundary, диагностики, upload/sync truth, серверного контракта, private Issue и fallback UX

**Release Gate**: `no deploy` в этом implementation slice; перед PR обязательны quickstart и `infra/scripts/ci-local.sh`, production rollout — отдельный release/deploy gate с approval

**Target Platform**: macOS поддерживаемых версий и Linux/Docker backend GRAF

**Project Type**: native desktop application + authenticated HTTP API + private GitHub support integration

**Performance Goals**: bounded report/clipboard preparation ≤1 s на поддерживаемом Mac; максимум 5 retry-событий и 5 affected fingerprints; payload ≤256 KiB после сериализации

**Constraints**: только metadata-only; запрещены аудио, transcript/content, secrets, cookies, tokens, signed URLs, raw UUID, live paths, filenames, meeting titles и private meeting content; клиент не вызывает MediaScribe напрямую

**Scale/Scope**: один incident report на группу локальных записей; server-side incident JSON хранит последнюю безопасную версию; issue idempotency/dedupe не создаёт дубликаты для повторной отправки того же incident

## Constitution Check

*GATE: Must pass before Phase 0 research and after Phase 1 design.*

- **Metadata-only diagnostics**: PASS. Новые значения — bounded enums, timestamps, counts и fingerprints; raw audio/transcript/content/credentials/paths не входят в контракт.
- **Capture and server boundary**: PASS. Изменение не меняет запись, system-audio-first архитектуру или прямой доступ desktop к MediaScribe; используется существующий upload queue и sync-state.
- **Deletion truth**: PASS. Серверное удаление/access block отделяется от локального purge и не объявляется доставкой по устаревшему `uploaded`/`finalizedAt`.
- **Privacy and egress**: PASS. Серверный allowlist/redaction остаётся обязательным, GitHub target — private `yshishenya/crisp`, fallback не содержит приватного контента.
- **Auth/CSRF/idempotency**: PASS. Используются существующие authenticated bridge, CSRF и dedupe/idempotency; новые обходы auth не добавляются.
- **Required Spec Kit flow**: PASS. Specify, clarify (критических неоднозначностей нет), plan, security/requirements checklists, tasks, analyze и task-to-issues выполняются до implementation.
- **Legacy boundary**: PASS. Отчёт не восстанавливает удалённый audio-routing legacy и не добавляет новый privileged компонент.

## Validation Plan

1. **Quickstart scenarios**: v2 report with all fields; v1 compatibility; server deletion/access conflict; unknown sync response; network/GitHub rejection with clipboard fallback; duplicate delivery and issue update; negative content/secret scan.
2. **Focused macOS tests**: `DesktopUploadCustodyProjectionTests`, `DesktopUploadClientTests`, queue/report fallback tests, including stale-finalized/deleted truth and retry history bounds.
3. **Focused server tests**: redaction unit tests, GitHub issue body tests, support incident contract/integration tests, including v1/v2 acceptance, state matrix, labels/title and no-secret body.
4. **Repository gate**: run `infra/scripts/ci-local.sh` once after implementation and before PR because this changes shared Swift/server contracts, privacy, UX and operations.
5. **Release/deploy**: not part of this slice. If the validated code is later released, use the project CalVer/release and CD gates separately; no claim of production behavior is made here.

## Project Structure

### Documentation (this feature)

```text
specs/114-support-incident-diagnostics/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   ├── support-incident-v2.md
│   ├── sync-state-projection.md
│   └── github-issue.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── security.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/Shared/Sources/Models/AudioModelCore.swift
  # persisted ServerTruthFingerprint: safe deletion/access/upload/processing/review facts
apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift
  # decode bounded fields from existing sync-state endpoint
apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift
  # canonical stage, truthful copy state, v2 report, retry/timeline metadata
apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift
  # build detailed report for submission and clipboard fallback
apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/RecApp/App/TwoBrainRecApp.swift
  # route the same detailed report to clipboard without AppKit in queue core
apps/macos/Shared/Tests/DesktopUploadCustodyProjectionTests.swift
apps/macos/Shared/Tests/DesktopUploadClientTests.swift
apps/macos/Shared/Tests/DesktopUploadQueueV5Tests.swift
  # report truth, safe payload, endpoint decoding and fallback tests
apps/server/src/twobrain_rec_server/support/redaction.py
apps/server/src/twobrain_rec_server/support/github_issues.py
apps/server/src/twobrain_rec_server/support/incidents.py
  # v1/v2 allowlist, redaction and structured private issue
apps/server/tests/unit/test_support_incident_redaction.py
apps/server/tests/unit/test_support_incident_github_issue_body.py
apps/server/tests/contract/test_support_incident_contract.py
apps/server/tests/integration/test_support_incidents.py
  # contract, privacy, dedupe and issue evidence
CHANGELOG.md
  # Unreleased behavior/security entry
```

**Structure Decision**: Сохраняем существующий native-first split. Shared
queue/server-truth модели остаются источником правды; клиент не создаёт второй
диагностический сервис, а backend не получает новую базу или endpoint.

## Complexity Tracking

Нет нарушений constitution, требующих исключения. Новые вложенные структуры
ограничены двумя bounded metadata списками (timeline/retry) и переиспользуют
существующие safe-code/date/fingerprint helpers.
