# Implementation Plan: Восстановление отчётов поддержки

**Branch**: `codex/111-support-incident-recovery` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/111-support-incident-recovery/spec.md`

## Summary

Восстановить доставку metadata-only отчёта из macOS-приложения до сервера и private GitHub Issue. Нативный код не будет переносить или читать web-cookie/CSRF-токен: он передаёт уже отредактированный отчёт только в текущий авторизованный embedded cabinet, а тот делает same-origin запрос с собственной сессией и CSRF-защитой. Сервер присваивает номер обращения и сохраняет отчёт до обращения к GitHub; поэтому результат честно различает синхронизированное и ожидающее синхронизации обращение.

## Technical Context

**Language/Version**: Python 3.13 / FastAPI; Swift 6, macOS 14+

**Primary Dependencies**: FastAPI, SQLAlchemy, httpx; SwiftUI, WebKit, Foundation, XCTest, pytest

**Storage**: Existing PostgreSQL `support_incidents` table and protected local desktop queue JSON; no audio or transcript storage is added

**Testing**: pytest contract/integration/unit tests; XCTest for queue, client response, bridge boundaries and UI copy; `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: high-risk feature — touches authenticated session/CSRF use, server-to-GitHub egress, PostgreSQL-backed diagnostics, local desktop state, privacy and degraded user-facing UX.

**Release Gate**: no deploy in this slice without a separate explicit release approval. Before handoff run local CI and the documented authenticated smoke path; a later release requires `infra/scripts/cd-remote.sh --dry-run` and explicit approval for execution.

**Target Platform**: Dockerised GRAF server at `rec.2brain.pro` and native macOS desktop app (macOS 14+).

**Project Type**: server API plus native desktop app.

**Performance Goals**: Accepted support report returns a correlation number within 5 seconds. The desktop bridge has a 5-second request timeout and must not block capture controls or expose auth material.

**Constraints**:

- The desktop client never sends audio, transcript text, private meeting content, credentials, cookies, session tokens, CSRF tokens, signed URLs or local paths.
- GitHub credentials remain server-only; Issues remain private.
- Existing session-cookie + CSRF policy remains intact. The endpoint must not be exempted from CSRF and legacy header authentication remains disabled in production.
- A server-accepted report may be pending GitHub synchronization; UI must not claim an Issue exists until it does.
- No new external dependency, service, worker, or secret distribution is introduced.

**Scale/Scope**: One existing support-incident endpoint and its private Issue synchronization, one embedded macOS cabinet surface, and queue-backed user feedback. No capture/audio pipeline, MediaScribe, analytics or public support portal work.

## Constitution Check

### Before Phase 0 research — PASS

- **Capture-first / visible control**: no recording path, capture control, permission or audio-routing change.
- **Data boundary and secrets**: reports stay metadata-only. The selected route deliberately retains cookie and CSRF state inside WebKit; neither is logged, copied to `URLSession`, placed in the queue, nor exposed to GitHub.
- **Lifecycle truth**: this feature reports a custody problem only; it neither changes retention/deletion behaviour nor promises recovery.
- **Spec-driven gates**: selected high-risk lane includes clarify, security and UX requirement checklists, analyze, task-to-Issue synchronization, focused tests and repository CI.

### After Phase 1 design — PASS

The selected bridge uses an already authenticated same-origin document and `callAsyncJavaScript` arguments rather than interpolating report JSON into JavaScript. The server persists the redacted report before attempting GitHub and returns an accepted-pending state on egress failure. This preserves the existing auth, privacy and RLS boundaries without adding a global cross-tenant worker or widening secret access.

## Validation Plan

1. Run focused pytest coverage for authenticated/CSRF intake, accepted-pending response, sync retry without a new report body, redaction, Issue body and internal readiness status.
2. Run focused XCTest coverage for response decoding, durable local pending state, safe failure/copy text, and the embedded cabinet bridge's same-origin/argument boundary.
3. Build and test the macOS Swift package; run the documented quickstart scenarios against local/fake server fixtures.
4. Run `infra/scripts/ci-local.sh` because the feature changes a user-visible desktop workflow, server contract, safe diagnostics and operations.
5. Before any release, verify an authenticated installed-app path against the production endpoint. A successful infrastructure health check alone is not proof of this user flow.

## Project Structure

### Documentation (this feature)

```text
specs/111-support-incident-recovery/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
├── contracts/
│   ├── desktop-support-incident-api.md
│   └── embedded-cabinet-support-bridge.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── src/twobrain_rec_server/
│   ├── api/support_incidents.py
│   ├── api/schemas.py
│   ├── api/health.py
│   └── support/{incidents.py,github_issues.py,redaction.py}
└── tests/{contract,integration,unit}/

apps/macos/
├── RecApp/App/TwoBrainRecApp.swift
├── RecApp/Sources/
│   ├── Cabinet/{EmbeddedCabinetWebView.swift,DesktopCabinetWorkspaceView.swift,...}
│   └── Upload/{DesktopUploadClient.swift,DesktopUploadQueueService.swift,DesktopSupportIncidentActionStrip.swift,...}
└── Shared/{Sources/Models/AudioModelCore.swift,Tests/}
```

**Structure Decision**: Keep the existing API/service, WebKit cabinet and local queue boundaries. Add only a narrowly scoped support-report transport bridge; do not create a general WebKit networking abstraction or a new service.

## Complexity Tracking

No constitution violation or new project is required.
