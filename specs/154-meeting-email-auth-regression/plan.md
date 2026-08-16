# Implementation Plan: Восстановление записи встречи и входа по email

**Branch**: `codex/154-meeting-email-auth-regression` | **Date**: 2026-08-16 | **Spec**: `spec.md`

## Summary

Восстановить существующий macOS lifecycle detector → prompt/countdown → capture
start → target end → finalization и исправить передачу request-origin cookie из
embedded WebKit в desktop HTTP-клиент. Capture policy/acknowledgement gates не
ослабляются: preflight допускает показ prompt, а каждый автоматический start
повторно проверяет assisted authorization непосредственно перед стартом.

## Technical Context

**Language/Version**: Swift 5.9+/macOS native; Python 3.11+ server

**Primary Dependencies**: Swift Package Manager, AppKit, SwiftUI, WebKit,
ScreenCaptureKit/AVFoundation; FastAPI, SQLAlchemy, PostgreSQL

**Storage**: local capture artifacts/settings; PostgreSQL auth callback state and
sessions; WebKit cookie store

**Testing**: `swift test`, `swift build`, focused pytest through
`apps/server/scripts/run_local_postgres_tests.sh`, `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: `high-risk-feature`; capture start/stop, visible
consent, auth/session and local cookie transport are protected product paths.

**Release Gate**: `no deploy`; production release/notarization is out of scope.

**Target Platform**: macOS desktop app plus local/production Linux web service

**Project Type**: native desktop app + web service

**Performance Goals**: preserve 8-second prompt boundary and existing 15-second
target-end grace period; no extra network round trip on capture start.

**Constraints**: system-audio-first capture, visible indicator, one-action Stop,
fail-closed assisted authorization, no secrets/raw audio/transcript in evidence,
no new runtime dependencies.

**Scale/Scope**: regression slice across existing detector, capture controller,
embedded WebKit session bridge and server email flow; no new protocol.

## Constitution Check

- Capture-First MVP Integrity: PASS — only existing system-audio-first route is
  used; legacy routing is untouched.
- Visible Consent And User Control: PASS — prompt, 8-second countdown, Skip,
  immediate button, indicator and one-action Stop remain required.
- Auth/session and secret discipline: PASS — existing state-bound code and
  request-selected cookie helpers are reused; no bypass token or secret logging.
- Spec-Driven Delivery: PASS — clarification decision is recorded in
  `research.md`, checklists cover capture/security/UX, and consistency analysis
  is clean before implementation.

## Validation Plan

1. Focused Swift tests for detector prompt eligibility without prior policy,
   automatic-start policy re-check, countdown cancellation/idempotency and end
   grace/duplicate stop behavior.
2. Focused server auth integration and unit tests, plus Swift cookie-selection
   tests for production and loopback origins.
3. Build the macOS product and run the local app against `127.0.0.1:8081`;
   exercise email login with local code `000000` and capture lifecycle using
   metadata-only/synthetic evidence.
4. Run `infra/scripts/ci-local.sh` before closeout. No deployment or release
   command is authorized by this task.

## Project Structure

```text
specs/154-meeting-email-auth-regression/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-lifecycle.md
│   └── email-auth-session.md
├── checklists/
│   ├── audio-capture.md
│   ├── security.md
│   └── ux.md
└── tasks.md

apps/macos/RecApp/App/TwoBrainRecApp.swift
apps/macos/RecApp/Sources/Cabinet/DesktopCabinetConfiguration.swift
apps/macos/RecApp/Sources/Cabinet/DesktopCabinetSessionBridge.swift
apps/macos/RecApp/Sources/Upload/DesktopUploadClient.swift
apps/macos/Shared/Tests/MeetingDetectionPolicyTests.swift
apps/macos/Shared/Tests/MeetingDetectionCountdownTests.swift
apps/macos/Shared/Tests/DesktopCabinetConfigurationTests.swift
apps/macos/Shared/Tests/DesktopUploadClientTests.swift
apps/server/src/twobrain_rec_server/auth/dependencies.py
apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py
apps/server/tests/integration/test_web_owner_session_context.py
```

**Structure Decision**: минимальный diff в существующих Swift и Python flows;
новые абстракции, auth protocol и audio engine не создаются.

## Complexity Tracking

Нет нарушений конституции, требующих исключения.
